FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FHIR_DATABASE_URL=sqlite:////app/data/fhir.db

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser . .
RUN python -m pip install --no-cache-dir . && mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "fhir_patient_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
