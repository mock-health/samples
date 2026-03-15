# mock.health samples

Example apps and code snippets for building with the [mock.health](https://mock.health) FHIR sandbox.

## Samples

| Sample | Description |
|--------|-------------|
| [smart-on-fhir-vital-signs](./smart-on-fhir-vital-signs/) | Single-page SMART on FHIR app — OAuth 2.0 + PKCE auth, vital signs chart |

## Quick Start

```bash
git clone https://github.com/mock-health/samples.git
cd samples
python3 -m http.server 8080
```

Then open the sample you want in your browser (e.g. `http://localhost:8080/smart-on-fhir-vital-signs/index.html`).

## Requirements

- A [mock.health](https://mock.health) account (free)
- A registered SMART app with a Client ID
- Python 3 (for the local dev server) or any static file server
