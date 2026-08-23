"""Casos de uso transacionais e consultas da plataforma."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .fhir import (
    SUPPORTED_RESOURCE_TYPES,
    FhirValidationError,
    display_for,
    patient_display,
    prepare_bundle,
)
from .models import AuditEvent, FhirResource, FhirResourceVersion
from .schemas import AuditEventRead, ImportSummary, PatientSummary, TimelineEvent


@dataclass(frozen=True)
class ImportResult:
    summary: ImportSummary
    response_entries: list[dict[str, Any]]


def _iso_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat().replace("+00:00", "Z")


def resource_payload(row: FhirResource) -> dict[str, Any]:
    payload = deepcopy(row.payload)
    meta = dict(payload.get("meta") or {})
    meta["versionId"] = str(row.version_id)
    meta["lastUpdated"] = _iso_datetime(row.updated_at)
    payload["meta"] = meta
    return payload


def version_payload(row: FhirResourceVersion) -> dict[str, Any]:
    payload = deepcopy(row.payload)
    meta = dict(payload.get("meta") or {})
    meta["versionId"] = str(row.version_id)
    meta["lastUpdated"] = _iso_datetime(row.recorded_at)
    payload["meta"] = meta
    return payload


def _validate_patient_references(session: Session, resources: list[Any]) -> None:
    patient_ids_in_bundle = {
        resource.resource_id for resource in resources if resource.resource_type == "Patient"
    }
    referenced_patient_ids = {
        resource.patient_id
        for resource in resources
        if resource.resource_type != "Patient" and resource.patient_id
    }
    missing_subject = next(
        (
            resource
            for resource in resources
            if resource.resource_type != "Patient" and resource.patient_id is None
        ),
        None,
    )
    if missing_subject:
        resource_identity = (
            f"{missing_subject.resource_type}/{missing_subject.resource_id}"
        )
        raise FhirValidationError(
            f"{resource_identity} deve referenciar Patient."
        )
    candidates = referenced_patient_ids.difference(patient_ids_in_bundle)
    if not candidates:
        return
    existing_ids = set(
        session.scalars(
            select(FhirResource.resource_id).where(
                FhirResource.resource_type == "Patient",
                FhirResource.resource_id.in_(candidates),
            )
        )
    )
    unresolved = candidates.difference(existing_ids)
    if unresolved:
        raise FhirValidationError(
            "Referencias de Patient nao resolvidas: " + ", ".join(sorted(unresolved)) + "."
        )


def import_bundle(session: Session, bundle: dict[str, Any]) -> ImportResult:
    prepared_bundle = prepare_bundle(bundle)
    _validate_patient_references(session, prepared_bundle.resources)
    now = datetime.now(UTC)
    created = 0
    updated = 0
    response_entries: list[dict[str, Any]] = []

    for resource in prepared_bundle.resources:
        row = session.scalar(
            select(FhirResource).where(
                FhirResource.resource_type == resource.resource_type,
                FhirResource.resource_id == resource.resource_id,
            )
        )
        if row is None:
            if resource.method == "PUT" and resource.if_match:
                raise FhirValidationError(
                    f"If-Match nao pode atualizar recurso inexistente: "
                    f"{resource.resource_type}/{resource.resource_id}."
                )
            row = FhirResource(
                resource_type=resource.resource_type,
                resource_id=resource.resource_id,
                patient_id=resource.patient_id,
                code_system=resource.code_system,
                code_value=resource.code_value,
                event_at=resource.event_at,
                version_id=1,
                payload=resource.payload,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            status = "201 Created"
            created += 1
        else:
            expected_etag = f'W/"{row.version_id}"'
            if resource.if_match and resource.if_match != expected_etag:
                raise FhirValidationError(
                    f"Conflito de versao em {resource.resource_type}/{resource.resource_id}: "
                    f"If-Match esperado {expected_etag}."
                )
            row.patient_id = resource.patient_id
            row.code_system = resource.code_system
            row.code_value = resource.code_value
            row.event_at = resource.event_at
            row.payload = resource.payload
            row.version_id += 1
            row.updated_at = now
            status = "200 OK"
            updated += 1
        session.flush()
        session.add(
            FhirResourceVersion(
                resource_type=resource.resource_type,
                resource_id=resource.resource_id,
                version_id=row.version_id,
                payload=deepcopy(resource.payload),
                recorded_at=now,
            )
        )
        response_entries.append(
            {
                "response": {
                    "status": status,
                    "location": (
                        f"{resource.resource_type}/{resource.resource_id}"
                        f"/_history/{row.version_id}"
                    ),
                }
            }
        )

    event_id = str(uuid4())
    session.add(
        AuditEvent(
            event_id=event_id,
            action="bundle-import",
            bundle_type=prepared_bundle.bundle_type,
            created_resources=created,
            updated_resources=updated,
            total_resources=len(prepared_bundle.resources),
            occurred_at=now,
        )
    )
    session.commit()
    return ImportResult(
        summary=ImportSummary(
            bundle_type=prepared_bundle.bundle_type,
            total=len(prepared_bundle.resources),
            created=created,
            updated=updated,
            audit_event_id=event_id,
        ),
        response_entries=response_entries,
    )


def get_resource(session: Session, resource_type: str, resource_id: str) -> dict[str, Any] | None:
    row = session.scalar(
        select(FhirResource).where(
            FhirResource.resource_type == resource_type,
            FhirResource.resource_id == resource_id,
        )
    )
    return resource_payload(row) if row else None


def get_resource_version(
    session: Session, resource_type: str, resource_id: str, version_id: int
) -> dict[str, Any] | None:
    row = session.scalar(
        select(FhirResourceVersion).where(
            FhirResourceVersion.resource_type == resource_type,
            FhirResourceVersion.resource_id == resource_id,
            FhirResourceVersion.version_id == version_id,
        )
    )
    return version_payload(row) if row else None


def resource_history(session: Session, resource_type: str, resource_id: str) -> dict[str, Any]:
    rows = session.scalars(
        select(FhirResourceVersion)
        .where(
            FhirResourceVersion.resource_type == resource_type,
            FhirResourceVersion.resource_id == resource_id,
        )
        .order_by(FhirResourceVersion.version_id.desc())
    ).all()
    return {
        "resourceType": "Bundle",
        "type": "history",
        "total": len(rows),
        "entry": [
            {
                "fullUrl": f"/fhir/{resource_type}/{resource_id}/_history/{row.version_id}",
                "resource": version_payload(row),
                "request": {"method": "PUT", "url": f"{resource_type}/{resource_id}"},
                "response": {
                    "status": "200 OK",
                    "etag": f'W/"{row.version_id}"',
                    "lastModified": _iso_datetime(row.recorded_at),
                },
            }
            for row in rows
        ],
    }


def search_resources(
    session: Session,
    resource_type: str,
    *,
    patient_id: str | None = None,
    code: str | None = None,
    count: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    if resource_type not in SUPPORTED_RESOURCE_TYPES:
        raise FhirValidationError(f"resourceType nao suportado: {resource_type}.")
    filters = [FhirResource.resource_type == resource_type]
    if patient_id:
        filters.append(FhirResource.patient_id == patient_id)
    if code:
        filters.append(FhirResource.code_value == code)
    total = session.scalar(select(func.count()).select_from(FhirResource).where(*filters)) or 0
    rows = session.scalars(
        select(FhirResource)
        .where(*filters)
        .order_by(FhirResource.resource_id)
        .offset(offset)
        .limit(count)
    ).all()
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": total,
        "entry": [
            {
                "fullUrl": f"/fhir/{row.resource_type}/{row.resource_id}",
                "resource": resource_payload(row),
                "search": {"mode": "match"},
            }
            for row in rows
        ],
    }


def list_patients(session: Session) -> list[PatientSummary]:
    rows = session.scalars(
        select(FhirResource)
        .where(FhirResource.resource_type == "Patient")
        .order_by(FhirResource.resource_id)
    ).all()
    return [
        PatientSummary(
            id=row.resource_id,
            display=patient_display(row.payload),
            gender=row.payload.get("gender"),
            birth_date=row.payload.get("birthDate"),
        )
        for row in rows
    ]


def patient_timeline(session: Session, patient_id: str) -> list[TimelineEvent] | None:
    patient = session.scalar(
        select(FhirResource).where(
            FhirResource.resource_type == "Patient",
            FhirResource.resource_id == patient_id,
        )
    )
    if patient is None:
        return None
    rows = session.scalars(
        select(FhirResource)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type != "Patient",
        )
        .order_by(FhirResource.event_at.asc().nulls_last(), FhirResource.resource_type)
    ).all()
    return [
        TimelineEvent(
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            event_at=row.event_at,
            display=display_for(row.payload),
            code_system=row.code_system,
            code=row.code_value,
            version_id=row.version_id,
        )
        for row in rows
    ]


def list_audit_events(session: Session, limit: int = 50) -> list[AuditEventRead]:
    rows = session.scalars(
        select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)
    ).all()
    return [
        AuditEventRead(
            event_id=row.event_id,
            action=row.action,
            bundle_type=row.bundle_type,
            created_resources=row.created_resources,
            updated_resources=row.updated_resources,
            total_resources=row.total_resources,
            occurred_at=row.occurred_at,
        )
        for row in rows
    ]
