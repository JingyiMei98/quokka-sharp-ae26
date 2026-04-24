import quokka_sharp as qk
from time import time
import os
import csv

def main():
    qasmfile = "../benchmark/algorithm/origin/qwalk-v-chain_nativegates_ibm_qiskit_opt0_5.qasm"
    basis = "comp"
    pre = {4: 0}
    post = {4: 0}

    output_csv = "results/verification_results.csv"

    start_time = time()
    res = qk.functionalities.verify(
        qasmfile,
        basis=basis,
        precons=pre,
        postcons=post
    )
    end_time = time()

    filename = os.path.basename(qasmfile)
    runtime = end_time - start_time

    print("basis,file,time,res")
    print(f"{basis},{filename},{runtime:.6f},{res}")

    file_exists = os.path.isfile(output_csv)

    with open(output_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["basis", "file", "time", "res"])
        writer.writerow([basis, filename, f"{runtime:.6f}", res])


if __name__ == "__main__":
    main()