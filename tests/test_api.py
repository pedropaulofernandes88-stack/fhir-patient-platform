"""Testes de contrato e comportamento da API."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fhir_patient_platform.main import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_bundle() -> dict:
    path = ROOT / "data" / "sample" / "fhir_bundle.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def client(tmp_path: Path):
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    with TestClient(create_app(database_url)) as test_client:
        yield test_client


def test_health_and_capability_statement(client: TestClient) -> None:
    health = client.get("/health")
    metadata = client.get("/fhir/metadata")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "fhirVersion": "4.0.1"}
    assert metadata.status_code == 200
    assert metadata.json()["resourceType"] == "CapabilityStatement"


def test_transaction_is_idempotent_and_versions_resources(
    client: TestClient, sample_bundle: dict
) -> None:
    first = client.post("/fhir", json=sample_bundle)
    second = client.post("/fhir", json=sample_bundle)
    patient = client.get("/fhir/Patient/ana-souza")
    audit = client.get("/api/audit")

    assert first.status_code == 200
    assert first.json()["type"] == "transaction-response"
    assert {entry["response"]["status"] for entry in first.json()["entry"]} == {
        "201 Created"
    }
    assert {entry["response"]["status"] for entry in second.json()["entry"]} == {
        "200 OK"
    }
    assert patient.json()["meta"]["versionId"] == "2"
    assert patient.headers["etag"] == 'W/"2"'
    assert len(audit.json()) == 2
    assert "ana-souza" not in audit.text

    history = client.get("/fhir/Patient/ana-souza/_history")
    first_version = client.get("/fhir/Patient/ana-souza/_history/1")
    assert history.status_code == 200
    assert history.json()["type"] == "history"
    assert history.json()["total"] == 2
    assert first_version.status_code == 200
    assert first_version.json()["meta"]["versionId"] == "1"


def test_search_and_patient_timeline(client: TestClient, sample_bundle: dict) -> None:
    client.post("/fhir", json=sample_bundle)

    observations = client.get("/fhir/Observation", params={"patient": "ana-souza"})
    timeline = client.get("/api/patients/ana-souza/timeline")

    assert observations.status_code == 200
    assert observations.json()["type"] == "searchset"
    assert observations.json()["total"] == 1
    assert observations.json()["entry"][0]["resource"]["id"] == "observation-ana-bp"
    assert timeline.status_code == 200
    assert len(timeline.json()) == 5
    assert [event["event_at"] for event in timeline.json()] == sorted(
        event["event_at"] for event in timeline.json()
    )


def test_missing_patient_reference_returns_operation_outcome(client: TestClient) -> None:
    invalid_bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "Observation/orphan-observation",
                "resource": {
                    "resourceType": "Observation",
                    "id": "orphan-observation",
                    "status": "final",
                    "subject": {"reference": "Patient/unknown"},
                    "code": {"text": "Teste"},
                },
                "request": {"method": "PUT", "url": "Observation/orphan-observation"},
            }
        ],
    }

    response = client.post("/fhir", json=invalid_bundle)

    assert response.status_code == 422
    assert response.json()["resourceType"] == "OperationOutcome"
    assert "unknown" in response.json()["issue"][0]["diagnostics"]


def test_administrative_import_accepts_collection_bundle(
    client: TestClient, sample_bundle: dict
) -> None:
    collection = {**sample_bundle, "type": "collection"}
    for entry in collection["entry"]:
        entry.pop("request", None)

    response = client.post("/api/import", json=collection)

    assert response.status_code == 200
    assert response.json()["created"] == 9
    assert response.json()["bundle_type"] == "collection"


def test_transaction_resolves_urn_uuid_references(client: TestClient) -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "urn:uuid:patient-one",
                "resource": {"resourceType": "Patient", "id": "patient-one"},
                "request": {"method": "PUT", "url": "Patient/patient-one"},
            },
            {
                "fullUrl": "urn:uuid:observation-one",
                "resource": {
                    "resourceType": "Observation",
                    "id": "observation-one",
                    "status": "final",
                    "subject": {"reference": "urn:uuid:patient-one"},
                    "code": {"text": "Exame sintetico"},
                },
                "request": {"method": "PUT", "url": "Observation/observation-one"},
            },
        ],
    }

    response = client.post("/fhir", json=bundle)
    observation = client.get("/fhir/Observation/observation-one")

    assert response.status_code == 200
    assert observation.json()["subject"]["reference"] == "Patient/patient-one"


def test_request_url_and_if_match_enforce_transaction_semantics(
    client: TestClient, sample_bundle: dict
) -> None:
    invalid_url = json.loads(json.dumps(sample_bundle))
    invalid_url["entry"][0]["request"]["url"] = "Patient/wrong"
    assert client.post("/fhir", json=invalid_url).status_code == 422

    assert client.post("/fhir", json=sample_bundle).status_code == 200
    stale = json.loads(json.dumps(sample_bundle))
    stale["entry"][0]["request"]["ifMatch"] = 'W/"9"'
    conflict = client.post("/fhir", json=stale)

    assert conflict.status_code == 422
    assert "If-Match" in conflict.text
    assert client.get("/fhir/Patient/ana-souza").json()["meta"]["versionId"] == "1"
