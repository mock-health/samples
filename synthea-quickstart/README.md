# Synthea Quickstart

Companion code for [How to Make Claude Write Valid Synthea Modules](https://mock.health/blog/synthea-best-worst-tool).

## Quickstart

```bash
# Clone + build + generate 10 patients
./generate.sh

# Analyze the output for clinical realism
python3 analyze.py
```

## Authoring custom modules

See the [synthea-module-skill](../synthea-module-skill/) for a Claude Code skill that authors valid Synthea modules with grounded medical codes.

```bash
claude install github:mock-health/samples/synthea-module-skill
claude "/synthea create a celiac disease module"
```

## What's here

| File | What it does |
|------|-------------|
| `generate.sh` | Clones [synthetichealth/synthea](https://github.com/synthetichealth/synthea), builds with Gradle, generates 10 patients with seed 42 |
| `analyze.py` | Population analysis: CDC prevalence comparison, comorbidity check, age bracket stats, medication variety, clinical absurdity detection |
