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
    assert len(audit.json()) == 2
    assert "ana-souza" not in audit.text


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
