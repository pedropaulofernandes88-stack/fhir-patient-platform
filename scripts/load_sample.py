"""Envia o Bundle sintético para uma instancia local da API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--bundle",
        type=Path,
        default=ROOT / "data" / "sample" / "fhir_bundle.json",
    )
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    response = httpx.post(f"{args.api_url.rstrip('/')}/fhir", json=bundle, timeout=30)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
