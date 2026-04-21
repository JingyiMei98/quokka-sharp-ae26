from pathlib import Path


from mqt.core import load

from mqt.ddsim import CircuitSimulator

# create a CircuitSimulator object
qc = load("test.qasm")
sim = CircuitSimulator(qc)

# run the simulation
result = sim.simulate(shots=32)

import numpy as np

# get the final DD
dd = sim.get_constructed_dd()
# transform the DD to a vector
vec = dd.get_amplitude(qc.num_qubits,"0"*qc.num_qubits)
# transform to a numpy array (without copying)
print(vec)