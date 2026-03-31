#!/bin/bash
set -euo pipefail

# Clone and build a fresh Synthea, then generate 10 patients.
# Prerequisites: Java 11+ and git.

SYNTHEA_DIR="synthea"

if [ -d "$SYNTHEA_DIR" ]; then
  echo "synthea/ already exists. Delete it first if you want a fresh clone."
  exit 1
fi

echo "=== Cloning Synthea ==="
git clone --depth 1 https://github.com/synthetichealth/synthea.git

echo ""
echo "=== Building (this takes ~45 seconds) ==="
cd "$SYNTHEA_DIR"
./gradlew build -x test

echo ""
echo "=== Generating 10 patients (seed 42, Massachusetts) ==="
./run_synthea -p 10 -s 42 Massachusetts Boston

echo ""
echo "Generated $(ls output/fhir/*.json 2>/dev/null | wc -l) patient bundles in synthea/output/fhir/"
echo "Run ./inspect.sh to see what you got."
