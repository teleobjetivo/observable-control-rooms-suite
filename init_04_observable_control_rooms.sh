#!/bin/bash
set -euo pipefail

BASE_DIR="04_observable_control_rooms"

PROJECTS=(
  "orion-control-room"
  "decision-intelligence-live"
  "anomaly-radar-control"
  "executive-report-factory"
  "ops-cell-lite"
)

mkdir -p "$BASE_DIR"
cd "$BASE_DIR"

for p in "${PROJECTS[@]}"; do
  mkdir -p "$p"/{data,src,outputs,img,notebooks}
  touch "$p"/{README.md,app.py}
done

echo "OK: created projects:"
ls -1
