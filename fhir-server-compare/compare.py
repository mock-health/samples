#!/usr/bin/env python3
"""Run a small set of FHIR queries against HAPI (and optionally GCP
Healthcare API), diff the responses, print a markdown table to stdout.

This is the runnable companion to the blog post
"Same FHIR, Different Answers: HAPI vs Google Cloud Healthcare API"
(https://mock.health/blog/hapi-vs-gcp-healthcare-api). Reader runs:

    docker run -d -p 8080:8080 hapiproject/hapi:latest
    pip install -r requirements.txt
    export HAPI_BASE_URL=http://localhost:8080/fhir
    python load_bundle.py
    python compare.py

...and sees the divergences the post talks about, against their own
HAPI server. The GCP column requires GCP_FHIR_STORE_URL + ADC; without
those, the script runs HAPI-only and shows the expected GCP behavior
from the YAML in the Verdict column.

Honest about scope: this is a single-patient single-workstation
single-shot reproducer. Latency numbers are not benchmark-quality. The
finding the script makes is structural: which queries succeed, which
fail, and what each backend's response shape looks like.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

SCRIPT_DIR = Path(__file__).parent
DEFAULT_QUERIES = SCRIPT_DIR / "queries.yaml"
FHIR_CONTENT_TYPE = "application/fhir+json"


# --------------------------------------------------------------------------
# YAML loader
# --------------------------------------------------------------------------


def load_queries(path: Path) -> list[dict]:
    try:
        import yaml  # type: ignore
    except ImportError:
        print("ERROR: PyYAML not installed. Run: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(2)
    data = yaml.safe_load(path.read_text())
    queries = data.get("queries") if isinstance(data, dict) else None
    if not isinstance(queries, list):
        print(f"ERROR: {path} must contain a top-level 'queries:' list", file=sys.stderr)
        sys.exit(2)
    return queries


# --------------------------------------------------------------------------
# GCP auth (optional)
# --------------------------------------------------------------------------


def gcp_token() -> str:
    """Fetch a GCP access token via Application Default Credentials.

    Reader runs `gcloud auth application-default login` once before
    enabling the GCP column. We do not impersonate a service account
    here — that's an internal-tooling concern from the fhir-studio repo
    that does not belong in a public reproducer.
    """
    try:
        from google.auth import default  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
    except ImportError:
        print(
            "ERROR: google-auth is not installed but GCP_FHIR_STORE_URL is set.\n"
            "  Run: pip install google-auth\n"
            "  Or unset GCP_FHIR_STORE_URL to run in HAPI-only mode.",
            file=sys.stderr,
        )
        sys.exit(2)
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


# --------------------------------------------------------------------------
# Per-backend response capture
# --------------------------------------------------------------------------


@dataclass
class BackendResponse:
    backend: str
    status_code: int
    ok: bool
    body: Any
    resource_type: str | None
    bundle_total: int | None
    entry_count: int | None
    latency_ms: int


def run_query(
    backend: str,
    base_url: str,
    query: dict,
    headers: dict[str, str],
    client: httpx.Client,
) -> BackendResponse:
    method = (query.get("method") or "GET").upper()
    path = query.get("path") or ""
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    params = query.get("params") or {}
    body = query.get("body")

    start = time.monotonic()
    try:
        if method == "POST":
            resp = client.post(url, params=params, json=body, headers=headers)
        else:
            resp = client.get(url, params=params, headers=headers)
    except httpx.RequestError as exc:
        return BackendResponse(
            backend=backend, status_code=0, ok=False, body=str(exc),
            resource_type=None, bundle_total=None, entry_count=None,
            latency_ms=int((time.monotonic() - start) * 1000),
        )

    latency_ms = int((time.monotonic() - start) * 1000)
    try:
        parsed = resp.json()
    except Exception:
        parsed = resp.text

    rt, total, ec = None, None, None
    if isinstance(parsed, dict):
        rt = parsed.get("resourceType")
        if rt == "Bundle":
            total = parsed.get("total")
            entries = parsed.get("entry") or []
            ec = len(entries) if isinstance(entries, list) else None

    return BackendResponse(
        backend=backend,
        status_code=resp.status_code,
        ok=200 <= resp.status_code < 300,
        body=parsed,
        resource_type=rt,
        bundle_total=total,
        entry_count=ec,
        latency_ms=latency_ms,
    )


# --------------------------------------------------------------------------
# Markdown table rendering
# --------------------------------------------------------------------------


def fmt_total(r: BackendResponse | None) -> str:
    if r is None:
        return "—"
    if r.bundle_total is None:
        return "null" if r.resource_type == "Bundle" else "—"
    return str(r.bundle_total)


def fmt_entries(r: BackendResponse | None) -> str:
    if r is None or r.entry_count is None:
        return "—"
    return str(r.entry_count)


def fmt_status(r: BackendResponse | None) -> str:
    if r is None:
        return "—"
    return str(r.status_code)


def render_table(rows: list[tuple[dict, BackendResponse, BackendResponse | None]]) -> str:
    out = []
    out.append(
        "| # | Query | Blog section | HAPI status | HAPI total | HAPI entries | "
        "GCP status | GCP total | GCP entries | Verdict |"
    )
    out.append(
        "|---|---|---|---|---|---|---|---|---|---|"
    )
    for i, (q, hapi, gcp) in enumerate(rows, start=1):
        name = q.get("name", "?")
        section = q.get("blog_section", "")
        verdict = compute_verdict(q, hapi, gcp)
        out.append(
            f"| {i} | `{name}` | {section} | "
            f"{fmt_status(hapi)} | {fmt_total(hapi)} | {fmt_entries(hapi)} | "
            f"{fmt_status(gcp)} | {fmt_total(gcp)} | {fmt_entries(gcp)} | "
            f"{verdict} |"
        )
    return "\n".join(out)


def compute_verdict(q: dict, hapi: BackendResponse, gcp: BackendResponse | None) -> str:
    if gcp is None:
        expected = q.get("expected_gcp", "—")
        return f"GCP disabled · expected: {expected}"
    if (
        hapi.status_code == gcp.status_code
        and hapi.resource_type == gcp.resource_type
        and hapi.bundle_total == gcp.bundle_total
        and hapi.entry_count == gcp.entry_count
    ):
        return "IDENTICAL ✅"
    diffs = []
    if hapi.status_code != gcp.status_code:
        diffs.append(f"status {hapi.status_code} vs {gcp.status_code}")
    if hapi.resource_type != gcp.resource_type:
        diffs.append(f"type {hapi.resource_type} vs {gcp.resource_type}")
    if hapi.bundle_total != gcp.bundle_total:
        diffs.append(f"total {hapi.bundle_total} vs {gcp.bundle_total}")
    if hapi.entry_count != gcp.entry_count:
        diffs.append(f"entries {hapi.entry_count} vs {gcp.entry_count}")
    return "DIVERGED · " + "; ".join(diffs)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", default=str(DEFAULT_QUERIES))
    parser.add_argument(
        "--hapi-url",
        default=os.environ.get("HAPI_BASE_URL", "http://localhost:8080/fhir"),
    )
    parser.add_argument("--gcp-url", default=os.environ.get("GCP_FHIR_STORE_URL"))
    args = parser.parse_args()

    queries_path = Path(args.queries)
    if not queries_path.exists():
        print(f"ERROR: queries file not found: {queries_path}", file=sys.stderr)
        return 2
    queries = load_queries(queries_path)

    gcp_enabled = bool(args.gcp_url)
    if not gcp_enabled:
        print(
            "GCP disabled. Set GCP_FHIR_STORE_URL and run "
            "`gcloud auth application-default login` (plus `pip install "
            "google-auth`) to enable the GCP column.\n"
        )

    hapi_headers = {"Accept": FHIR_CONTENT_TYPE, "Content-Type": FHIR_CONTENT_TYPE}
    gcp_headers: dict[str, str] = {}
    if gcp_enabled:
        token = gcp_token()
        gcp_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": FHIR_CONTENT_TYPE,
            "Content-Type": FHIR_CONTENT_TYPE,
        }

    gcp_fhir_base = (
        f"{args.gcp_url.rstrip('/')}/fhir" if gcp_enabled else ""
    )

    print(
        f"Running {len(queries)} queries against:\n"
        f"  HAPI: {args.hapi_url}\n"
        f"  GCP:  {gcp_fhir_base if gcp_enabled else '(disabled)'}\n"
    )

    rows: list[tuple[dict, BackendResponse, BackendResponse | None]] = []
    with httpx.Client(timeout=60.0) as client:
        for i, q in enumerate(queries, start=1):
            name = q.get("name", f"q{i}")
            print(f"  [{i}/{len(queries)}] {name}")
            hapi_resp = run_query("hapi", args.hapi_url, q, hapi_headers, client)
            gcp_resp = (
                run_query("gcp", gcp_fhir_base, q, gcp_headers, client)
                if gcp_enabled
                else None
            )
            rows.append((q, hapi_resp, gcp_resp))

    print()
    print(render_table(rows))
    print()
    if gcp_enabled:
        identical = sum(1 for _, h, g in rows if g is not None and compute_verdict({}, h, g).startswith("IDENTICAL"))
        print(f"{identical}/{len(rows)} queries identical, {len(rows) - identical} divergent")
    else:
        print(
            f"{len(rows)} queries run against HAPI. Set GCP_FHIR_STORE_URL to "
            "compare against GCP Healthcare API."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
