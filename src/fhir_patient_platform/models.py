"""Modelos de persistencia; o recurso FHIR original e preservado em JSON."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class FhirResource(Base):
    __tablename__ = "fhir_resources"
    __table_args__ = (
        UniqueConstraint("resource_type", "resource_id", name="uq_fhir_resource_identity"),
        Index("ix_fhir_resource_patient_type", "patient_id", "resource_type"),
    )

    internal_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    patient_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code_value: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    event_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    bundle_type: Mapped[str] = mapped_column(String(30), nullable=False)
    created_resources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_resources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_resources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
