import os
import subprocess
import re
import time
from collections import defaultdict
from typing import List

# -----------------------------------------------------------------------------
# Parsing Functions
# -----------------------------------------------------------------------------

def parse_gprof_output(gprof_output: str):
    """
    Parses gprof output to extract flat profile and call graph information.

    Returns a dictionary:
    {
        "flat_profile": [...],
        "call_graph": { index: { ... }, ... }
    }
    """
    parsed_data = {
        "flat_profile": [],
        "call_graph": defaultdict(lambda: {"parents": [], "children": []})
    }

    sections = gprof_output.split("\n\n")

    # Extract Flat Profile
    flat_profile_section = None
    for section in sections:
        if "Flat profile:" in section:
            flat_profile_section = section
            break

    if flat_profile_section:
        for line in flat_profile_section.splitlines():
            match = re.match(
                r"\s*(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)?\s+(\d+\.\d+)?\s+(\d+\.\d+)?\s+(.+)",
                line
            )
            if match:
                parsed_data["flat_profile"].append({
                    "percentage_time": float(match.group(1)),
                    "cumulative_seconds": float(match.group(2)),
                    "self_seconds": float(match.group(3)),
                    "calls": int(match.group(4)) if match.group(4) else None,
                    "self_ms_per_call": float(match.group(5)) if match.group(5) else None,
                    "total_ms_per_call": float(match.group(6)) if match.group(6) else None,
                    "function_name": match.group(7).strip()
                })

    # Extract Call Graph
    call_graph_section = None
    for section in sections:
        if "Call graph" in section:
            call_graph_section = section
            break

    if call_graph_section:
        lines = call_graph_section.splitlines()
        current_function = None

        for line in lines:
            # Match a function entry
            match_func = re.match(
                r"^\[(\d+)\]\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)(\+(\d+))?\s+(.+)",
                line
            )
            if match_func:
                index = int(match_func.group(1))
                parsed_data["call_graph"][index].update({
                    "index": index,
                    "percentage_time": float(match_func.group(2)),
                    "self_time": float(match_func.group(3)),
                    "children_time": float(match_func.group(4)),
                    "called": int(match_func.group(5)),
                    "recursive_calls": int(match_func.group(7)) if match_func.group(7) else 0,
                    "function_name": match_func.group(8).strip(),
                })
                current_function = index
                continue

            # Match parents or children lines
            if current_function:
                parent_child_match = re.match(
                    r"^\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)/(\d+)\s+(.+)", line
                )
                if parent_child_match:
                    parsed_data["call_graph"][current_function]["children"].append({
                        "self_time": float(parent_child_match.group(1)),
                        "children_time": float(parent_child_match.group(2)),
                        "called_times": int(parent_child_match.group(3)),
                        "total_called_times": int(parent_child_match.group(4)),
                        "function_name": parent_child_match.group(5).strip()
                    })
                elif "spontaneous" in line.lower():
                    parsed_data["call_graph"][current_function]["parents"].append({
                        "function_name": "<spontaneous>"
                    })

    return parsed_data


def parse_valgrind_output(valgrind_output: str):
    """
    Parses Valgrind Memcheck output (heap usage, errors, leaks).
    """
    result = {}

    heap_in_use = re.search(
        r"in use at exit:\s+(\d+)\s+bytes in\s+(\d+)\s+blocks", 
        valgrind_output
    )
    if heap_in_use:
        result["in_use_at_exit_bytes"] = int(heap_in_use.group(1))
        result["in_use_at_exit_blocks"] = int(heap_in_use.group(2))
    else:
        result["in_use_at_exit_bytes"] = 0
        result["in_use_at_exit_blocks"] = 0

    heap_usage = re.search(
        r"total heap usage:\s+(\d+)\s+allocs,\s+(\d+)\s+frees,\s+([\d,]+)\s+bytes allocated", 
        valgrind_output
    )
    if heap_usage:
        result["total_allocs"] = int(heap_usage.group(1))
        result["total_frees"] = int(heap_usage.group(2))
        result["total_bytes_allocated"] = int(heap_usage.group(3).replace(",", ""))
    else:
        result["total_allocs"] = 0
        result["total_frees"] = 0
        result["total_bytes_allocated"] = 0

    if "All heap blocks were freed -- no leaks are possible" in valgrind_output:
        result["memory_leaks"] = "No leaks"
    else:
        result["memory_leaks"] = "Potential leaks detected"

    error_summary = re.search(
        r"ERROR SUMMARY:\s+(\d+)\s+errors from\s+(\d+)\s+contexts", 
        valgrind_output
    )
    if error_summary:
        result["error_count"] = int(error_summary.group(1))
        result["context_count"] = int(error_summary.group(2))
    else:
        result["error_count"] = 0
        result["context_count"] = 0

    # Identify error types
    error_types = []
    error_patterns = [
        r"Invalid write of size",
        r"Invalid read of size",
        r"Use after free",
        r"Uninitialised value was created",
        r"Conditional jump or move depends on uninitialised value",
    ]
    for pattern in error_patterns:
        matches = re.findall(pattern, valgrind_output)
        for match in matches:
            error_types.append(match)
    result["error_types"] = error_types

    return result


def parse_perf_output(report_text: str):
    """
    Parses the output of 'perf report --stdio' and returns a list of dicts:
    [
       {
         "overhead_percent": float,
         "binary": str,
         "symbol_info": str
       },
       ...
    ]
    """
    perf_results = []
    for line in report_text.splitlines():
        match = re.match(r"^\s*([\d\.]+)%\s+(\S+)\s+(.*)$", line)
        if match:
            overhead_str = match.group(1)
            overhead = float(overhead_str)
            binary_str = match.group(2)
            symbol_info = match.group(3).strip()
            perf_results.append({
                "overhead_percent": overhead,
                "binary": binary_str,
                "symbol_info": symbol_info
            })
    return perf_results


def parse_perf_stat_output(perf_stat_output: str) -> dict:
    """
    Parses the output of `perf stat` to extract task-clock, cycles, and instructions.
    """
    metrics = {}
    # Match task-clock
    task_clock_match = re.search(r"([\d\.]+)\s+task-clock.*", perf_stat_output)
    if task_clock_match:
        metrics["task_clock_ms"] = float(task_clock_match.group(1))

    # Match cycles
    cycles_match = re.search(r"([\d,]+)\s+cycles.*", perf_stat_output)
    if cycles_match:
        metrics["cycles"] = int(cycles_match.group(1).replace(",", ""))

    # Match instructions
    instructions_match = re.search(r"([\d,]+)\s+instructions.*", perf_stat_output)
    if instructions_match:
        metrics["instructions"] = int(instructions_match.group(1).replace(",", ""))

    return metrics


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def compile_code(source_file: str, executable: str, compiler: str = "g++", flags: List[str] = None):
    commands = [compiler] + (flags or []) + ["-o", executable, source_file]
    subprocess.run(commands, check=True)
    print(f"[INFO] Compiled {source_file} -> {executable} (flags: {flags})")


def run_program(executable: str) -> str:
    if not os.access(executable, os.X_OK):
        raise PermissionError(f"[ERROR] The file {executable} is not executable.")
    result = subprocess.run([executable], check=True, text=True, capture_output=True)
    return result.stdout


def run_gprof(executable: str) -> str:
    gprof_command = ["gprof", executable, "gmon.out"]
    result = subprocess.run(gprof_command, check=True, text=True, capture_output=True)
    return result.stdout


def run_valgrind(executable: str) -> str:
    valgrind_command = ["valgrind", "--leak-check=full", executable]
    result = subprocess.run(valgrind_command, check=True, text=True, capture_output=True)
    # Valgrind’s analysis is in stderr
    return result.stderr


def run_perf_with_timing(executable: str, frequency: int = 1000) -> dict:
    """
    Returns:
    {
      'execution_time': float,
      'perf_output': str
    }
    """
    perf_data_file = "perf.data"
    if not os.access(executable, os.X_OK):
        raise PermissionError(f"[ERROR] The file {executable} is not executable.")

    print(f"[PERF] Recording data (freq={frequency})...")
    start_time = time.perf_counter()

    record_cmd = [
        "perf", "record",
        f"-F{frequency}",
        "-g",
        "-o", perf_data_file,
        executable
    ]
    subprocess.run(record_cmd, check=True)

    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"[PERF] Program execution completed in {execution_time:.4f} seconds.")

    print("[PERF] Generating report from perf.data...")
    report_cmd = [
        "perf", "report",
        "--stdio",
        "-i", perf_data_file
    ]
    report_proc = subprocess.run(report_cmd, check=True, text=True, capture_output=True)

    return {
        "execution_time": execution_time,
        "perf_output": report_proc.stdout
    }


def run_perf_stat(executable: str) -> str:
    """
    Runs `perf stat -e task-clock,cycles,instructions` on the given executable.
    Returns the raw stderr output from perf.
    """
    if not os.access(executable, os.X_OK):
        raise PermissionError(f"[ERROR] The file {executable} is not executable.")

    print("[PERF STAT] Collecting performance statistics...")
    perf_command = [
        "perf", "stat",
        "-e", "task-clock,cycles,instructions",
        executable
    ]
    result = subprocess.run(perf_command, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"[ERROR] perf stat failed:\n{result.stderr}")
    # perf stat writes results to stderr
    return result.stderr


def process_perf_stat(executable: str):
    """
    Runs `perf stat`, parses the output, and prints the metrics.
    """
    try:
        perf_stat_output = run_perf_stat(executable)
        parsed_metrics = parse_perf_stat_output(perf_stat_output)
        print("\n[PERF STAT ANALYSIS]")
        if parsed_metrics:
            for k, v in parsed_metrics.items():
                print(f"{k}: {v}")
            return parsed_metrics
        else:
            return "(No metrics found in perf stat output.)"
            
    except Exception as e:
        print(f"[ERROR - PERF STAT STEP] {e}")


def cleanup_files(files: List[str]):
    for file_path in files:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[CLEANUP] Removed file: {file_path}")


# -----------------------------------------------------------------------------
# Main 4-Step Processing Approach
# -----------------------------------------------------------------------------

def process_file_four_step(source_file: str, output_dir: str):
    """
    The pipeline includes:
      STEP A: Gprof
      STEP B: Valgrind
      STEP C: Perf Record
      STEP D: Perf Stat
    """
    all_analysis = []
    os.makedirs(output_dir, exist_ok=True)

    gprof_exe    = os.path.join(output_dir, "example_gprof.x")
    valgrind_exe = os.path.join(output_dir, "example_valgrind.x")
    perf_exe     = os.path.join(output_dir, "example_perf.x")

    # -------------------------------------------------------------------------
    # STEP A: Gprof
    # -------------------------------------------------------------------------
    print("\n--- STEP A: Gprof Analysis ---")
    try:
        compile_code(source_file, gprof_exe, flags=["-g", "-pg"])
        print("[PROGRAM OUTPUT] (gprof build)")
        program_output = run_program(gprof_exe)
        print(program_output)

        gprof_text = run_gprof(gprof_exe)
        parsed_gprof = parse_gprof_output(gprof_text)

        print("\n[GPROF FLAT PROFILE]")
        for entry in parsed_gprof["flat_profile"]:
            print(entry)

        print("\n[GPROF CALL GRAPH]")
        for func_id, info in parsed_gprof["call_graph"].items():
            print(f"Function ID [{func_id}]: {info}")
        all_analysis.append(parsed_gprof)

    except subprocess.CalledProcessError as e:
        print(f"[ERROR - GPROF STEP] Subprocess failed: {e}")
    finally:
        cleanup_files(["gmon.out", gprof_exe])

    # -------------------------------------------------------------------------
    # STEP B: Valgrind
    # -------------------------------------------------------------------------
    print("\n--- STEP B: Valgrind Analysis ---")
    try:
        compile_code(source_file, valgrind_exe, flags=["-g"])
        valgrind_text = run_valgrind(valgrind_exe)
        valgrind_analysis = parse_valgrind_output(valgrind_text)

        print("[VALGRIND ANALYSIS]")
        for k, v in valgrind_analysis.items():
            print(f"{k}: {v}")
        all_analysis.append(valgrind_analysis)

    except subprocess.CalledProcessError as e:
        print(f"[ERROR - VALGRIND STEP] Subprocess failed: {e}")
    finally:
        cleanup_files([valgrind_exe])

    # -------------------------------------------------------------------------
    # STEP C: Perf Record
    # -------------------------------------------------------------------------
    print("\n--- STEP C: Perf Record Analysis ---")
    try:
        compile_code(source_file, perf_exe, flags=["-g"])
        perf_data_dict = run_perf_with_timing(perf_exe, frequency=1000)
        print(f"[PERF RECORD] Execution Time: {perf_data_dict['execution_time']:.4f}s")

        perf_results = parse_perf_output(perf_data_dict["perf_output"])
        print("[PERF RECORD ANALYSIS]")
        for entry in perf_results:
            print(entry)
        
        all_analysis.append(perf_data_dict)

    except subprocess.CalledProcessError as e:
        print(f"[ERROR - PERF RECORD STEP] Subprocess failed: {e}")
    finally:
        cleanup_files([perf_exe, "perf.data"])

    # -------------------------------------------------------------------------
    # STEP D: Perf Stat
    # -------------------------------------------------------------------------
    print("\n--- STEP D: Perf Stat Analysis ---")
    try:
        # Recompile again (or you could reuse the same binary, but we do a fresh compile)
        compile_code(source_file, perf_exe, flags=["-g"])
        perf_stats =process_perf_stat(perf_exe)
        all_analysis.append(perf_stats)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR - PERF STAT STEP] Subprocess failed: {e}")
    finally:
        cleanup_files([perf_exe])
    
    return all_analysis
        



def run_analysis(code:str):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    analysis_dir = os.path.join(base_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)

    source_file = os.path.join(analysis_dir, "example.cpp")
    
    with open(source_file, "w") as f:
        f.write(code)

    # Now run the four-step process
    return process_file_four_step(source_file, analysis_dir)
