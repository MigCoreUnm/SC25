import os
from sambaNovaCode.cpp_analyzer import compile_code, run_gprof,run_program,run_valgrind,write_code_to_file, clean_temp_files
import subprocess
import tempfile
from OnPremLLM.execution import execution


# Mapping of C++ include directories to their corresponding Debian package names.
C_INCLUDE_TO_PACKAGE = {
    'boost/': 'libboost-all-dev',
}


@execution
def run_c(c_code:str) -> str:
    """
    Executes the provided C++ code after resolving and installing necessary dependencies.

    This function performs the following steps:
    3. Compiles the C++ code using g++.
    4. Executes the compiled binary.
    5. Cleans up temporary files and uninstalls dependencies.

    Args:
        c_code (CodeInput): The C++ code to execute.

    Returns:
        str: The standard output produced by the executed C++ code.

    Raises:
        Exception: If compilation or execution fails, with details of the error.
    """


    # Create a temporary C++ source file
    filep = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.cpp', prefix='test')
    executable = filep.name.replace('.cpp', '')
    try:
        with open(filep.name, 'w') as file:
            file.write(c_code.code)

        # Compile the C++ code
        compile_process = subprocess.run(
            ['g++', filep.name, '-o', executable, '-std=c++17'],
            capture_output=True,
            text=True
        )
        if compile_process.returncode != 0:
            raise Exception(f"Compilation failed:\n{compile_process.stderr}")

        # Execute the compiled binary
        run_process = subprocess.run(
            [executable],
            capture_output=True,
            text=True
        )
        if run_process.returncode != 0:
            raise Exception(f"Execution failed:\n{run_process.stderr}")

        return run_process.stdout
    finally:
        # Clean up temporary files and uninstall dependencies
        if os.path.exists(filep.name):
            os.unlink(filep.name)
        if os.path.exists(executable):
            os.unlink(executable)

@execution
def run_tests(code:str) ->str:
    """
    Compiles, runs, and profiles a C++ source code provided as a string.

    This function performs the following steps:
    1. Writes the provided C++ code (as a string) to a temporary source file (`temp_code.cpp`).
    2. Compiles the source code into an executable (`temp_code`).
    3. Runs the compiled executable, capturing the output.
    4. Runs memory analysis on the executable using Valgrind to detect memory issues.
    5. Runs gprof profiling on the executable and stores the results in a file (`temp_code_gprof_results.txt`).
    6. Cleans up temporary files after execution, including the source file, executable, and profiling data.

    Parameters:
    - code (str): The C++ source code to be compiled and tested.

    Returns:
    - str: A string containing the results of the unit tests, Valgrind output, and gprof profiling.
    """
    source_file = "temp_code.cpp"
    executable = "./temp_code"
    write_code_to_file(code, source_file)

    try:
        compile_code(source_file, executable)
        run_program(executable)
        run_valgrind(executable)
        run_gprof(executable, "temp_code_gprof_results.txt")
    finally:
        clean_temp_files([source_file, "gmon.out", executable])


