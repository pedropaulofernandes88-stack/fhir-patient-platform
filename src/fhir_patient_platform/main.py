"""Aplicacao FastAPI: superficie FHIR R4 e endpoints de apoio ao dashboard."""

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .config import Settings
from .database import Database
from .fhir import FHIR_VERSION, FhirValidationError, operation_outcome
from .schemas import AuditEventRead, ImportSummary, PatientSummary, TimelineEvent
from .service import (
    get_resource,
    import_bundle,
    list_audit_events,
    list_patients,
    patient_timeline,
    search_resources,
)


def create_app(database_url: str | None = None) -> FastAPI:
    settings = Settings.from_env()
    database = Database(database_url or settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        database.create_schema()
        yield

    application = FastAPI(
        title="FHIR Patient Platform",
        description="FHIR R4 interoperability MVP using synthetic patient data.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.database = database

    def get_session() -> Generator[Session, None, None]:
        yield from database.session_dependency()

    SessionDependency = Annotated[Session, Depends(get_session)]

    @application.exception_handler(FhirValidationError)
    async def fhir_validation_handler(
        _request: Request, error: FhirValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=operation_outcome(error.diagnostics),
            media_type="application/fhir+json",
        )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "fhirVersion": FHIR_VERSION}

    @application.get("/fhir/metadata")
    def capability_statement() -> dict[str, Any]:
        return {
            "resourceType": "CapabilityStatement",
            "status": "active",
            "kind": "instance",
            "fhirVersion": FHIR_VERSION,
            "format": ["json"],
            "rest": [
                {
                    "mode": "server",
                    "resource": [
                        {
                            "type": resource_type,
                            "interaction": [{"code": "read"}, {"code": "search-type"}],
                        }
                        for resource_type in [
                            "Patient",
                            "Encounter",
                            "Condition",
                            "Observation",
                            "MedicationRequest",
                            "Procedure",
                            "Immunization",
                        ]
                    ],
                }
            ],
        }

    @application.post("/fhir")
    def fhir_transaction(
        bundle: Annotated[dict[str, Any], Body()], session: SessionDependency
    ) -> JSONResponse:
        if bundle.get("type") not in {"transaction", "batch"}:
            raise FhirValidationError("POST /fhir aceita Bundle transaction ou batch.")
        result = import_bundle(session, bundle)
        response_type = (
            "transaction-response"
            if result.summary.bundle_type == "transaction"
            else "batch-response"
        )
        return JSONResponse(
            content={
                "resourceType": "Bundle",
                "type": response_type,
                "entry": result.response_entries,
            },
            media_type="application/fhir+json",
        )

    @application.post("/api/import", response_model=ImportSummary)
    def administrative_import(
        bundle: Annotated[dict[str, Any], Body()], session: SessionDependency
    ) -> ImportSummary:
        return import_bundle(session, bundle).summary

    @application.get("/fhir/{resource_type}")
    def fhir_search(
        resource_type: str,
        session: SessionDependency,
        patient: str | None = None,
        code: str | None = None,
        count: Annotated[int, Query(alias="_count", ge=1, le=100)] = 20,
        offset: Annotated[int, Query(alias="_offset", ge=0)] = 0,
    ) -> JSONResponse:
        bundle = search_resources(
            session,
            resource_type,
            patient_id=patient,
            code=code,
            count=count,
            offset=offset,
        )
        return JSONResponse(content=bundle, media_type="application/fhir+json")

    @application.get("/fhir/{resource_type}/{resource_id}")
    def fhir_read(
        resource_type: str, resource_id: str, session: SessionDependency
    ) -> JSONResponse:
        resource = get_resource(session, resource_type, resource_id)
        if resource is None:
            return JSONResponse(
                status_code=404,
                content=operation_outcome(
                    f"Recurso nao encontrado: {resource_type}/{resource_id}.", "not-found"
                ),
                media_type="application/fhir+json",
            )
        return JSONResponse(content=resource, media_type="application/fhir+json")

    @application.get("/api/patients", response_model=list[PatientSummary])
    def patients(session: SessionDependency) -> list[PatientSummary]:
        return list_patients(session)

    @application.get(
        "/api/patients/{patient_id}/timeline",
        response_model=list[TimelineEvent],
    )
    def timeline(
        patient_id: str, session: SessionDependency
    ) -> list[TimelineEvent] | JSONResponse:
        events = patient_timeline(session, patient_id)
        if events is None:
            return JSONResponse(status_code=404, content={"detail": "Patient not found"})
        return events

    @application.get("/api/audit", response_model=list[AuditEventRead])
    def audit(
        session: SessionDependency,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> list[AuditEventRead]:
        return list_audit_events(session, limit=limit)

    return application


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("fhir_patient_platform.main:app", host="127.0.0.1", port=8000, reload=False)
