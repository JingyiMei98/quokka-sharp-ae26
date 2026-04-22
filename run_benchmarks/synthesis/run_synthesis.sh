#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export QUOKKA_CONFIG="${SCRIPT_DIR}/config.json"

# Patch D4ToolInvocation in config.json to point to the local maxT_static binary
MAXT_PATH="${SCRIPT_DIR}/maxT_static"
 
if [ ! -f "${MAXT_PATH}" ]; then
    echo "ERROR: maxT_static binary not found at ${MAXT_PATH}"
    exit 1
fi
 
python3 - <<EOF
import json
 
config_path = "${QUOKKA_CONFIG}"
 
with open(config_path, "r") as f:
    config = json.load(f)
 
config["D4ToolInvocation"] = "${MAXT_PATH}"
 
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
 
print("config.json updated: D4ToolInvocation ->", "${MAXT_PATH}")
EOF
 
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to update config.json"
    exit 1
fi

TMP_DIR="${SCRIPT_DIR}/tmp"
mkdir -p "${TMP_DIR}"

python3 "${SCRIPT_DIR}/syn_ccx.py" \
    --qasmfile "${SCRIPT_DIR}/ccx.qasm" \
    --tmp "${TMP_DIR}" \
    > "${SCRIPT_DIR}/ccx_output.log" 2>&1

echo "Python script finished. Parsing log..."

LOG_FILE="${SCRIPT_DIR}/ccx_output.log"

LOG_FILE="${SCRIPT_DIR}/ccx_output.log"
 
# Parse the log file and build CSV table
ITER_HEADER="Iteration"
VARS_ROW="Variables"
CLAUSES_ROW="Clauses"
LITERALS_ROW="Literals"
RUNTIME_ROW="Runtime (sec)"
 
while IFS= read -r line; do
    # Match "Iteration: N"
    if [[ "$line" =~ ^Iteration:[[:space:]]*([0-9]+) ]]; then
        iter_num="${BASH_REMATCH[1]}"
        display_num=$((iter_num + 1))
        ITER_HEADER="${ITER_HEADER}, ${display_num}"
    fi
 
    # Match "Run Time: N"
    if [[ "$line" =~ ^Run\ Time:[[:space:]]*([0-9]+\.[0-9]+) ]]; then
        runtime="${BASH_REMATCH[1]}"
        rounded=$(printf "%.2f" "$runtime")
        RUNTIME_ROW="${RUNTIME_ROW}, ${rounded}"
    fi
done < "$LOG_FILE"
 
for i in 0 1 2 3 4 5; do
    OUT_FILE="${TMP_DIR}/onehotXZ_Reg_${i}_d4.out"
    vars=""
    clauses=""
    literals=""
 
    if [ -f "${OUT_FILE}" ]; then
        while IFS= read -r line; do
            if [[ "$line" =~ \[INITIAL\ INPUT\]\ Number\ of\ variables:[[:space:]]*([0-9]+) ]]; then
                vars="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ \[INITIAL\ INPUT\]\ Number\ of\ clauses:[[:space:]]*([0-9]+) ]]; then
                clauses="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ \[INITIAL\ INPUT\]\ Number\ of\ literals:[[:space:]]*([0-9]+) ]]; then
                literals="${BASH_REMATCH[1]}"
            fi
        done < "${OUT_FILE}"
    else
        echo "WARNING: ${OUT_FILE} not found, using empty values"
    fi
 
    VARS_ROW="${VARS_ROW}, ${vars}"
    CLAUSES_ROW="${CLAUSES_ROW}, ${clauses}"
    LITERALS_ROW="${LITERALS_ROW}, ${literals}"
done
 
# Write CSV output
CSV_FILE="${SCRIPT_DIR}/ccx_results.csv"
{
    echo "${ITER_HEADER}"
    echo "${VARS_ROW}"
    echo "${CLAUSES_ROW}"
    echo "${LITERALS_ROW}"
    echo "${RUNTIME_ROW}"
} > "${CSV_FILE}"
 
echo "CSV table written to: ${CSV_FILE}"
echo ""
cat "${CSV_FILE}"