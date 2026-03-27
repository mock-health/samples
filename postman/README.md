# mock.health API Collection

34 pre-configured requests for the mock.health FHIR R4 API. Works with Postman, Bruno, Insomnia, and Hoppscotch.

## Import

Import directly from URL in any REST client:

```
https://raw.githubusercontent.com/mock-health/samples/main/postman/mock-health-fhir-api.postman_collection.json
```

Or download the file and import manually.

## Setup

1. Sign up at [mock.health](https://mock.health) (free)
2. In Postman, open the collection and go to **Variables**
3. You need to authenticate first — either:
   - **Option A (browser):** Log in at mock.health, go to Settings, copy your API key, paste it as the `api_key` variable
   - **Option B (Postman):** If you already have a token, run **Getting Started > Generate API Key** — it auto-saves the key

## Workflow

The collection is ordered for a natural getting-started flow:

1. **Getting Started** — verify your account and get an API key
2. **FHIR Search & Read** — explore patients, observations, conditions, medications
3. **FHIR Write** — create/update/delete resources (Pro plan)
4. **Bulk Export** — export patient data as NDJSON
5. **Validation** — validate resources against US Core 6.1.0
6. **Media** — retrieve and render DICOM images
7. **SMART on FHIR** — OAuth 2.0 endpoints for app authorization
8. **SMART App Management** — register and manage SMART app credentials

## Auto-populated Variables

Several requests auto-save variables from responses:

| Request | Saves |
|---------|-------|
| Generate API Key | `api_key` |
| Search Patients | `patient_id` (first result) |
| Kick Off Patient Export | `export_job_id` |
| Register App | `app_id` |

## Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `base_url` | API base URL | `https://api.mock.health` |
| `api_key` | Your API key (`sk_live_...`) | — |
| `patient_id` | FHIR Patient resource ID | — |
| `app_id` | SMART app ID | — |
| `media_id` | Media resource ID | — |
| `export_job_id` | Bulk export job ID | — |
| `group_id` | FHIR Group ID for bulk export | `all-patients` |
| `access_token` | SMART OAuth access token | — |
