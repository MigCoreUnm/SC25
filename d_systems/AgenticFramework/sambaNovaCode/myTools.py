from langchain_core.tools import  tool
import timeit
from AgenticFramework.sambaNovaCode.cpp_analyzer import run_analysis
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_milvus import Milvus
import os
import subprocess
import tempfile
import sys
import os
import importlib.util
import cProfile
import pstats
import io
import tracemalloc
import time
import subprocess
import cProfile
import pstats
import tracemalloc
import time
import timeit
import io
import tempfile

import subprocess
import tempfile
import cProfile
import tracemalloc
import time
import io
import pstats
import timeit
import concurrent.futures

###############################
# 1. System Package Installation
###############################
def install_package(package_name):
    """
    Installs a system package using apt-get.
    """
    try:
        subprocess.run(['sudo', 'apt-get', 'update'],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(['sudo', 'apt-get', 'install', '-y', package_name],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package_name}: {e.stderr.decode()}")
        return False


###############################
# 2. Conda Environment Helpers (For run_py)
###############################
def create_conda_env(env_name: str, python_version="3.10") -> bool:
    """
    Create a new conda environment named env_name with the specified Python version.
    """
    try:
        cmd = [
            "conda", "create",
            "-n", env_name,
            f"python={python_version}",
            "-y"
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating conda env {env_name}: {e.stderr}")
        return False


def remove_conda_env(env_name: str):
    """
    Remove the specified conda environment.
    """
    try:
        cmd = ["conda", "env", "remove", "-n", env_name, "-y"]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Error removing conda env {env_name}: {e.stderr}")

@tool
def install_conda_or_pip(package_names: list) -> bool:
    """
    Installs a package into the given conda environment. First tries `conda install`,
    then falls back to pip install (via `conda run -n ... python -m pip install ...`)
    if conda install fails.
    Parameters:
    package_names: list -> a list of dependencies that need to be installed.
    Returns:
        bool: True if installation succeeded, False otherwise.
    """
    env_name = "temp_env_1"
    # 1. Attempt conda install
    for package_name in package_names:
        print(f"Attempting to conda-install '{package_name}' into env '{env_name}'...")
        try:
            conda_cmd = ["conda", "install", "-n", env_name, "-y", package_name]
            subprocess.run(conda_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Conda installation of '{package_name}' succeeded.")
        except subprocess.CalledProcessError as e_conda:
            print(f"Conda installation failed for '{package_name}': {e_conda.stderr.decode()}")

        # 2. Fallback to pip install
        #    We run pip from inside the conda environment with: conda run -n env python -m pip install ...
        print(f"Attempting to pip-install '{package_name}' into env '{env_name}'...")
        try:
            pip_cmd = ["conda", "run", "-n", env_name, "python", "-m", "pip", "install", package_name]
            subprocess.run(pip_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"pip installation of '{package_name}' succeeded.")
        except subprocess.CalledProcessError as e_pip:
            print(f"pip installation failed for '{package_name}': {e_pip.stderr.decode()}")

    # If both conda and pip fail, return False
    return True

###############################
# 3. Tools: run_c
###############################

    
    # Optionally, clean up the temporary file:
    # os.remove(filename)
    
    return {
        "static_reports": static_reports,
        "dynamic_profile": profile_report,
        "memory_report": mem_report,
        "benchmark_time": benchmark_time,
    }
@tool
def run_c(c_code: str) -> str:
    """
    Compiles and executes the provided C++ code.


    Steps:
      2. Compile the C++ code using g++.
      3. Execute the compiled binary.
      4. Clean up temporary files.
    """
    # Step 1: Install extra dependencies
    # if dependencies:
    #     for dep in dependencies:
    #         if not install_package(dep):
    #             return f"Failed to install dependency: {dep}"

    # Step 2: Compile & Execute
    source_file = None
    executable = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.cpp', prefix='test_') as filep:
            filep.write(c_code)
            source_file = filep.name

        executable = source_file.replace('.cpp', '')

        compile_process = subprocess.run(
            ['g++', source_file, '-o', executable, '-std=c++17'],
            capture_output=True,
            text=True
        )
        if compile_process.returncode != 0:
            return f"Compilation failed:\n{compile_process.stderr}"

        run_process = subprocess.run(
            [executable],
            capture_output=True,
            text=True,
            timeout = 60
        )
        if run_process.returncode != 0:
            return f"Execution failed:\n{run_process.stderr}"

        return run_process.stdout
    except Exception as e:
        return f"Unexpected error: {str(e)}"
    finally:
        if source_file and os.path.exists(source_file):
            os.unlink(source_file)
        if executable and os.path.exists(executable):
            os.unlink(executable)

def conda_env_exists(env_name):
    result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
    envs = result.stdout.splitlines()
    return any(env_name in line for line in envs)

###############################
# 4. Tools: run_py
###############################

@tool
def run_py(py_code: str) -> str:
    """
    Execute Python code in a secure, isolated temporary Conda environment.

    ---
    **Parameters:**
    - `py_code` (str): The Python code to be executed. Assure to capture all the code that is needed for this program to be run

      
      
    ### **Returns:**
    - A string containing either:
      - The standard output of the executed Python code.
      - An error message if execution fails.


    """

    import tempfile, subprocess, os

    # Step 1: Create a unique conda environment name.
    env_name = "temp_env_1"

    print(f"{py_code}")


    try:
        # --- Prepend sys.path modification code ---

        # Prepend the sys.path modification code to the provided user code.
        full_code =  py_code

        # Step 3: Write the modified code to a temporary file and execute it.
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.py', prefix='test_') as f:
                f.write(full_code)
                tmp_file = f.name

            cmd = ["conda", "run", "-n", env_name, "python", tmp_file]
            run_process = subprocess.run(cmd, capture_output=True, text=True,timeout=60)
            if run_process.returncode != 0:
                return f"Execution failed:\n{run_process.stderr}"

            return "Ran the output was : "+run_process.stdout + run_process.stderr
        finally:
            if tmp_file and os.path.exists(tmp_file):
                os.unlink(tmp_file)
    except Exception as e:
        return f"Unexpected error: {str(e)}"


###############################
# 5. Tools: run_fortran
###############################
@tool
def run_fortran(fortran_code: str, dependencies: list = None) -> str:
    """
    Compiles and executes the provided Fortran code.

    Only installs manually specified packages (via 'dependencies').

    Steps:
      1. Install any extra dependencies from 'dependencies'.
      2. Write the code to a .f90 file.
      3. Compile with gfortran.
      4. Execute the binary.
      5. Cleanup.
    """
    # Step 1: Install extra dependencies
    if dependencies:
        for dep in dependencies:
            if not install_package(dep):
                return f"Failed to install dependency: {dep}"

    # Step 2: Write Fortran code to temp file
    cleaned_code = (fortran_code.replace("\\n", "\n")
                                .replace('\\"', "'"))
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.f90', prefix='fortran_test_') as source_file:
        source_file.write(cleaned_code)
        source_file_path = source_file.name

    # Step 3: Compile & Execute
    binary_file_path = source_file_path.replace(".f90", "")
    try:
        compile_process = subprocess.run(
            ["gfortran", "-o", binary_file_path, source_file_path],
            capture_output=True,
            text=True
        )
        if compile_process.returncode != 0:
            return f"Compilation failed:\n{compile_process.stderr}"

        run_process = subprocess.run(
            [binary_file_path],
            capture_output=True,
            text=True
        )
        if run_process.returncode != 0:
            return f"Execution failed:\n{run_process.stderr}"

        return run_process.stdout
    finally:
        try:
            os.remove(source_file_path)
        except OSError:
            pass
        try:
            os.remove(binary_file_path)
        except OSError:
            pass


###############################
# 6. Tools: run_java
###############################
@tool
def run_java(java_code: str) -> str:
    """
    Compiles and executes the provided Java code using 'javac' and 'java'.


    Steps:
      2. Create a temp directory.
      3. Write the code to `Main.java`.
      4. Compile with `javac`.
      5. Run via `java -cp <temp_dir> Main`.
      6. Capture and return stdout.
      7. Cleanup.
    """
    try:
        # Step 2: Temp directory for .java
        with tempfile.TemporaryDirectory() as temp_dir:
            java_file_path = os.path.join(temp_dir, "Main.java")
            with open(java_file_path, "w") as f:
                f.write(java_code)

            # Step 3: Compile
            compile_process = subprocess.run(
                ["javac", java_file_path],
                capture_output=True,
                text=True,
                timeout = 60
            )
            if compile_process.returncode != 0:
                return f"Java compilation failed:\n{compile_process.stderr}"

            # Step 4: Execute
            run_process = subprocess.run(
                ["java", "-cp", temp_dir, "Main"],
                capture_output=True,
                text=True
            )
            if run_process.returncode != 0:
                return f"Java execution failed:\n{run_process.stderr}"

            return run_process.stdout
    except Exception as e:
        return f"error running code {e}"


###############################
# 7. Tools: run_js
###############################
@tool
def run_js(js_code: str, dependencies: list = None) -> str:
    """
    Executes JavaScript code using Node.js.

    Only installs manually specified packages (via 'dependencies').

    Steps:
      1. Install extra dependencies if provided.
      2. Create a temp file for the JS code.
      3. Run it via `node`.
      4. Capture stdout.
      5. Cleanup.
    """
    # Step 1: Install extra dependencies
    if dependencies:
        for dep in dependencies:
            if not install_package(dep):
                return f"Failed to install dependency: {dep}"

    # Step 2: Create temp JS file & run
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.js', prefix='js_test_') as js_file:
        js_file.write(js_code)
        js_file_path = js_file.name

    try:
        run_process = subprocess.run(
            ["node", js_file_path],
            capture_output=True,
            text=True
        )
        if run_process.returncode != 0:
            return f"JS execution failed:\n{run_process.stderr}"

        return run_process.stdout
    finally:
        if os.path.exists(js_file_path):
            os.remove(js_file_path)


###############################
# 8. Tools: run_tests
###############################

def run_static_tool(command, timeout=10):
    """Runs a shell command with a timeout and returns its output or logs an issue if it fails."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True, timeout=timeout)
        return result.stdout if result.returncode == 0 else "Issue detected"
    except subprocess.TimeoutExpired:
        return "Timeout expired"
    except Exception:
        return "Issue detected"

def run_static_analysis(code):
    """Runs Pylint, Flake8, MyPy, and Radon on the given Python code."""
    results = {}

    # Store code in a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
        temp_file.write(code.encode('utf-8'))
        temp_file.flush()
        temp_filename = temp_file.name

    # Run static analysis tools with timeout
    results["pylint"] = run_static_tool(f"pylint {temp_filename}")
    results["flake8"] = run_static_tool(f"flake8 {temp_filename}")
    results["mypy"] = run_static_tool(f"mypy {temp_filename}")
    results["radon_cc"] = run_static_tool(f"radon cc {temp_filename} -nc")  # Cyclomatic complexity
    results["radon_mi"] = run_static_tool(f"radon mi {temp_filename}")  # Maintainability index

    return results

def execute_with_timeout(code, timeout=10):
    """Executes the given code with a timeout."""
    def execute():
        namespace = {}
        compiled_code = compile(code, '<string>', 'exec')
        exec(compiled_code, namespace)
        if 'main' in namespace and callable(namespace['main']):
            namespace['main']()
        return namespace

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(execute)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return "Execution timed out"
        except Exception:
            return "Execution failed"

def run_dynamic_analysis(code):
    """Runs dynamic profiling using cProfile, tracemalloc, and timeit."""
    results = {}

    try:
        compiled_code = compile(code, '<string>', 'exec')
    except Exception:
        return {"compilation": "Issue detected"}

    profiler = cProfile.Profile()
    tracemalloc.start()
    start_time = time.perf_counter()
    
    try:
        profiler.enable()
        execution_result = execute_with_timeout(compiled_code, timeout=10)
        profiler.disable()
    except Exception:
        profiler.disable()
        tracemalloc.stop()
        return {"execution": "Issue detected"}

    if execution_result in ["Execution timed out", "Execution failed"]:
        return {"execution": execution_result}

    end_time = time.perf_counter()
    execution_time = end_time - start_time

    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumtime')
    ps.print_stats()
    profile_results = s.getvalue()

    top_stats = snapshot.statistics('lineno')
    memory_usage_top_stats = [str(stat) for stat in top_stats[:10]]

    results["execution_time_seconds"] = execution_time
    results["profile_results"] = profile_results
    results["memory_usage_top_stats"] = memory_usage_top_stats

    if "main" in execution_result and callable(execution_result["main"]):
        try:
            results["benchmark_time"] = timeit.timeit(lambda: execution_result["main"](), number=10)
        except Exception:
            results["benchmark_time"] = "Issue detected"
    else:
        results["benchmark_time"] = None

    return results

@tool
def run_tests(code : str):
    """
    parameters:
    code is a string of code that will analyzed


    Runs both static (linting, complexity, type checks) and dynamic (performance, memory) analysis on Python code.
    
    - Uses pylint, flake8, mypy, and radon for static analysis.
    - Uses cProfile and tracemalloc for dynamic profiling.

    Returns:
        dict: Combined results from static and dynamic analysis.
    """
    return {
        "static_analysis": run_static_analysis(code),
        "dynamic_analysis": run_dynamic_analysis(code)
    }


class embeddingDataSet:
    """
    Manages embedding models and interactions with a Milvus vector database.
    This class handles:
    - Initialization of the embedding model.
    - Creation and management of the Milvus database.
    - Adding documents to the database.
    - Performing vector-based searches.
    """
    # Initialize the embedding model using a pre-trained SentenceTransformer model
    embedding_model = HuggingFaceEmbeddings(model_name='sentence-transformers/multi-qa-MiniLM-L6-cos-v1')
    database = None  # Placeholder for the Milvus database instance
    @classmethod
    def init_database(cls, documents: list):
        """
        Initializes the Milvus database and adds the provided documents.
        This method performs the following steps:
        1. Establishes a connection to the Milvus database.
        2. Converts each document string into a Document object.
        3. Adds all Document objects to the Milvus database for vector storage.
        Args:
            documents (list): A list of document strings to be added to the database.
        """
        URI = "./milvus_example.db"  # Path or URI to the Milvus database
        documentsList = []
        index_params = {
        "index_type": "FLAT",
        "metric_type": "L2",
        "params": {}
        }
        # Initialize the Milvus database with the embedding function
        cls.database = Milvus(
            embedding_function=cls.embedding_model,
            auto_id= True,
            connection_args={"uri": URI},
            index_params=index_params
        )
        # Convert each string document into a Document object
        for doc in documents:
            document = Document(page_content=doc)
            documentsList.append(document)
        # Add all documents to the Milvus database
        cls.database.add_documents(documents=documentsList)
    @classmethod
    def add_to_db(cls, data: str):
        """
        Adds additional text data to the Milvus database.
        This method converts the input data into a string and adds it to the existing database.
        """
        data = str(data)
        cls.database.add_texts(data)
    @classmethod
    def vector_search(cls, string: str) -> str:
        """
        Performs a vector-based search on the Milvus database using the provided query string.
        This method:
        1. Converts the query string into its vector representation using the embedding model.
        2. Queries the Milvus database for the most similar documents.
        3. Cleans and concatenates the retrieved documents into a single string.
        """
        # Invoke the retriever to perform vector-based search
        results = cls.database.as_retriever().invoke(string)
        cleaned = []
        # Extract the page content from each retrieved document
        for result in results:
            cleaned.append(result.page_content)
        # Concatenate all cleaned documents into a single string separated by newlines
        ret_string = ""
        for clean in cleaned:
            ret_string = ret_string + "\n\n" + clean
        return results[0]


def write_to_file(code: str, filename: str,folder:str):
    """
    Writes Python code to a file with a .py extension.

    Parameters:
    - code (str): The Python code to write into the file.
    - filename (str): Desired filename.

    Returns:
    - dict: Status indicating success or error details.
    """

    folder_path = f"Tests/{folder}/"
    # Join folder path and filename
    full_path = os.path.join(folder_path, filename) if folder_path else filename

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        with open(full_path, 'w', encoding='utf-8') as file:
            file.write(code)
        return {
            "status": "success",
            "message": f"Python file '{full_path}' written successfully."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to write file '{full_path}': {str(e)}"
        }