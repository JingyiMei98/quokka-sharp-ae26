from utils import get_qubits_and_gate_count_from_file
import utils
import argparse
import os

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

folder = "/"
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
for file in benchmarks_list:
    file_path = utils.get_file_path(file, folder, benchmark_folder)
    print(file, get_qubits_and_gate_count_from_file(file_path))