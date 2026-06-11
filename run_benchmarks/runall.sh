#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

export LD_LIBRARY_PATH="/Quokka/Quasimodo/python_pkg:${LD_LIBRARY_PATH:-}"

GPMC_CONFIG="${SCRIPT_DIR}/config_gpmc.json"
GANAK_CONFIG="${SCRIPT_DIR}/config_ganak.json"
export QUOKKA_CONFIG="$GPMC_CONFIG"

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

for f in "$GPMC_CONFIG" "$GANAK_CONFIG"; do
  if [ ! -f "$f" ]; then
    echo "Error: config file not found: $f"
    exit 1
  fi
done

update_timeout() {
  local file="$1"
  local tmp="${file}.tmp"
  jq ".TIMEOUT = $TIMEOUT" "$file" > "$tmp" && mv "$tmp" "$file"
}

run_py() {
  echo "Running: python3.11 $*"
  python3.11 "$@"
}

update_timeout "$GPMC_CONFIG"
update_timeout "$GANAK_CONFIG"

echo "Updated TIMEOUT to $TIMEOUT"
echo "Using QUOKKA_CONFIG=$QUOKKA_CONFIG"

cd "$SCRIPT_DIR"

echo "=== Simulation results comparison ==="
# run_py compare_simulation.py -a Feynman -b benchlist-feymann.txt
run_py compare_simulation.py -a origin -b benchlist-sim.txt -t quokka-gpmc quokka-ganak quasimodo ddsim
run_py compare_simulation.py -a origin -b benchlist-sim-add.txt
run_py compare_simulation.py -a Feynman -b benchlist-feynman.txt
run_py compare_simulation.py -a ModifiedRevLib -b benchlist-mrevlib.txt
run_py compare_simulation.py -a revlib -b benchlist-revlib.txt

echo "=== Equivalence checking ==="
run_py compare_eqcheck.py -b benchlist-eq-phaseshift.txt -m shift4 -t quokka-gpmc quokka-ganak qcec
run_py compare_eqcheck.py -b benchlist-eq-gatemissing.txt -m gm

echo "=== Verification ==="
run_py eval_verification.py

echo "=== Synthesis ==="
echo "Running: ./synthesis/run_synthesis.sh"
./synthesis/run_synthesis.sh
