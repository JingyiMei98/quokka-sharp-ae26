import contextlib
import quokka_sharp as qk
import utils, os


name = "syn_CCX"
folder = utils.get_results_file_path(name)
if not os.path.exists(folder):
	os.makedirs(folder)

with open(os.path.join(folder, f'{name}_out.txt'),'w') as f:
	with contextlib.redirect_stdout(f):
		qk.functionalities.syn(os.path.join(utils.benchmark_path, "basic_tests", "ccx_gate_0.qasm"), "pauli", cyc_lin_encoding=True, fid=1, files_root=folder)



