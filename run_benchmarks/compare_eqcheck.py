import shutil
import os, time
import re
import utils
from tqdm import tqdm
import subprocess
from mqt import qcec
from OtherToolPath import SliQECPath, ConfigGPMC, ConfigGanak
import quokka_sharp as qk
import quokka_sharp.config as qc

import os
import argparse
import utils

parser = argparse.ArgumentParser()
parser.add_argument(
    "-b", "--benchlist",
    default="benchlist-eq-phaseshift.txt",
    help="Benchmark list file, e.g. benchlist-eq-phaseshift.txt",
)
parser.add_argument(
    "-m", "--modifications",
    nargs="+",
    default=["shift4"],
    help="Modification folders to run, e.g. shift4 or opt gm",
)
args = parser.parse_args()

benchmark_folder = os.path.join("algorithm")

benchmarks_list = utils.get_benchmark_list_from_file(args.benchlist)
benchmarks_list.sort()

df_columns = ["modification", "qubits", "algo", "tool", "result", "time"]

modifications = args.modifications

benchlist_base = os.path.splitext(os.path.basename(args.benchlist))[0]
mods_base = "_".join(modifications)
results_file_name = f"compare_eqcheck_{benchlist_base}_{mods_base}.csv"

print("Benchlist:", args.benchlist)
print("Benchmarks:", benchmarks_list)
print("Modifications:", modifications)
print("Results file:", results_file_name)


quokka_bases = [ "comp"]
quokka_checks = {
	"comp": "cyclic",
	"pauli": "linear"
}
quokka_threads = {
	"comp": 1,
	"pauli": 16
}

def get_results():
	return utils.get_results_from_file(results_file_name, df_columns)

def update_results(results_df):
	utils.save_results_to_file(results_file_name, results_df)

def sort_results():
	results_df = get_results()
	results_df.sort_values(by=["modification", "algo", "qubits", "tool"], inplace=True)
	update_results(results_df)

def check_results():
	results_df = get_results()
	print(results_df)
	assert all(results_df[results_df["modification"] == "opt"]["result"].isin(["TIMEOUT", "True", True])), "Opt results are not valid\n{}".format(results_df[results_df["modification"] == "opt"])
	assert all(results_df[results_df["modification"] != "opt"]["result"].isin(["TIMEOUT", "False", False])), "GM results are not valid\n{}".format(results_df[results_df["modification"] != "opt"])

def draw_figures():
	results_df = get_results()

	def compute_to_print(row):
		if row["result"] == "TIMEOUT":
			return "TIMEOUT"
		if (row["modification"] == "opt") and (row["result"] == "False"):
			return "wrong"
		if (row["modification"] == "gm") and (row["result"] == "True"):
			return "wrong"
		return f"{row['time']:.3f}"

	results_df["Run Time (sec)"] = results_df.apply(compute_to_print, axis=1)
	print(results_df)

	for mod in modifications:
		results_df[results_df["modification"] == mod].pivot_table(
			values=["Run Time (sec)"],
			index=["algo", "qubits"],
			columns=["tool"],
			aggfunc="sum"
			).to_latex(
			utils.get_results_file_path(results_file_name).replace(".csv", f"_{mod}.tex"),
			# column_format="lccc",
			multirow=True, multicolumn=True, na_rep=""
			)
	
def get_run_data(mod, algo, qubits, tool):
	return {
		"modification": mod,
		"algo": algo,
		"qubits": qubits,
		"tool": tool
	}

def run_QuokkaSharp(file_name, mod, tool):
    if tool == "gpmc":
        os.environ["QUOKKA_CONFIG"] = ConfigGPMC
    elif tool == "ganak":
        os.environ["QUOKKA_CONFIG"] = ConfigGanak
    else:
        raise Exception("Tool does not support")
    qc.reload_config()
    print("tool =", tool, "| ToolInvocation =", qc.CONFIG["ToolInvocation"])    
    results_df = get_results()
    origin_file = utils.get_file_path(file_name, "origin", benchmark_folder)
    mod_file = utils.get_file_path(file_name, mod, benchmark_folder)
    algo_name, qubits = utils.get_data_from_algo_file_name(file_name)
    
    if not qubits:
        qubits = get_qubits_from_file(origin_file)
    new = False
    for basis in quokka_bases:
        run_data = get_run_data(mod, algo_name, qubits, f"quokka-sharp-{basis}-{tool}")
        if utils.data_exists(run_data, results_df):
            continue
		
        start_time = time.time()
        result = qk.functionalities.eq(origin_file, mod_file, basis, quokka_checks[basis], N=quokka_threads[basis])
        
        end_time = time.time()
        print("")
        results_df = utils.add_result_to_df(run_data, result, end_time-start_time, results_df)
        utils.save_results_to_file(results_file_name, results_df)
        new = True
    return new

import time
import multiprocessing as mp


def _qcec_verify_worker(origin_file, mod_file, queue):
    try:
        v = qcec.verify(origin_file, mod_file, run_zx_checker=False)
        queue.put(v.equivalence)
    except Exception as e:
        queue.put(e)

def run_QCEC(file_name, mod):
    results_df = get_results()

    origin_file = utils.get_file_path(file_name, "origin", benchmark_folder)
    mod_file = utils.get_file_path(file_name, mod, benchmark_folder)

    algo_name, qubits = utils.get_data_from_algo_file_name(file_name)
    if not qubits:
        qubits = get_qubits_from_file(origin_file)

    run_data = get_run_data(mod, algo_name, qubits, "QCEC")
    if utils.data_exists(run_data, results_df):
        return False

    start_time = time.time()

    q = mp.Queue()
    p = mp.Process(
        target=_qcec_verify_worker,
        args=(origin_file, mod_file, q)
    )

    p.start()
    p.join(utils.timeout)

    if p.is_alive():
        p.terminate()
        p.join()
        result = "TIMEOUT"
    else:
        out = q.get()
        if isinstance(out, Exception):
            result = "ERROR"
        else:
            result = (str(out) == "EquivalenceCriterion.equivalent_up_to_global_phase")

    end_time = time.time()

    results_df = utils.add_result_to_df(
        run_data,
        result,
        end_time - start_time,
        results_df
    )
    utils.save_results_to_file(results_file_name, results_df)

    return True


def get_qubits_from_file(file_path):
	with open(file_path, "r") as f:
		for line in f:
			match = re.search(r"qreg q\[(\d+)\];", line)
			if match:
				return int(match.group(1))
	return None
def run_SliQEC(file_name, mod):
    results_df = get_results()
    origin_file = utils.get_file_path(file_name, "origin", benchmark_folder)
    mod_file = utils.get_file_path(file_name, mod, benchmark_folder)
    algo_name, qubits = utils.get_data_from_algo_file_name(file_name)
    if not qubits:
        qubits = get_qubits_from_file(origin_file)

    run_data = get_run_data(mod, algo_name, qubits, "SliQEC")
    if utils.data_exists(run_data, results_df):
        return False

    cmd = [
        SliQECPath,
        "--circuit1", origin_file,
        "--circuit2", mod_file,
    ]

    start_time = time.time()
    output = None

    try:
        output = subprocess.check_output(
            cmd,
            universal_newlines=True,
            timeout=utils.timeout,
            stderr=subprocess.STDOUT,
        )
        end_time = time.time()
        runtime = end_time - start_time

        result_matches = re.search(r"Is equivalent\? (Yes|No)", output)
        if result_matches is None or len(result_matches.groups()) != 1:
            result = "ERROR"
        else:
            result = (result_matches.group(1) == "Yes")

    except subprocess.TimeoutExpired as e:
        end_time = time.time()
        runtime = end_time - start_time
        result = "TIMEOUT"
        output = getattr(e, "output", None)

    except subprocess.CalledProcessError as e:
        end_time = time.time()
        runtime = end_time - start_time
        result = "ERROR"
        output = e.output

    except Exception as e:
        end_time = time.time()
        runtime = end_time - start_time
        result = "ERROR"
        output = str(e)

    results_df = utils.add_result_to_df(run_data, result, runtime, results_df)
    utils.save_results_to_file(results_file_name, results_df)

    if result == "ERROR":
        print(f"[SliQEC ERROR] {file_name} ({mod})")
        if output:
            print(output)

    return True
total = len(benchmarks_list) * len(modifications) * 3
pbar = tqdm(total=total, desc="All runs", unit="run")


def main():
	for file in benchmarks_list:
		new = False
		for mod in modifications:
			print(file)
			# # QuokkaSharp gpmc
			t0 = time.perf_counter()
			new |= run_QuokkaSharp(file, mod, "gpmc")
			dt = time.perf_counter() - t0
			print(f"[DONE] file={file}, mod={mod}, tool=gpmc, time={dt:.2f}s")

			# QuokkaSharp ganak
			t0 = time.perf_counter()
			new |= run_QuokkaSharp(file, mod, "ganak")
			dt = time.perf_counter() - t0
			print(f"[DONE] file={file}, mod={mod}, tool=ganak, time={dt:.2f}s")

			# SliQEC
			t0 = time.perf_counter()
			new |= run_SliQEC(file, mod)
			dt = time.perf_counter() - t0
			print(f"[DONE] file={file}, mod={mod}, tool=SliQEC, time={dt:.2f}s")

			# qcec
			t0 = time.perf_counter()
			new |= run_QCEC(file, mod)
			dt = time.perf_counter() - t0
			print(f"[DONE] file={file}, mod={mod}, tool=qcec, time={dt:.2f}s")
		

if __name__ == "__main__":
    mp.freeze_support()  
    main()
    sort_results()
    # check_results()
    draw_figures()

