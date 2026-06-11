#!/usr/bin/env python3
import argparse
import csv
import math
from collections import defaultdict


NON_NUMERIC = {"TIMEOUT", "ERROR", "N/S", "--", ""}


def normalize_qubits(q: str) -> str:
    q = q.strip()
    try:
        return str(int(float(q)))
    except ValueError:
        return q


def parse_result(x: str):
    x = x.strip()
    if x in NON_NUMERIC:
        return x
    try:
        return float(x)
    except ValueError:
        # Handles values like 0E-14
        try:
            return float(x.replace("E", "e"))
        except ValueError:
            return "PARSE_ERROR"


def same_result(a, b, abs_tol=1e-6):
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, abs_tol=abs_tol, rel_tol=0.0)
    return a == b


def fmt(x):
    if isinstance(x, float):
        return f"{x:.17g}"
    return str(x)


def main():
    parser = argparse.ArgumentParser(
        description="Check whether simulation results from different tools agree."
    )
    parser.add_argument("csv_file", help="CSV file with columns: algo,qubits,tool,result,time")
    parser.add_argument(
        "--ref",
        default="DDSim",
        help="Reference tool name. Default: DDSim",
    )
    parser.add_argument(
        "--tol",
        type=float,
        default=1e-6,
        help="Absolute tolerance. Default: 1e-6",
    )
    parser.add_argument(
        "--show-ok",
        action="store_true",
        help="Also print matching results.",
    )
    args = parser.parse_args()

    groups = defaultdict(dict)

    with open(args.csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"algo", "qubits", "tool", "result", "time"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain columns: {required}")

        for row in reader:
            algo = row["algo"].strip()
            qubits = normalize_qubits(row["qubits"])
            tool = row["tool"].strip()
            result = parse_result(row["result"])
            time = row["time"].strip()

            key = (algo, qubits)
            groups[key][tool] = {
                "result": result,
                "time": time,
            }

    total_checked = 0
    total_ok = 0
    total_bad = 0
    total_skipped = 0

    print(f"Reference tool: {args.ref}")
    print(f"Absolute tolerance: {args.tol:g}")
    print()

    for key in sorted(groups.keys()):
        algo, qubits = key
        tools = groups[key]

        if args.ref not in tools:
            print(f"[SKIP] {algo}, n={qubits}: no reference result from {args.ref}")
            total_skipped += 1
            continue

        ref_result = tools[args.ref]["result"]

        if not isinstance(ref_result, float):
            print(
                f"[SKIP] {algo}, n={qubits}: reference {args.ref} result is {ref_result}"
            )
            total_skipped += 1
            continue

        for tool, data in sorted(tools.items()):
            if tool == args.ref:
                continue

            result = data["result"]
            total_checked += 1

            if not isinstance(result, float):
                print(
                    f"[SKIP] {algo}, n={qubits}, {tool}: result={result}, "
                    f"ref={fmt(ref_result)}"
                )
                total_skipped += 1
                continue

            diff = abs(result - ref_result)
            ok = same_result(result, ref_result, abs_tol=args.tol)

            if ok:
                total_ok += 1
                if args.show_ok:
                    print(
                        f"[OK]   {algo}, n={qubits}, {tool}: "
                        f"{fmt(result)} vs {args.ref} {fmt(ref_result)}, "
                        f"diff={diff:.3g}, time={data['time']}"
                    )
            else:
                total_bad += 1
                print(
                    f"[BAD]  {algo}, n={qubits}, {tool}: "
                    f"{fmt(result)} vs {args.ref} {fmt(ref_result)}, "
                    f"diff={diff:.3g}, time={data['time']}"
                )

    print()
    print("Summary:")
    print(f"  checked numeric comparisons: {total_checked}")
    print(f"  OK:      {total_ok}")
    print(f"  BAD:     {total_bad}")
    print(f"  skipped: {total_skipped}")


if __name__ == "__main__":
    main()
