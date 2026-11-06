#!/usr/bin/env bash
# Run a phase in bounded-memory chunks until no worlds remain: scripts/run_phase.sh configs/pilot.yaml [chunk]
set -uo pipefail
cfg="$1"
chunk="${2:-10}"
export MPLBACKEND=Agg
while true; do
  uv run --locked python -m mmm_benchmark.cli run --config "$cfg" --resume --max-worlds "$chunk"
  rc=$?
  [[ $rc -eq 3 ]] && continue
  exit $rc
done
