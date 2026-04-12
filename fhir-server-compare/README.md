# FHIR Server Compare: HAPI vs Google Cloud Healthcare API

A runnable companion to the blog post [Same FHIR, Different Answers: HAPI vs Google Cloud Healthcare API](https://mock.health/blog/hapi-vs-gcp-healthcare-api).

Load one Synthea patient into a local HAPI server, run 10 FHIR queries, and see the divergences the post describes — on your own machine, against your own data. The HAPI side runs in 90 seconds with one Docker command. The GCP side is opt-in via env var.

## Prerequisites

1. Docker (for local HAPI)
2. Python 3.10+
3. ~500 MB disk for the HAPI Docker image
4. **Optional, for the GCP column:** a [Google Cloud Healthcare API FHIR R4 store](https://cloud.google.com/healthcare-api/docs/how-tos/fhir) and Application Default Credentials

## Run

```bash
# 1. Start HAPI locally (FHIR R4, in-memory H2 database)
docker run -d --name hapi -p 8080:8080 hapiproject/hapi:latest
# Wait ~25 seconds for startup. Verify with:
curl -sf http://localhost:8080/fhir/metadata > /dev/null && echo "HAPI ready"

# 2. Install Python deps
pip install -r requirements.txt

# 3. Load one Synthea patient (171 resources, transaction bundle)
export HAPI_BASE_URL=http://localhost:8080/fhir
python load_bundle.py

# 4. Run the comparison
python compare.py
```

You should see a 10-row markdown table at the end of the run. With GCP disabled, the GCP columns show `—` and the Verdict column shows the expected GCP behavior pulled from `queries.yaml`. Set `GCP_FHIR_STORE_URL` and re-run to fill in the GCP side (see below).

## What It Demonstrates

Each row backs up a specific section of the blog post. The 10 queries are not arbitrary — they are the smallest set that surfaces every structural finding the post claims.

| # | Query | Blog claim |
|---|-------|------------|
| 1 | `capability_statement` | CapabilityStatement shape diff — both servers return a valid `CapabilityStatement` resource, but with different top-level fields. |
| 2 | `observation_search_default` | `Bundle.total` is `null` on HAPI by default. GCP always populates it. |
| 3 | `observation_search_total_accurate` | The fix — passing `_total=accurate` makes HAPI return the count. |
| 4 | `q7_error_unsupported_param` | **The silent-ignore.** HAPI 400s on a misspelled search parameter. GCP returns a 200 with the unfiltered result set. The most dangerous DX divergence in the post. |
| 5 | `observation_by_code` | `Observation?code=8480-6` (systolic BP) returns 0 on both. Synthea encodes BP as a panel — the systolic code lives in `component[]`, not at the top level. |
| 6 | `q1_uscore_observation_combo` | The fix — `combo-code` (US Core extension) matches `code` OR `component.code`. Returns the BP panels query #5 misses. |
| 7 | `q2_history_type` | `Patient/_history` works on HAPI. GCP returns `400 invalid ID '_history'`. |
| 8 | `q6_expand_valueset` | `ValueSet/$expand` exists on HAPI. GCP returns `400 invalid ID '$expand'`. |
| 9 | `q6_lookup_loinc` | `CodeSystem/$lookup` exists on HAPI. GCP returns `400 invalid ID '$lookup'`. Both fail in this reproducer for **different reasons** (HAPI: not loaded, GCP: not implemented) — that is the point. |
| 10 | `patient_revinclude_wildcard` | `_revinclude=*` is HAPI-only. GCP rejects the wildcard. |

## Example output

Here is what the HAPI-only run looks like with the bundle loaded:

```
Running 10 queries against:
  HAPI: http://localhost:8080/fhir
  GCP:  (disabled)

  [1/10] capability_statement
  [2/10] observation_search_default
  [3/10] observation_search_total_accurate
  [4/10] q7_error_unsupported_param
  [5/10] observation_by_code
  [6/10] q1_uscore_observation_combo
  [7/10] q2_history_type
  [8/10] q6_expand_valueset
  [9/10] q6_lookup_loinc
  [10/10] patient_revinclude_wildcard

| # | Query                              | HAPI status | HAPI total | HAPI entries | Verdict (expected GCP)                              |
|---|------------------------------------|-------------|------------|--------------|-----------------------------------------------------|
| 1 | capability_statement               | 200         | —          | —            | different top-level fields (description, url, ...) |
| 2 | observation_search_default         | 200         | null       | 10           | total populated (GCP always returns total)         |
| 3 | observation_search_total_accurate  | 200         | 37         | 1            | total = 37 (matched-volume)                        |
| 4 | q7_error_unsupported_param         | 400         | —          | —            | 200 with full unfiltered Patient list ⚠            |
| 5 | observation_by_code                | 200         | 0          | 0            | 0 (same — code parameter excludes component)       |
| 6 | q1_uscore_observation_combo        | 200         | 3          | 1            | 3+ (combo-code matches BP panel components)        |
| 7 | q2_history_type                    | 200         | 1          | 1            | 400 invalid ID '_history'                          |
| 8 | q6_expand_valueset                 | 404         | —          | —            | 400 invalid ID '$expand'                           |
| 9 | q6_lookup_loinc                    | 404         | —          | —            | 400 invalid ID '$lookup'                           |
|10 | patient_revinclude_wildcard        | 200         | 1          | 162          | 400 invalid _revinclude query: *                   |
```

The columns above are abbreviated for readability — `compare.py` prints the full table with separate HAPI and GCP columns.

The interesting rows are #4, #6, #7, #8, #9, and #10. Read them against the blog post and you should be able to verify each claim line-by-line.

## Files

| File | Purpose |
|------|---------|
| `compare.py` | Query runner: loads `queries.yaml`, hits HAPI (and GCP if enabled), diffs the responses, prints a markdown table |
| `load_bundle.py` | POSTs the transaction bundle to HAPI |
| `queries.yaml` | 10 hand-picked queries with `expected_hapi` / `expected_gcp` annotations |
| `requirements.txt` | `httpx`, `PyYAML`. `google-auth` is optional, only needed for the GCP column |
| `data/Aurelio_Whorton_transaction.json` | Synthea patient as a FHIR transaction bundle (171 entries) — ready to POST |
| `data/Aurelio_Whorton_collection.json` | The original Synthea collection bundle, shipped alongside for transparency. Diff the two files to see how the transaction wrapper differs |

## Enabling the GCP column (optional)

The reproducer runs HAPI-only by default because GCP requires a project, a billing account, and a FHIR store. If you have those, you can fill in the GCP column:

```bash
# 1. Create a Healthcare API FHIR store
#    https://cloud.google.com/healthcare-api/docs/how-tos/fhir

# 2. Authenticate to your account
gcloud auth application-default login

# 3. Install the optional GCP dependency
pip install google-auth

# 4. Tell compare.py where to find your FHIR store
export GCP_FHIR_STORE_URL="https://healthcare.googleapis.com/v1/projects/PROJECT/locations/us-central1/datasets/DATASET/fhirStores/STORE"

# 5. Re-run
python compare.py
```

You will hit the **strip rules** the moment you try to load `data/Aurelio_Whorton_transaction.json` into a GCP store with `load_bundle.py` (after pointing it at GCP). That failure is the demonstration — see the next section.

## The five strip rules (why you only hit them on GCP)

GCP Healthcare API enforces FHIR R4 validation that HAPI lets slide. Loading the same Synthea bundle into HAPI works as-is. Loading it into GCP fails until you remove these resource types:

| Type | Why GCP rejects it |
|------|--------------------|
| `Claim` | GCP requires `Claim.diagnosis[x]` — Synthea sometimes emits `Claim.diagnosis` without the polymorphic inner field. GCP returns `HTTP 400 unparseable_resource`. HAPI persists. |
| `ExplanationOfBenefit` | Same root cause, same failure mode. |
| `Questionnaire` | Every Synthea bundle ships the same canonical URL `http://loinc.org/q/96842-0` (PHQ-9). GCP treats canonical URLs as globally unique and rejects duplicates with `HTTP 409 conflict` after the first one. HAPI silently allows duplicates. |
| `QuestionnaireResponse` | Has a `urn:uuid` reference to the stripped Questionnaire. GCP rejects the entire transaction with `invalid_references`. |
| `Provenance` | Synthea Provenance resources list every resource they touched in `Provenance.target`, including the stripped Questionnaire. GCP rejects with the same `invalid_references` error. |

For the bundle in this directory (`Aurelio_Whorton_collection.json`, 171 entries):

```
Claim:                15 entries  ← STRIP for GCP
ExplanationOfBenefit: 15 entries  ← STRIP for GCP
Questionnaire:         1 entry    ← STRIP for GCP
QuestionnaireResponse: 1 entry    ← STRIP for GCP
Provenance:            1 entry    ← STRIP for GCP
                      ─────
                      33 entries (19% of the bundle)
```

About one in five resources in a normal Synthea patient bundle has to be removed before GCP will accept the import. On a more chronic patient (decades of claims) the strip rate climbs above 30%.

You can verify this yourself by running `python load_bundle.py` with `HAPI_BASE_URL` pointed at your GCP FHIR store base URL. The first few resources will load and then the transaction will fail with one of the errors above. That **is** the strip rule demonstration. The blog post lists the full `--strip-types` workaround used in the matched-volume run.

## Notes

- **One patient, not a thousand.** The blog used 1,000 patients across two cloud-hosted servers. This reproducer uses one patient against local Docker so you can run it in 90 seconds without a GCP bill. The behavioral findings (silent-ignore, operations support, `_revinclude=*`, `Bundle.total`) surface on the first query — volume is not required.
- **Latency is not measured here.** This is a single-threaded sample-of-one runner against managed services with cold caches. The blog post deliberately avoids latency claims for the same reason. The script does record `latency_ms` per query but the value is informational, not a benchmark.
- **No writes except the initial load.** `compare.py` is GET-only. The blog's full catalog includes a few POST queries (`$validate`, `Bundle` of GETs); this minimal subset omits them to keep the GET-only mental model simple.
- **No mock.health credentials needed.** This sample runs against your own HAPI Docker container. mock.health is not in the loop.
- **Want to add a query?** Edit `queries.yaml` and re-run. The schema is documented at the top of the file. Each entry takes ~10 lines.
- **The full 39-query catalog** organized around [Darren Devitt's nine FHIR architecture decision questions](https://darrendevitt.com/) lives in the [fhir-studio repo](https://github.com/mock-health/fhir-studio) — this sample is the trust-building subset.
