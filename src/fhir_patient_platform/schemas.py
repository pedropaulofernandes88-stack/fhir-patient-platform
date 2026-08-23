"""Modelos das rotas de conveniencia fora da superficie REST FHIR."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ImportSummary(BaseModel):
    bundle_type: str
    total: int = Field(ge=0)
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    audit_event_id: str


class PatientSummary(BaseModel):
    id: str
    display: str
    gender: str | None = None
    birth_date: str | None = None


class TimelineEvent(BaseModel):
    resource_type: str
    resource_id: str
    event_at: str | None = None
    display: str
    code_system: str | None = None
    code: str | None = None
    version_id: int = Field(ge=1)


class AuditEventRead(BaseModel):
    event_id: str
    action: str
    bundle_type: str
    created_resources: int
    updated_resources: int
    total_resources: int
    occurred_at: datetime
