from concurrent.futures import process
import shutil
import os, time
import quokka_sharp as qk
import re
import utils
from tqdm import tqdm
import subprocess
from OtherToolPath import SliQSimPath, QuaismodoPath, ConfigGanak, ConfigGPMC
import quokka_sharp.config as qc
from mqt.core import load

from mqt.ddsim import CircuitSimulator
# Evaluate per algorithm

import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "-a", "--algorithm",
    default="origin",
    help="Algorithm subfolder name, e.g. origin",
)
parser.add_argument(
    "-b", "--benchlist",
    default="benchlist-sim.txt",
    help="Benchmark list file, e.g. benchlist-sim.txt",
)
parser.add_argument(
    "-t", "--tools",
    nargs="+",
    default=["quokka-gpmc", "quokka-ganak", "sliqsim", "quasimodo", "ddsim"],
    help="Tools to run: quokka-gpmc quokka-ganak sliqsim quasimodo ddsim",
)

args = parser.parse_args()

benchmark_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "benchmark",
)

algorithm = args.algorithm
benchmark_folder = os.path.join("algorithm", algorithm)

benchmarks_list = utils.get_benchmark_list_from_file(args.benchlist)
benchmarks_list.sort()
print("Benchmarks:", benchmarks_list)
print("Tools:", args.tools)

benchlist_base = os.path.splitext(os.path.basename(args.benchlist))[0]
results_file_name = f"compare_simulations_{algorithm}_{benchlist_base}.csv"

folder = "/"

df_columns = ["qubits", "algo", "tool", "result", "time"]

quokka_bases = ["comp", "pauli"]
# quokka_bases = ["comp"]

quokka_measurement = "allzero"

sliqsim_measurement = lambda qubits: f"amp {'0'*qubits};"

def get_results():
	return utils.get_results_from_file(results_file_name, df_columns)

def update_results(results_df):
	utils.save_results_to_file(results_file_name, results_df)

def sort_results():
	results_df = get_results()
	results_df.sort_values(by=["algo", "qubits", "tool"], inplace=True)
	update_results(results_df)

def check_results():
	results_df = get_results()
	time_over_timeout_allowed = 0 #seconds
	result_accuracy = 1e-6
	for exp, results in results_df.groupby(["qubits", "algo"]):
		# assert len(results) == 3, f"Expected 3 results for {exp}, but found {len(results)}\n{results}"

		for timeout_result in results[results["result"] == "TIMEOUT"].itertuples():
			assert abs(timeout_result.time - utils.timeout) <= time_over_timeout_allowed, f"Timeout result for {exp} is not close to timeout: {timeout_result.time}"

		non_timeout_results = results[results["result"] != "TIMEOUT"]
		min_result = non_timeout_results["result"].min()
		max_result = non_timeout_results["result"].max()
		assert max_result - min_result <= result_accuracy, f"Non-timeout results for {exp} are not similar: {min_result} vs {max_result}\n{non_timeout_results}"

def draw_figures():
	results_df = get_results()

	def compute_to_print(row):
		if row["result"] == "TIMEOUT":
			return "TIMEOUT"
		return f"{row['time']:.3f}"

	results_df["Run Time (sec)"] = results_df.apply(compute_to_print, axis=1)

	results_df.pivot_table(
		values=["Run Time (sec)"], 
		index=["algo", "qubits"],
		columns=["tool"],
		aggfunc="sum"
		).to_latex(
		utils.get_results_file_path(results_file_name).replace(".csv", f".tex"),
		# column_format="lccc",
		multirow=True, multicolumn=True, na_rep=""
		)
	
def get_run_data(algo, qubits, tool):
	return {
		"algo": algo,
		"qubits": qubits,
		"tool": tool
	}

def run_QuokkaSharp(file_name, tool):

    if tool == "gpmc":
        os.environ["QUOKKA_CONFIG"] = ConfigGPMC
    elif tool == "ganak":
        os.environ["QUOKKA_CONFIG"] = ConfigGanak
    else:
        raise Exception("Tool does not support")
    qc.reload_config()
    results_df = get_results()
    file_path = utils.get_file_path(file, folder, benchmark_folder)
    print(f"Running QuokkaSharp with {tool} on {file_path}...")
    algo_name, qubits = utils.get_data_from_algo_file_name(file_name)
    if not qubits:
        qubits = get_qubits_from_file(file_path)
    new = False
    for basis in quokka_bases:
        run_data = get_run_data(algo_name, qubits, f"quokka-sharp-{basis}-{tool}")
        if utils.data_exists(run_data, results_df):
            continue
        start_time = time.time()
        print(f"Running QuokkaSharp with {tool} on {file_path} with basis {basis}...")
        result = qk.functionalities.sim(file_path, basis, quokka_measurement)
        end_time = time.time()
        
        results_df = utils.add_result_to_df(run_data, result, end_time-start_time, results_df)
        utils.save_results_to_file(results_file_name, results_df)
        new = True
        print("Quokka_sharp", tool, "runtime:", end_time-start_time, "result:", result)

    return new

def get_SliQSim_obs_file_path(qubits):
	obs_file_path = os.path.join(".", "temp", f"SliQSim_{qubits}_obs.obs")
	if not os.path.exists(obs_file_path):
		os.makedirs("temp", exist_ok=True)
		with open(obs_file_path, "w") as f:
			f.write(f"{sliqsim_measurement(qubits)};\n")
	return obs_file_path

def run_SliQSim(file_name):
    results_df = get_results()
    file_path = utils.get_file_path(file_name, folder, benchmark_folder)

    algo_name, qubits = utils.get_data_from_algo_file_name(file_name)
    if not qubits:
        qubits = get_qubits_from_file(file_path)

    run_data = get_run_data(algo_name, qubits, "SliQSim")
    if utils.data_exists(run_data, results_df):
        return False

    obs_file_path = get_SliQSim_obs_file_path(qubits)
    cmd = [
        SliQSimPath,
        "--sim_qasm", file_path,
        "--obs_file", obs_file_path,
        "--type", "2"
    ]

    start_time = time.time()
    try:
        output = subprocess.check_output(
            cmd,
            universal_newlines=True,
            timeout=utils.timeout,
            stderr=subprocess.DEVNULL
        )
        end_time = time.time()

        result_matches = re.search(r"\s*([-\d.e]+)\s", output)
        if result_matches is None:
            raise ValueError(f"Could not find result in SliQSim output:\n{output}")
        if len(result_matches.groups()) != 1:
            raise ValueError(
                f"Expected one result match, got {len(result_matches.groups())} in output:\n{output}"
            )

        result = float(result_matches.group(1)) ** 2

    except subprocess.TimeoutExpired:
        end_time = time.time()
        result = "TIMEOUT"

    except Exception as e:
        end_time = time.time()
        result = "error"
        print(f"SliQSim failed on {file_name}: {e}")

    runtime = end_time - start_time
    results_df = utils.add_result_to_df(run_data, result, runtime, results_df)
    utils.save_results_to_file(results_file_name, results_df)
    return True



def remove_temp_folder():
	temp_folder = os.path.join(".", "temp")
	if os.path.exists(temp_folder):
		shutil.rmtree(temp_folder)

def get_qubits_from_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = re.search(r"qreg q\[(\d+)\];", line)
            if match:
                return int(match.group(1))
    return None

def run_Quasimodo(file_name):
	results_df = get_results()
	file_path = utils.get_file_path(file, folder, benchmark_folder)
	algo_name, qubits = utils.get_data_from_algo_file_name(file_name)
	if not qubits:
		qubits = get_qubits_from_file(file_path)
	run_data = get_run_data(algo_name, qubits, "Quasimodo")
	if utils.data_exists(run_data, results_df):
		return False

	cmd = [
		"python3.10",
		QuaismodoPath,
		"-f", file_path
  	]
	try:
		start_time = time.time()
		output = subprocess.check_output(cmd, universal_newlines=True, timeout=utils.timeout)
		end_time = time.time()
	except subprocess.TimeoutExpired:
		end_time = time.time()
		result = "TIMEOUT"
		runtime = end_time - start_time
	else:
		result_matches = re.search(r"\s*([-\d.e]+)\s", output)
		assert result_matches is not None, f"Could not find result in Quasimodo output:\n{output}"
		assert len(result_matches.groups()) == 1, f"Expected one result match, got {len(result_matches.groups())} in output:\n{output}"
		runtime = end_time - start_time
		print("Quasimodo", "runtime:", runtime, "result:", result_matches.group(1))
		result = float(result_matches.group(1))**2

	results_df = utils.add_result_to_df(run_data, result, runtime, results_df)
	utils.save_results_to_file(results_file_name, results_df)
	return True	

import subprocess
import time
import os
import signal

import subprocess
import time
import sys

import subprocess
import time
import sys
import signal
import os

def run_DDSim(file_name):
    results_df = get_results()
    file_path = utils.get_file_path(file_name, folder, benchmark_folder)

    algo_name, qubits = utils.get_data_from_algo_file_name(file_name)
    if not qubits:
        qubits = get_qubits_from_file(file_path)

    run_data = get_run_data(algo_name, qubits, "DDSim")

    if utils.data_exists(run_data, results_df):
        return False

    cmd = [
        "bash",
        "-c",
        f"exec timeout {utils.timeout}s {sys.executable} run_ddsim_single.py '{file_path}'"
    ]

    start_time = time.time()

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid  
    )

    try:
        output, stderr = process.communicate(timeout=utils.timeout)  

        end_time = time.time()

        if process.returncode == 124:
            result = "TIMEOUT"
        elif process.returncode != 0:
            result = "ERROR"
            print("stderr:", stderr)
        else:
            result = float(output.strip())

    except KeyboardInterrupt:
        print("\n[Ctrl+C detected] Killing DDSim...")

        os.killpg(os.getpgid(process.pid), signal.SIGKILL)

        end_time = time.time()
        result = "INTERRUPTED"
    except subprocess.TimeoutExpired:
        print("\n[Timeout] Killing DDSim...")
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        end_time = time.time()
        result = "TIMEOUT"

    runtime = end_time - start_time

    results_df = utils.add_result_to_df(run_data, result, runtime, results_df)
    utils.save_results_to_file(results_file_name, results_df)

    print("DDSim", "runtime:", runtime, "result:", result)

    return True


for file in benchmarks_list:
    print(f"Processing {file}...")

    if "quokka-gpmc" in args.tools:
        run_QuokkaSharp(file, "gpmc")

    if "quokka-ganak" in args.tools:
        run_QuokkaSharp(file, "ganak")

    if "sliqsim" in args.tools:
        run_SliQSim(file)

    if "quasimodo" in args.tools:
        run_Quasimodo(file)

    if "ddsim" in args.tools:
        run_DDSim(file)


remove_temp_folder()
sort_results()
# check_results()
draw_figures()

