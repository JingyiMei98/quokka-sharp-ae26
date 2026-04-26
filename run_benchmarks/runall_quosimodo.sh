#!/usr/bin/env bash
set -euo pipefail

export LD_LIBRARY_PATH=/Quokka/Quasimodo/python_pkg:$LD_LIBRARY_PATH

export QUOKKA_CONFIG=config_gpmc.json

if [ $# -lt 1 ]; then
  echo "Usage: $0 <timeout>"
  exit 1
fi

TIMEOUT="$1"

if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
  echo "Error: timeout must be a non-negative integer"
  exit 1
fi

command -v jq >/dev/null 2>&1 || {
  echo "Error: jq is not installed"
  exit 1
}

update_timeout() {
  local file="$1"
  local tmp="${file}.tmp"
  jq ".TIMEOUT = $TIMEOUT" "$file" > "$tmp" && mv "$tmp" "$file"
}

run_py() {
  echo "Running: python3.11 $*"
  python3.11 "$@"
}

update_timeout config_gpmc.json
update_timeout config_ganak.json

echo "Updated TIMEOUT to $TIMEOUT"

echo "=== Simulation results comparison ==="
run_py compare_simulation.py -a origin -b benchlist-sim.txt -t quasimodo
run_py compare_simulation.py -a origin -b benchlist-sim-add.txt -t quasimodo
run_py compare_simulation.py -a Feynman -b benchlist-feymann.txt -t quasimodo
run_py compare_simulation.py -a ModifiedRevLib -b benchlist-mrevlib.txt -t quasimodo
run_py compare_simulation.py -a revlib -b benchlist-revlib.txt -t quasimodo
