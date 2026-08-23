"""Configuracao por ambiente sem incluir segredos no repositorio."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./data/fhir.db"
    api_url: str = "http://127.0.0.1:8000"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.getenv("FHIR_DATABASE_URL", cls.database_url),
            api_url=os.getenv("FHIR_API_URL", cls.api_url),
        )
