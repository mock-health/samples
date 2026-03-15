# SMART on FHIR Vital Signs Chart

A single-page SMART on FHIR app that authenticates via OAuth 2.0 + PKCE, fetches vital sign Observations, and renders interactive line charts. No build step — one HTML file, one CDN dependency (Chart.js).

## Prerequisites

1. A [mock.health](https://mock.health) account (free)
2. A registered SMART app — go to [Sandbox → Register App](https://mock.health/sandbox/apps/new)
   - Set **Redirect URI** to `http://localhost:8080/smart-on-fhir-vital-signs/index.html`
   - Enable scopes: `launch/patient`, `patient/Patient.read`, `patient/Observation.read`, `openid`, `fhirUser`
   - Copy the **Client ID**

## Run

```bash
# From the repo root
python3 -m http.server 8080

# Open in browser
open http://localhost:8080/smart-on-fhir-vital-signs/index.html
```

1. Paste your Client ID
2. Click **Connect**
3. Approve access in the consent screen
4. Browse vital signs (heart rate, blood pressure, SpO2, temperature, weight, BMI)

## What It Demonstrates

- SMART App Launch Framework (standalone launch)
- PKCE (Proof Key for Code Exchange) using Web Crypto API
- FHIR `.well-known/smart-configuration` discovery
- OAuth 2.0 authorization code flow
- Fetching `Patient` and `Observation` resources with bearer token auth
- Parsing LOINC-coded vital signs including blood pressure panel components

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `index.html` | ~280 | Complete app — HTML, CSS, and JS in one file |

## How It Works

1. **Discovery** — fetches `/.well-known/smart-configuration` to find authorize + token endpoints
2. **PKCE** — generates a code verifier + SHA-256 challenge (RFC 7636)
3. **Authorize** — redirects to the authorization server with scopes, PKCE challenge, and state
4. **Callback** — exchanges the authorization code for an access token
5. **Fetch** — loads `Patient/{id}` and `Observation?category=vital-signs` with the bearer token
6. **Render** — groups observations by LOINC code, renders Chart.js line charts with tab navigation

## Vital Signs Supported

| Vital | LOINC | Notes |
|-------|-------|-------|
| Heart Rate | 8867-4 | bpm |
| Blood Pressure | 85354-9 | Panel with systolic (8480-6) + diastolic (8462-4) components |
| Temperature | 8310-5 | °F |
| SpO2 | 2708-6 | % |
| Weight | 29463-7 | kg |
| BMI | 39156-5 | kg/m² |
