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
run_py compare_simulation.py -a origin -b temp-origin.txt -c 2 -t quokka-gpmc quokka-ganak quasimodo ddsim
run_py compare_simulation.py -a ModifiedRevLib -b temp-mrevlib-quokka.txt -t quokka-gpmc quokka-ganak
run_py compare_simulation.py -a ModifiedRevlib -b temp-mrevLib-other.txt -t quasimodo ddsim sliqsim
run_py compare_simulation.py -a origin -b temp-grover-pauli.txt -c 1 -t quokka-gpmc quokka-ganak
run_py compare_simulation.py -a Feynman -b temp-feynman-pauli.txt -c 1 -t quokka-gpmc quokka-ganak
run_py compare_simulation.py -a Feynman -b temp-feynman-comp.txt -c 0 -t quokka-gpmc quokka-ganak
run_py compare_simulation.py -a Feynman -b temp-feynman-all.txt -c 0 -t quokka-gpmc quokka-ganak quasimodo ddsim sliqsim

