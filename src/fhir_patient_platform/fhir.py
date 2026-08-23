"""Validacao estrutural e extracao dos campos indexados do subconjunto FHIR R4."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

FHIR_VERSION = "4.0.1"
SUPPORTED_RESOURCE_TYPES = {
    "Patient",
    "Encounter",
    "Condition",
    "Observation",
    "MedicationRequest",
    "Procedure",
    "Immunization",
}
SUPPORTED_BUNDLE_TYPES = {"collection", "transaction", "batch"}
FHIR_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")


class FhirValidationError(ValueError):
    def __init__(self, diagnostics: str) -> None:
        super().__init__(diagnostics)
        self.diagnostics = diagnostics


@dataclass(frozen=True)
class PreparedResource:
    resource_type: str
    resource_id: str
    patient_id: str | None
    code_system: str | None
    code_value: str | None
    event_at: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class PreparedBundle:
    bundle_type: str
    resources: list[PreparedResource]


def _reference_id(reference: Any, expected_type: str = "Patient") -> str | None:
    if not isinstance(reference, dict):
        return None
    value = reference.get("reference")
    if not isinstance(value, str):
        return None
    prefix = f"{expected_type}/"
    if value.startswith(prefix):
        return value.removeprefix(prefix).split("/")[0]
    return None


def patient_id_for(resource: dict[str, Any]) -> str | None:
    resource_type = resource.get("resourceType")
    if resource_type == "Patient":
        return resource.get("id")
    if resource_type == "Immunization":
        return _reference_id(resource.get("patient"))
    return _reference_id(resource.get("subject"))


def coding_for(resource: dict[str, Any]) -> tuple[str | None, str | None]:
    resource_type = resource.get("resourceType")
    if resource_type == "MedicationRequest":
        concept = resource.get("medicationCodeableConcept")
    else:
        concept = resource.get("code")
    if not isinstance(concept, dict):
        return None, None
    codings = concept.get("coding")
    if not isinstance(codings, list) or not codings or not isinstance(codings[0], dict):
        return None, None
    return codings[0].get("system"), codings[0].get("code")


def event_datetime_for(resource: dict[str, Any]) -> str | None:
    resource_type = resource.get("resourceType")
    candidates: list[Any]
    if resource_type == "Encounter":
        candidates = [(resource.get("period") or {}).get("start")]
    elif resource_type == "Condition":
        candidates = [resource.get("onsetDateTime"), resource.get("recordedDate")]
    elif resource_type == "Observation":
        candidates = [resource.get("effectiveDateTime"), resource.get("issued")]
    elif resource_type == "MedicationRequest":
        candidates = [resource.get("authoredOn")]
    elif resource_type == "Procedure":
        candidates = [
            resource.get("performedDateTime"),
            (resource.get("performedPeriod") or {}).get("start"),
        ]
    elif resource_type == "Immunization":
        candidates = [resource.get("occurrenceDateTime")]
    else:
        candidates = []
    return next((value for value in candidates if isinstance(value, str) and value), None)


def display_for(resource: dict[str, Any]) -> str:
    resource_type = resource.get("resourceType")
    if resource_type == "Encounter":
        class_display = (resource.get("class") or {}).get("display")
        return class_display or "Encounter"
    if resource_type == "Immunization":
        concept = resource.get("vaccineCode") or {}
    elif resource_type == "MedicationRequest":
        concept = resource.get("medicationCodeableConcept") or {}
    else:
        concept = resource.get("code") or {}
    if isinstance(concept, dict):
        if concept.get("text"):
            return str(concept["text"])
        codings = concept.get("coding") or []
        if codings and isinstance(codings[0], dict):
            return str(codings[0].get("display") or codings[0].get("code") or resource_type)
    return str(resource_type)


def patient_display(resource: dict[str, Any]) -> str:
    names = resource.get("name") or []
    if names and isinstance(names[0], dict):
        text = names[0].get("text")
        if text:
            return str(text)
        given = " ".join(str(part) for part in names[0].get("given") or [])
        family = str(names[0].get("family") or "")
        combined = f"{given} {family}".strip()
        if combined:
            return combined
    return f"Patient/{resource.get('id', 'unknown')}"


def operation_outcome(diagnostics: str, code: str = "invalid") -> dict[str, Any]:
    return {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": "error",
                "code": code,
                "diagnostics": diagnostics,
            }
        ],
    }


def prepare_bundle(bundle: dict[str, Any]) -> PreparedBundle:
    if bundle.get("resourceType") != "Bundle":
        raise FhirValidationError("O corpo deve ser um recurso FHIR Bundle.")
    bundle_type = bundle.get("type")
    if bundle_type not in SUPPORTED_BUNDLE_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_BUNDLE_TYPES))
        raise FhirValidationError(f"Bundle.type deve ser um de: {allowed}.")
    entries = bundle.get("entry")
    if not isinstance(entries, list) or not entries:
        raise FhirValidationError("Bundle.entry deve conter ao menos um recurso.")

    prepared: list[PreparedResource] = []
    identities: set[tuple[str, str]] = set()
    full_urls: set[str] = set()

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("resource"), dict):
            raise FhirValidationError(f"Bundle.entry[{index}].resource e obrigatorio.")
        if bundle_type in {"transaction", "batch"}:
            request = entry.get("request")
            if not isinstance(request, dict) or request.get("method") not in {"POST", "PUT"}:
                raise FhirValidationError(
                    f"Bundle.entry[{index}].request deve usar POST ou PUT."
                )

        full_url = entry.get("fullUrl")
        if isinstance(full_url, str):
            if full_url in full_urls:
                raise FhirValidationError(f"Bundle.entry[{index}].fullUrl esta duplicado.")
            full_urls.add(full_url)

        resource = deepcopy(entry["resource"])
        resource_type = resource.get("resourceType")
        if resource_type not in SUPPORTED_RESOURCE_TYPES:
            supported = ", ".join(sorted(SUPPORTED_RESOURCE_TYPES))
            raise FhirValidationError(
                f"Bundle.entry[{index}] possui resourceType nao suportado. Suportados: {supported}."
            )
        resource_id = resource.get("id") or str(uuid4())
        if not isinstance(resource_id, str) or not FHIR_ID_PATTERN.fullmatch(resource_id):
            raise FhirValidationError(f"Bundle.entry[{index}].resource.id e invalido.")
        resource["id"] = resource_id
        identity = (resource_type, resource_id)
        if identity in identities:
            raise FhirValidationError(
                f"O recurso {resource_type}/{resource_id} aparece mais de uma vez no Bundle."
            )
        identities.add(identity)
        code_system, code_value = coding_for(resource)
        prepared.append(
            PreparedResource(
                resource_type=resource_type,
                resource_id=resource_id,
                patient_id=patient_id_for(resource),
                code_system=code_system,
                code_value=code_value,
                event_at=event_datetime_for(resource),
                payload=resource,
            )
        )

    return PreparedBundle(bundle_type=bundle_type, resources=prepared)
