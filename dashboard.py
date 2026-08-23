"""Interface Streamlit para explorar pacientes e a linha do tempo FHIR."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DEFAULT_API_URL = os.getenv("FHIR_API_URL", "http://127.0.0.1:8000").rstrip("/")
SAMPLE_BUNDLE = ROOT / "data" / "sample" / "fhir_bundle.json"


def api_get(api_url: str, path: str) -> Any:
    response = httpx.get(f"{api_url}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def import_sample(api_url: str) -> dict[str, Any]:
    bundle = json.loads(SAMPLE_BUNDLE.read_text(encoding="utf-8"))
    response = httpx.post(f"{api_url}/fhir", json=bundle, timeout=30)
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="FHIR Patient Platform", page_icon="🧬", layout="wide")
st.markdown(
    """
    <style>
      .stApp { background: #f5f7fb; }
      [data-testid="stSidebar"] { background: #111c3b; }
      [data-testid="stSidebar"] * { color: #f4f7ff; }
      [data-testid="stMetric"] {
        background: white; border: 1px solid #dfe5f0; border-radius: 14px; padding: 16px;
      }
      .hero {
        color: white; padding: 24px 28px; border-radius: 18px; margin-bottom: 18px;
        background: linear-gradient(120deg, #111c3b, #384ea3 60%, #657be0);
      }
      .hero h1 { margin: 0 0 6px; }
      .hero p { margin: 0; opacity: .9; }
    </style>
    <div class="hero">
      <h1>FHIR Patient Platform</h1>
      <p>Importação, busca e linha do tempo longitudinal com recursos FHIR R4 sintéticos.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Conexão")
    api_url = st.text_input("URL da API", value=DEFAULT_API_URL).rstrip("/")
    if st.button("Importar Bundle de demonstração", width="stretch"):
        try:
            result = import_sample(api_url)
            statuses = [entry["response"]["status"] for entry in result.get("entry", [])]
            st.success(f"Bundle processado: {len(statuses)} recursos.")
        except (httpx.HTTPError, OSError, ValueError, KeyError) as error:
            st.error(f"Falha na importação: {error}")

try:
    health = api_get(api_url, "/health")
    patients = api_get(api_url, "/api/patients")
except httpx.HTTPError:
    st.error(
        "API indisponível. Inicie `fhir-platform-api` em outro terminal e tente novamente."
    )
    st.stop()

metric1, metric2, metric3 = st.columns(3)
metric1.metric("Status da API", health["status"].upper())
metric2.metric("FHIR", health["fhirVersion"])
metric3.metric("Pacientes sintéticos", len(patients))

if not patients:
    st.info("Importe o Bundle de demonstração pela barra lateral para começar.")
    st.stop()

patient_by_label = {
    f"{patient['display']} — {patient['id']}": patient for patient in patients
}
selected_label = st.selectbox("Paciente", options=list(patient_by_label))
selected_patient = patient_by_label[selected_label]

left, right = st.columns([1, 2])
with left:
    st.subheader("Resumo")
    st.write(f"**ID:** `{selected_patient['id']}`")
    gender = selected_patient.get("gender") or "não informado"
    birth_date = selected_patient.get("birth_date") or "não informado"
    st.write(f"**Gênero administrativo:** {gender}")
    st.write(f"**Nascimento:** {birth_date}")
    patient_resource = api_get(api_url, f"/fhir/Patient/{selected_patient['id']}")
    with st.expander("Recurso Patient em JSON"):
        st.json(patient_resource)

with right:
    st.subheader("Linha do tempo")
    timeline = api_get(api_url, f"/api/patients/{selected_patient['id']}/timeline")
    if timeline:
        frame = pd.DataFrame(timeline).rename(
            columns={
                "event_at": "Data/hora",
                "resource_type": "Recurso",
                "display": "Descrição",
                "code": "Código",
                "version_id": "Versão",
            }
        )
        st.dataframe(
            frame[["Data/hora", "Recurso", "Descrição", "Código", "Versão"]],
            width="stretch",
            hide_index=True,
        )
        event_labels = {}
        for event in timeline:
            event_date = event["event_at"] or "Sem data"
            label = f"{event_date} — {event['resource_type']} — {event['display']}"
            event_labels[label] = event
        event_label = st.selectbox("Inspecionar evento", options=list(event_labels))
        event = event_labels[event_label]
        resource_path = f"/fhir/{event['resource_type']}/{event['resource_id']}"
        resource = api_get(api_url, resource_path)
        st.json(resource, expanded=False)
    else:
        st.info("Este paciente ainda não possui eventos clínicos importados.")

with st.expander("Auditoria de importações"):
    audit = api_get(api_url, "/api/audit")
    st.dataframe(pd.DataFrame(audit), width="stretch", hide_index=True)

st.caption(
    "Todos os registros de demonstração são fictícios. "
    "O MVP não deve ser usado para assistência clínica."
)
