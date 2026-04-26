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
# run_py compare_simulation.py -a Feynman -b benchlist-feymann.txt
run_py compare_simulation.py -a origin -b temp-sim-quokka-pauli.txt -c 1 -t quokka-gpmc quokka-ganak 
run_py compare_simulation.py -a origin -b temp-sim-quokka-comp.txt -c 0 -t quokka-gpmc quokka-ganak
run_py compare_simulation.py -a origin -b temp-sim-ddsim.txt -t ddsim
run_py compare_simulation.py -a origin -b temp-sim-quasimodo.txt -t quasimodo
run_py compare_simulation.py -a origin -b temp-sim-sliqsim.txt -t sliqsim

