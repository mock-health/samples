#!/usr/bin/env python3
"""POST data/Aurelio_Whorton_transaction.json to a HAPI FHIR server.

Usage:
    docker run -d -p 8080:8080 hapiproject/hapi:latest
    # wait ~25 seconds for HAPI to come up
    export HAPI_BASE_URL=http://localhost:8080/fhir
    python load_bundle.py

Loads one Synthea patient (Aurelio Whorton, 171 resources) as a single
FHIR transaction bundle. The bundle's internal `urn:uuid:` references
are resolved automatically by FHIR transaction semantics — no client-
side rewriting required.

The transaction bundle was generated once at maintainer-prep time from
the original Synthea collection bundle (data/Aurelio_Whorton_collection.json,
shipped alongside for transparency). To regenerate from source:

    # Requires the fhir-studio repo cloned alongside samples/
    import sys, json
    sys.path.insert(0, "../fhir-studio/scripts")
    from import_fhir_bundles_gcp import convert_collection_to_transaction
    collection = json.load(open("data/Aurelio_Whorton_collection.json"))
    transaction = convert_collection_to_transaction(collection)
    json.dump(transaction, open("data/Aurelio_Whorton_transaction.json", "w"), indent=2)
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import httpx

SCRIPT_DIR = Path(__file__).parent
BUNDLE_PATH = SCRIPT_DIR / "data" / "Aurelio_Whorton_transaction.json"


def main() -> int:
    base_url = os.environ.get("HAPI_BASE_URL", "http://localhost:8080/fhir")
    if not BUNDLE_PATH.exists():
        print(f"ERROR: bundle not found: {BUNDLE_PATH}", file=sys.stderr)
        return 2

    bundle = json.loads(BUNDLE_PATH.read_text())
    if bundle.get("type") != "transaction":
        print(
            f"ERROR: bundle type is '{bundle.get('type')}', expected 'transaction'",
            file=sys.stderr,
        )
        return 2

    entry_count = len(bundle.get("entry") or [])
    print(f"Loading {entry_count} entries to {base_url} ...")

    headers = {
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json",
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(base_url, json=bundle, headers=headers)
    except httpx.RequestError as exc:
        print(f"ERROR: HTTP request failed: {exc}", file=sys.stderr)
        print(
            "  Is HAPI running? Try: curl -sf "
            f"{base_url}/metadata > /dev/null && echo OK",
            file=sys.stderr,
        )
        return 1

    if not (200 <= resp.status_code < 300):
        print(f"ERROR: HAPI returned HTTP {resp.status_code}", file=sys.stderr)
        print(resp.text[:1000], file=sys.stderr)
        return 1

    try:
        result = resp.json()
    except Exception:
        print("ERROR: response was not valid JSON", file=sys.stderr)
        print(resp.text[:500], file=sys.stderr)
        return 1

    statuses: Counter[str] = Counter()
    for e in result.get("entry") or []:
        status = (e.get("response") or {}).get("status", "missing")
        statuses[status.split()[0]] += 1

    summary = ", ".join(f"{n} × {s}" for s, n in sorted(statuses.items()))
    print(f"Loaded {entry_count} entries ({summary})")

    failures = sum(n for s, n in statuses.items() if not s.startswith("2"))
    if failures:
        print(f"\n{failures} entries did not return 2xx — see HAPI logs", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
