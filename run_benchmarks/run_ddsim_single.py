# run_ddsim_single.py

import sys
from mqt.ddsim import CircuitSimulator
from mqt.core import load


def main(file_path):
    qc = load(file_path)
    sim = CircuitSimulator(qc)
    result = sim.simulate(shots=1024)
    dd = sim.get_constructed_dd()

    amp = dd.get_amplitude(qc.num_qubits, "0" * qc.num_qubits)
    prob = abs(amp) ** 2

    print(prob)


if __name__ == "__main__":
    file_path = sys.argv[1]
    main(file_path)