# Synthea Module Author

Create valid Synthea disease modules with grounded medical codes. Every code is validated against a real terminology server — never hallucinated from training data.

## When to use this skill

- "Create a Synthea module for celiac disease"
- "Add a rare condition to Synthea"
- "Write a module for [condition] with labs, meds, and encounters"
- "Extend the diabetes module to include CKD progression"

## Before you start

You need a cloned and built copy of Synthea:

```bash
git clone https://github.com/synthetichealth/synthea.git
cd synthea
./gradlew build -x test   # Java 11+ required, ~45 seconds
```

## Module JSON Schema

Every Synthea module is a JSON file in `src/main/resources/modules/`. Top-level structure:

```json
{
  "name": "Module Display Name",
  "remarks": ["Optional explanation of what this module models"],
  "states": {
    "Initial": { "type": "Initial", "direct_transition": "First_State" },
    "...": "...",
    "Terminal": { "type": "Terminal" }
  },
  "gmf_version": 2
}
```

### State types you'll use

| Type | Purpose | Requires codes? |
|------|---------|----------------|
| `Initial` | Module entry point | No |
| `Terminal` | Module exit point | No |
| `Simple` | Logic/routing node (no clinical action) | No |
| `Delay` | Time passage | No |
| `Guard` | Conditional gate (waits until condition is true) | No |
| `Encounter` | Start a clinical encounter | Yes (SNOMED) |
| `EncounterEnd` | End encounter | No |
| `ConditionOnset` | Diagnose a condition | Yes (SNOMED) |
| `ConditionEnd` | Resolve a condition | No (references prior onset) |
| `MedicationOrder` | Prescribe a medication | Yes (RxNorm) |
| `MedicationEnd` | Stop a medication | No (references prior order) |
| `Observation` | Lab result or vital sign | Yes (LOINC) |
| `DiagnosticReport` | Lab panel or report | Yes (LOINC) |
| `Procedure` | Medical procedure | Yes (SNOMED) |
| `CarePlanStart` | Begin care plan | Yes (SNOMED) |
| `CarePlanEnd` | End care plan | No |
| `SetAttribute` | Store a patient variable | No |
| `Counter` | Increment/decrement a value | No |
| `CallSubmodule` | Call another module | No |
| `Death` | Patient death | No |

### Transition types

**Direct** — always go to one state:
```json
"direct_transition": "Next_State"
```

**Conditional** — branch on a condition:
```json
"conditional_transition": [
  { "condition": { "condition_type": "Age", "operator": ">", "quantity": 50, "unit": "years" }, "transition": "Older_Path" },
  { "transition": "Default_Path" }
]
```

**Distributed** — probabilistic branching:
```json
"distributed_transition": [
  { "distribution": 0.01, "transition": "Gets_Disease" },
  { "distribution": 0.99, "transition": "No_Disease" }
]
```

**Complex** — conditions with distributions:
```json
"complex_transition": [
  {
    "condition": { "condition_type": "Attribute", "attribute": "risk_factor", "operator": "is not nil" },
    "distributions": [
      { "distribution": 0.05, "transition": "Gets_Disease" },
      { "distribution": 0.95, "transition": "No_Disease" }
    ]
  },
  { "transition": "No_Disease" }
]
```

### Condition types for transitions and guards

| Condition type | Example |
|----------------|---------|
| `Age` | `{ "condition_type": "Age", "operator": ">", "quantity": 18, "unit": "years" }` |
| `Gender` | `{ "condition_type": "Gender", "gender": "F" }` |
| `Date` | `{ "condition_type": "Date", "operator": ">=", "year": 2000 }` |
| `Attribute` | `{ "condition_type": "Attribute", "attribute": "some_flag", "operator": "is not nil" }` |
| `PriorState` | `{ "condition_type": "PriorState", "name": "Some_State" }` |
| `Active Condition` | `{ "condition_type": "Active Condition", "codes": [{ "system": "SNOMED-CT", "code": "...", "display": "..." }] }` |
| `And` / `Or` / `Not` | Nest other conditions with boolean logic |

## Code Systems

Every medical code in a module uses this format:

```json
{
  "system": "SNOMED-CT",
  "code": "396331005",
  "display": "Celiac disease (disorder)"
}
```

| System | URI | Used for |
|--------|-----|----------|
| SNOMED-CT | `http://snomed.info/sct` | Conditions, procedures, findings, body sites, encounter types |
| LOINC | `http://loinc.org` | Lab observations, vital signs, diagnostic reports |
| RxNorm | `http://www.nlm.nih.gov/research/umls/rxnorm` | Medications |
| CVX | `http://hl7.org/fhir/sid/cvx` | Vaccines |

## CRITICAL: Code Grounding Rules

**NEVER generate a medical code from memory.** LLMs pattern-match codes from training data. Sometimes they're correct, sometimes they're plausible but don't exist. You cannot tell by looking at a code whether it's real.

**ALWAYS validate every code** against the public FHIR terminology server at tx.fhir.org before writing it into a module.

### Validate a code

```bash
# Validate a SNOMED code
curl -s "https://tx.fhir.org/r4/CodeSystem/\$validate-code?system=http://snomed.info/sct&code=396331005" \
  | jq '.parameter[] | select(.name=="result" or .name=="display")'

# Validate a LOINC code
curl -s "https://tx.fhir.org/r4/CodeSystem/\$validate-code?system=http://loinc.org&code=31017-7" \
  | jq '.parameter[] | select(.name=="result" or .name=="display")'

# Validate an RxNorm code
curl -s "https://tx.fhir.org/r4/CodeSystem/\$validate-code?system=http://www.nlm.nih.gov/research/umls/rxnorm&code=328383" \
  | jq '.parameter[] | select(.name=="result" or .name=="display")'
```

A valid code returns `"valueBoolean": true` and a `"display"` parameter with the canonical name. An invalid code returns `"valueBoolean": false`.

**CRITICAL: Validating existence is not enough.** A code can be valid but mean something completely different from what you intended. `12866006` is a valid SNOMED code — it's pneumococcal vaccination, not duodenal biopsy. After validating, **always compare the canonical display from tx.fhir.org against what you wrote in the module.** If they don't match, the code is wrong even though it's "valid."

```bash
# Example: check that the display matches your intent
curl -s "https://tx.fhir.org/r4/CodeSystem/\$validate-code?system=http://snomed.info/sct&code=12866006" \
  | jq '.parameter[] | select(.name=="display") | .valueString'
# Returns: "Pneumococcal vaccination" — NOT "Biopsy of duodenum"
```

For every code: validate it exists, then read the display and confirm it describes what you think it describes. This is the step that catches LLM hallucinations.

### Search for codes

When you need to find the right code for a concept:

```bash
# Search SNOMED for a term
curl -s "https://tx.fhir.org/r4/ValueSet/\$expand?url=http://snomed.info/sct?fhir_vs&filter=celiac+disease&count=5" \
  | jq '.expansion.contains[] | {code, display}'

# Search LOINC for a term
curl -s "https://tx.fhir.org/r4/ValueSet/\$expand?url=http://loinc.org/vs&filter=tissue+transglutaminase&count=5" \
  | jq '.expansion.contains[] | {code, display}'

# Search RxNorm for a medication
curl -s "https://tx.fhir.org/r4/ValueSet/\$expand?url=http://www.nlm.nih.gov/research/umls/rxnorm?fhir_vs&filter=ferrous+sulfate&count=5" \
  | jq '.expansion.contains[] | {code, display}'
```

### Rate limiting

tx.fhir.org is a public, free service. Be respectful:
- Add a brief pause between requests (0.5-1 second)
- Cache results within the session — don't re-validate the same code twice
- If you get rate limited (HTTP 429), wait 5 seconds and retry

## Workflow

When asked to create a module:

### Step 1: Check existing modules

```bash
ls synthea/src/main/resources/modules/ | grep -i "<condition>"
grep -rl "<condition>" synthea/src/main/resources/modules/ 2>/dev/null
```

If a module already exists, read it and tell the user what's there. Ask whether they want to extend it or create a new one.

### Step 2: Research the condition

Before writing any JSON, understand:
- Prevalence by age and sex (for transition probabilities)
- Diagnostic criteria (what labs, imaging, or procedures confirm the diagnosis)
- Standard treatment pathway (first-line meds, escalation, monitoring)
- Condition progression (does it resolve? is it lifelong? what complications?)

Use WebSearch if available. If not, state what you know and flag uncertainty.

### Step 3: Look up every code

For each clinical concept in the module, search tx.fhir.org and validate the code. Do this BEFORE writing the module JSON. Build a code inventory:

```
Concept                    System      Code        Display (from tx.fhir.org)
─────────────────────────  ──────────  ──────────  ─────────────────────────────
Celiac disease             SNOMED-CT   396331005   Celiac disease (disorder)
tTG IgA antibody           LOINC       31017-7     Tissue transglutaminase IgA Ab
Endoscopy of duodenum      SNOMED-CT   386813002   Endoscopy of duodenum
...
```

### Step 4: Generate the module JSON

Write the module following the schema above. Place it in `synthea/src/main/resources/modules/`. Use validated codes only.

Key patterns:
- Start with an `Initial` state and an age/prevalence gate
- Use `distributed_transition` for prevalence-based onset (calibrate against CDC/CMS data)
- Wrap clinical actions (labs, meds, procedures) inside `Encounter`/`EncounterEnd` pairs
- Use `SetAttribute` to track patient state across module cycles
- End chronic conditions with a monitoring loop (`Delay` → `Encounter` → `Delay`)
- Use `target_encounter` on ConditionOnset, Observation, Procedure, MedicationOrder to link them to the encounter

### Step 5: Validate the module

```bash
# Structural validation — Synthea's build catches bad JSON
cd synthea && ./gradlew build -x test

# Functional test — generate a patient using only this module
./run_synthea -m <module_name> -p 1 -s 42 -a 30-60

# Check output
jq '.entry[].resource.resourceType' output/fhir/*.json | sort | uniq -c | sort -rn
```

If the build fails, read the error — it usually points to the exact JSON issue (missing required field, invalid state type, bad transition target).

### Step 6: Inspect the generated FHIR

Verify the module produced the expected resources:

```bash
# Check conditions
jq -r '.entry[].resource | select(.resourceType=="Condition") | .code.coding[0].display' output/fhir/*.json

# Check observations/labs
jq -r '.entry[].resource | select(.resourceType=="Observation") | .code.coding[0].display' output/fhir/*.json

# Check medications
jq -r '.entry[].resource | select(.resourceType=="MedicationRequest") | .medicationCodeableConcept.coding[0].display' output/fhir/*.json

# Check procedures
jq -r '.entry[].resource | select(.resourceType=="Procedure") | .code.coding[0].display' output/fhir/*.json
```

## Common pitfalls

1. **Forgetting `target_encounter`** — ConditionOnset, Observation, Procedure, and MedicationOrder states need `"target_encounter": "Encounter_State_Name"` to link them to the active encounter. Without it, the resource is orphaned.

2. **Not ending encounters** — Every `Encounter` state needs a corresponding `EncounterEnd`. Without it, Synthea will error or produce corrupt bundles.

3. **Prevalence miscalibration** — A `distributed_transition` with `0.01` means 1% of the population per timestep (default 1 week). Over a 70-year life, that's not 1% prevalence. Use Synthea's `"remarks"` to document your prevalence math.

4. **Missing Terminal** — Every execution path must eventually reach a `Terminal` state or the module loops forever.

5. **Code system names** — Synthea uses `"SNOMED-CT"` not `"http://snomed.info/sct"` in the `system` field. The URI goes in FHIR export, not in the module JSON.

6. **`exporter.years_of_history` hides older events** — By default Synthea filters exported resources to recent history. If your module's procedures or early encounters are missing from the output, run with `--exporter.years_of_history=0` to keep everything.

7. **Procedures need `duration`** — Add `"duration": { "low": N, "high": M, "unit": "minutes" }` to Procedure states. Without it, some exporters may skip them.

8. **`assign_to_attribute` on ConditionOnset** — If procedures or medications reference the condition via `reason`, add `"assign_to_attribute": "condition_name"` to the ConditionOnset state so the reference resolves.

## Related tools

- **`/fhir` Claude Code skill** — for FHIR development beyond Synthea modules (R4, IGs, FSH, SMART on FHIR, validation)
- **[Inferno](https://inferno.healthit.gov/)** — ONC FHIR server compliance testing
- **[Synthea Module Builder](https://synthetichealth.github.io/module-builder/)** — GUI for visual module authoring
- **[tx.fhir.org](https://tx.fhir.org)** — public FHIR terminology server (no account needed)
- **[mock.health](https://mock.health)** — synthetic patients with population-level realism (Markov models trained on millions of real patient journeys)
