# SMART on FHIR Vital Signs Chart

A single-page SMART on FHIR app that authenticates via OAuth 2.0 + PKCE, fetches vital sign Observations, and renders interactive line charts. No build step — plain HTML files, one CDN dependency (Chart.js).

It demonstrates **both** SMART launch modes:

- **Standalone launch** (`index.html`) — the app starts the flow and the user picks a patient. No EHR required.
- **EHR launch** (`launch.html`) — an EHR launches the app with a patient already in context, the way a clinical app opens from inside Epic/Cerner.

## Prerequisites

1. A [mock.health](https://mock.health) account (free)
2. A registered SMART app — go to [Sandbox → Register App](https://mock.health/sandbox/apps/new)
   - Set **Redirect URI** to `http://localhost:8080/smart-on-fhir-vital-signs/index.html`
   - For EHR launch, also set **Launch URL** to `http://localhost:8080/smart-on-fhir-vital-signs/launch.html`
   - Enable scopes: `launch`, `launch/patient`, `patient/Patient.rs`, `patient/Observation.rs`, `openid`, `fhirUser`
   - Copy the **Client ID**

## Run

```bash
# From the repo root
python3 -m http.server 8080
```

### Standalone launch

```bash
open http://localhost:8080/smart-on-fhir-vital-signs/index.html
```

1. Paste your Client ID
2. Click **Connect**
3. Approve access in the consent screen
4. Browse vital signs (heart rate, blood pressure, SpO2, temperature, weight, BMI)

### EHR launch

The EHR — not the app — kicks this off, so you start from the launcher, not the file.

1. Open `launch.html` and set the `CLIENT_ID` constant near the top to your app's Client ID.
2. Go to **[Sandbox → SMART Launcher](https://mock.health/sandbox/smart)** on mock.health.
3. Select this app, pick a patient, choose **EHR Launch**, and click **Launch**.
4. mock.health mints a one-time launch token and opens
   `launch.html?iss=https://api.mock.health/fhir&launch=<token>`. The patient is
   already in context — no picker — and you land on the chart for that patient.

> **What the launcher is doing:** it `POST`s to `/api/smart/launch` with your
> `client_id` + the chosen `patient_id`, gets back your Launch URL with `iss` and
> a single-use `launch` token appended, and opens it. That is exactly what a real
> EHR does when a clinician opens your app from a patient's chart.

## What It Demonstrates

- SMART App Launch Framework — **both** standalone launch and EHR launch
- The EHR launch handshake: `iss` + single-use `launch` token → pre-set patient context (no patient picker)
- PKCE (Proof Key for Code Exchange) using Web Crypto API
- FHIR `.well-known/smart-configuration` discovery
- OAuth 2.0 authorization code flow
- Fetching `Patient` and `Observation` resources with bearer token auth
- Parsing LOINC-coded vital signs including blood pressure panel components

## Files

| File | Purpose |
|------|---------|
| `index.html` | The app itself — standalone launch screen, OAuth callback handler, and the chart UI |
| `launch.html` | EHR launch entry point — reads `iss` + `launch`, then redirects into the same OAuth flow |

`launch.html` is purely additive: it writes the same `sessionStorage` keys that
`index.html`'s callback handler already reads, so the two files share one session
and `index.html` needs no special-casing for EHR launch.

## How It Works

**Standalone (`index.html`):**

1. **Discovery** — fetches `/.well-known/smart-configuration` to find authorize + token endpoints
2. **PKCE** — generates a code verifier + SHA-256 challenge (RFC 7636)
3. **Authorize** — redirects with scopes (incl. `launch/patient`), PKCE challenge, and state
4. **Callback** — exchanges the authorization code for an access token
5. **Fetch** — loads `Patient/{id}` and `Observation?category=vital-signs` with the bearer token
6. **Render** — groups observations by LOINC code, renders Chart.js line charts with tab navigation

**EHR launch (`launch.html` → `index.html`):**

1. **Launch** — the EHR opens `launch.html?iss=<fhir-base>&launch=<token>`
2. **Discovery** — runs against `iss` (never a hardcoded server)
3. **Authorize** — redirects with the `launch` scope **and** the `launch` token, `redirect_uri` pointing at `index.html`
4. The server resolves the launch token to the patient already in context — no picker — and redirects to `index.html`
5. From there it's the same callback → fetch → render path as standalone

The only differences between the two modes are *who starts the flow* and *how the
patient is chosen*. Discovery, PKCE, token exchange, and rendering are identical.

## Vital Signs Supported

| Vital | LOINC | Notes |
|-------|-------|-------|
| Heart Rate | 8867-4 | bpm |
| Blood Pressure | 85354-9 | Panel with systolic (8480-6) + diastolic (8462-4) components |
| Temperature | 8310-5 | °F |
| SpO2 | 2708-6 | % |
| Weight | 29463-7 | kg |
| BMI | 39156-5 | kg/m² |

## Hosting on GitHub Pages (instead of localhost)

`localhost` is fine for one developer, but for a class — where everyone needs a
stable, shareable URL — GitHub Pages serves these static files for free over HTTPS.
No server to run.

1. **Fork or copy** these files into a repo, e.g. `your-name/smart-vitals`, keeping
   `index.html` and `launch.html` together in one folder (the repo root is simplest).
2. In the repo, go to **Settings → Pages**, set **Source** to *Deploy from a branch*,
   choose `main` / `/ (root)`, and save. After a minute your app is live at:

   ```
   https://your-name.github.io/smart-vitals/index.html
   https://your-name.github.io/smart-vitals/launch.html
   ```

3. **Register a SMART app** on mock.health using those HTTPS URLs:
   - **Redirect URI:** `https://your-name.github.io/smart-vitals/index.html`
   - **Launch URL:** `https://your-name.github.io/smart-vitals/launch.html`
4. Paste the new **Client ID** into the `CLIENT_ID` constant in `launch.html`,
   commit, and push. (Standalone mode reads the Client ID from the on-screen field,
   so it needs no edit.)

The redirect and launch URLs you register must match the deployed URLs **exactly** —
scheme, host, and path. A trailing-slash or `http` vs `https` mismatch is the most
common reason the authorization server rejects the redirect.

> **Teaching tip:** students can each fork the repo, enable Pages, and register their
> own app in a few minutes — no local web server, no shared state, and every app
> gets its own HTTPS origin, which is exactly what real SMART app registration expects.
