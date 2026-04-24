#!/usr/bin/env bash
set -euo pipefail

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
run_py compare_simulation.py -a origin -b benchlist-sim.txt -t quokka-gpmc quokka-ganak quasimodo ddsim
run_py compare_simulation.py -a origin -b benchlist-sim-add.txt
run_py compare_simulation.py -a ModifiedRevlib -b benchlist-mrevlib.txt
run_py compare_simulation.py -a revlib -b benchlist-revlib.txt

echo "=== Equivalence checking ==="
run_py compare_eqcheck.py -b benchlist-eq-phaseshift.txt -m shift4
run_py compare_eqcheck.py -b benchlist-eq-gatemissing.txt -m gm

echo "=== Verification ==="
run_py eval_verification.py

echo "=== Synthesis ==="
echo "Running: ./synthesis/run_synthesis.sh"
./synthesis/run_synthesis.sh