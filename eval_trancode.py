import os
import sys
import json
import shutil
import logging
import subprocess
import tempfile
import re

# Default timeout in seconds for each test run.
DEFAULT_TIMEOUT = 10

# --- Helper Functions ---

def run_python_test(source_code, timeout):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(source_code)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired:
        logging.error("Python test timed out.")
        stdout = ""
        stderr = "TimeoutExpired"
    finally:
        os.unlink(tmp_path)
    return stdout, stderr

def run_cpp_test(source_code, timeout):
    def fix_cpp_includes(source_code):
        if "#include <bits/stdc++.h>" in source_code:
            replacement = (
                "#include <iostream>\n"
                "#include <vector>\n"
                "#include <algorithm>\n"
                "#include <cmath>\n"
                "#include <cstdlib>\n"
                "#include <cstdio>\n"
                "#include <cstring>\n"
                "#include <sstream>\n"
                "#include <climits>\n"
                "#include <stack>\n"
                "#include <unordered_map>\n"
                "#include <queue>\n"
                "#include <unordered_set>\n"

            )
            logging.info("Replacing '#include <bits/stdc++.h>' with standard headers.")
            source_code = source_code.replace("#include <bits/stdc++.h>", replacement)
        extra = ""
        if "#include <set>" not in source_code:
            extra += "#include <set>\n"
        if "unordered_set" in source_code and "#include <unordered_set>" not in source_code:
            extra += "#include <unordered_set>\n"
        if "using namespace std;" not in source_code:
            extra += "using namespace std;\n"
        if extra:
            source_code = extra + source_code
        return source_code

    source_code = fix_cpp_includes(source_code)
    temp_dir = tempfile.mkdtemp()
    cpp_file = os.path.join(temp_dir, "temp_test.cpp")
    binary_file = os.path.join(temp_dir, "temp_test.out")

    with open(cpp_file, "w", encoding="utf-8") as f:
        f.write(source_code)

    compile_cmd = ["g++", cpp_file, "-o", binary_file, "-O2", "-std=gnu++11"]
    try:
        compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=timeout)
        if compile_proc.returncode != 0:
            logging.error("C++ compilation failed:\n%s", compile_proc.stderr)
            shutil.rmtree(temp_dir)
            return "", compile_proc.stderr
    except subprocess.TimeoutExpired:
        logging.error("C++ compilation timed out.")
        shutil.rmtree(temp_dir)
        return "", "Compilation TimeoutExpired"

    try:
        run_proc = subprocess.run([binary_file], capture_output=True, text=True, timeout=timeout)
        stdout = run_proc.stdout
        stderr = run_proc.stderr
    except subprocess.TimeoutExpired:
        logging.error("C++ test execution timed out.")
        stdout = ""
        stderr = "Execution TimeoutExpired"

    shutil.rmtree(temp_dir)
    return stdout, stderr

def run_java_test(source_code, timeout):
    def fix_java_imports(source_code):
        source_code = re.sub(r'import\s+java\.lang\.\*;\s*\n', '', source_code)
        source_code = re.sub(r'import\s+javafx\.util\.Pair;\s*\n', '', source_code)
        source_code = re.sub(r'(import\s+[a-zA-Z0-9_.]+)\.\s+\*;', r'\1.*;', source_code)
        if ("Pair<" in source_code or "Pair " in source_code) and not re.search(r'class\s+Pair\s*<', source_code):
            pair_def = (
                "class Pair<K, V> {\n"
                "    private final K key;\n"
                "    private final V value;\n"
                "    public Pair(K key, V value) { this.key = key; this.value = value; }\n"
                "    public K getKey() { return key; }\n"
                "    public V getValue() { return value; }\n"
                "}\n\n"
            )
            match = re.search(r'((?:import\s+.*;\s*\n)+)', source_code)
            if match:
                imports_block = match.group(1)
                source_code = source_code.replace(imports_block, imports_block + pair_def, 1)
            else:
                match = re.search(r'(package\s+.*;\s*\n)', source_code)
                if match:
                    package_line = match.group(1)
                    source_code = source_code.replace(package_line, package_line + pair_def, 1)
                else:
                    source_code = pair_def + source_code
        open_braces = source_code.count('{')
        close_braces = source_code.count('}')
        if open_braces > close_braces:
            source_code += "\n" + "}" * (open_braces - close_braces)
        return source_code

    source_code = fix_java_imports(source_code)
    temp_dir = tempfile.mkdtemp()
    def extract_class_name(java_source):
        match = re.search(r'public\s+class\s+(\w+)', java_source)
        if match:
            return match.group(1)
        return None
    class_name = extract_class_name(source_code)
    if not class_name:
        logging.error("Could not extract Java class name.")
        shutil.rmtree(temp_dir)
        return "", "Class name extraction error"

    java_file = os.path.join(temp_dir, f"{class_name}.java")
    with open(java_file, "w", encoding="utf-8") as f:
        f.write(source_code)

    compile_cmd = ["javac", java_file]
    try:
        compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=timeout)
        if compile_proc.returncode != 0:
            logging.error("Java compilation failed:\n%s", compile_proc.stderr)
            shutil.rmtree(temp_dir)
            return "", compile_proc.stderr
    except subprocess.TimeoutExpired:
        logging.error("Java compilation timed out.")
        shutil.rmtree(temp_dir)
        return "", "Compilation TimeoutExpired"

    try:
        run_cmd = ["java", "-cp", temp_dir, class_name]
        run_proc = subprocess.run(run_cmd, capture_output=True, text=True, timeout=timeout)
        stdout = run_proc.stdout
        stderr = run_proc.stderr
    except subprocess.TimeoutExpired:
        logging.error("Java test execution timed out.")
        stdout = ""
        stderr = "Execution TimeoutExpired"

    shutil.rmtree(temp_dir)
    return stdout, stderr

def parse_test_results(output):
    """
    Parse the test output to find a line that starts with "#Results:".
    Expected format: "#Results: X, Y" where X = passed count, Y = total tests.
    Returns a tuple (passed, total) if found, otherwise (None, None).
    """
    for line in output.splitlines():
        if line.strip().startswith("#Results:"):
            try:
                parts = line.strip().split(":")[1].split(",")
                passed = int(parts[0].strip())
                total = int(parts[1].strip())
                return passed, total
            except Exception:
                return None, None
    return None, None

def load_tests(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logging.error("Error loading JSON file '%s': %s", json_file, str(e))
        sys.exit(1)

def run_test_for_function(func_name, lang, tests_data, impl_file, timeout):
    if lang not in tests_data[func_name]:
        logging.error("No test data for function '%s' in language '%s'.", func_name, lang)
        return

    f_gold_code = tests_data[func_name][lang].get("f_gold", "")
    test_code = tests_data[func_name][lang].get("test", "")

    if not f_gold_code:
        logging.error("Missing f_gold code for '%s' in language '%s'.", func_name, lang)
        return

    if impl_file:
        try:
            with open(impl_file, "r", encoding="utf-8") as f:
                candidate = f.read()
            logging.info("Using user-provided implementation from '%s'.", impl_file)
        except Exception as e:
            logging.error("Error reading implementation file '%s': %s", impl_file, str(e))
            sys.exit(1)
    else:
        # Default candidate comes from f_gold code renamed.
        if lang.lower() == "python":
            candidate = f_gold_code.replace("def f_gold", "def f_filled", 1)
        elif lang.lower() in ["cpp", "java"]:
            candidate = f_gold_code.replace("f_gold", "f_filled", 1)
        else:
            candidate = ""
        logging.info("Using default candidate (duplicate of f_gold) for language '%s'.", lang)

    if "#TOFILL" in test_code:
        test_code = test_code.replace("#TOFILL", candidate)
    elif "TOFILL" in test_code:
        test_code = test_code.replace("TOFILL", candidate)
    else:
        test_code = candidate + "\n" + test_code

    full_code = f_gold_code + "\n" + test_code

    if lang == "python":
        stdout, stderr = run_python_test(full_code, timeout)
    elif lang == "cpp":
        stdout, stderr = run_cpp_test(full_code, timeout)
    elif lang == "java":
        stdout, stderr = run_java_test(full_code, timeout)
    else:
        logging.error("Unsupported language: %s", lang)
        return

    logging.info("Test output for '%s' (%s):\n%s", func_name, lang, stdout)
    if stderr:
        logging.error("Errors during test for '%s' (%s):\n%s", func_name, lang, stderr)

    passed, total = parse_test_results(stdout)
    if passed is None or total is None:
        print(f"Test failed to run for {func_name}, counting as 0/10.")
        passed, total = 0, 10

    return passed, total

def rename_candidate(candidate_code, language):
    """
    Extract the function's original name from its definition in the candidate code
    and replace every occurrence of that name with 'f_filled'.
    """
    if language == "python":
        pattern = r"def\s+(\w+)\s*\("
    elif language == "java":
        pattern = r"(?:public\s+|private\s+|protected\s+|static\s+)*\s*\w+\s+(\w+)\s*\("
    elif language == "cpp":
        pattern = r"(?:\w+\s+)+(\w+)\s*\("
    else:
        pattern = r"def\s+(\w+)\s*\("

    match = re.search(pattern, candidate_code)
    if match:
        orig_name = match.group(1)
        candidate_code = re.sub(r"\b" + re.escape(orig_name) + r"\b", "f_filled", candidate_code)
    return candidate_code

def remove_main(candidate_code, language):
    """
    Remove any main function from the candidate code.
    For Python, remove the block starting with "if __name__ == '__main__':".
    For Java, remove the main method.
    For C++, delete everything starting at the first occurrence of 'int main(' or 'void main('.
    """
    if language == "python":
        parts = re.split(r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:", candidate_code)
        return parts[0]
    elif language == "java":
        # Remove the main method using a non-greedy match.
        return re.sub(r"public\s+static\s+void\s+main\s*\([^)]*\)\s*\{.*?\}", "", candidate_code, flags=re.DOTALL)
    elif language == "cpp":
        main_pos = None
        for pattern in [r"int\s+main\s*\(", r"void\s+main\s*\("]:
            match = re.search(pattern, candidate_code)
            if match:
                pos = match.start()
                if main_pos is None or pos < main_pos:
                    main_pos = pos
        if main_pos is not None:
            candidate_code = candidate_code[:main_pos].rstrip()
        return candidate_code
    else:
        return candidate_code

def evaluate_translations_against_tests(translation_json_path, test_json_path, language="python", timeout=10):
    try:
        with open(translation_json_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
        with open(test_json_path, "r", encoding="utf-8") as f:
            tests_data = json.load(f)
    except Exception as e:
        logging.error("Error loading input files: %s", str(e))
        return

    passed_total = 0
    total_tests = 0
    missing_tests = []
    partial_passes = []

    for entry in translations:
        func_id = entry.get("function_id")
        if not func_id:
            continue

        translated_code = entry.get("translated_code", "")
        match = re.search(r"```(?:\w+)?\n(.*?)```", translated_code, re.DOTALL)

        candidate_code = match.group(1) if match else translated_code

        # --- Rename the translated function to f_filled uniformly ---
        candidate_code = rename_candidate(candidate_code, language)
        # --- Remove any additional main from candidate code ---
        candidate_code = remove_main(candidate_code, language)
        # --- End modifications ---

        if func_id not in tests_data or language not in tests_data[func_id]:
            logging.warning("Skipping %s: no %s test available.", func_id, language)
            missing_tests.append(func_id)
            continue

        f_gold_code = tests_data[func_id][language].get("f_gold", "")
        test_code = tests_data[func_id][language].get("test", "")
        if not f_gold_code or not test_code:
            logging.warning("Skipping %s: missing f_gold or test.", func_id)
            missing_tests.append(func_id)
            continue

        if "#TOFILL" in test_code:
            test_code = test_code.replace("#TOFILL", candidate_code)
        elif "TOFILL" in test_code:
            test_code = test_code.replace("//TOFILL", candidate_code)
        else:
            test_code = candidate_code + "\n" + test_code

        full_code = f_gold_code + "\n" + test_code

        if language == "python":
            stdout, stderr = run_python_test(full_code, timeout)
        elif language == "java":
            stdout, stderr = run_java_test(full_code, timeout)
        elif language == "cpp":
            stdout, stderr = run_cpp_test(full_code, timeout)
        else:
            logging.error("Unsupported language: %s", language)
            continue

        result = parse_test_results(stdout)
        if result is None or result[0] is None or result[1] is None:
            print(f"⚠️  Test failed to run for {func_id}, counting as 0/10.")
            passed, total = 0, 10
            partial_passes.append((func_id, passed, total))
        else:
            passed, total = result
            if passed != total:
                partial_passes.append((func_id, passed, total))

        total_tests += total
        passed_total += passed
        status = "PASS" if passed == total else f"{passed}/{total}"
        print(f"{status} - {func_id}")

    # Save missing tests to a JSON file.
    missing_tests_records = [{"test_name": func_id} for func_id in missing_tests]
    with open("missing_tests.json", "w", encoding="utf-8") as f:
        json.dump(missing_tests_records, f, indent=4)

    # Save partial passes to a text file.
    with open("partial_passes.txt", "w") as f:
        for func_id, passed, total in partial_passes:
            f.write(f"{func_id}: {passed}/{total}\n")

    print(f"\n=== Final Score: {passed_total} / {total_tests} passed ===")
    print(f"Missing tests: {len(missing_tests)}")
    print(f"Partial passes: {len(partial_passes)}")
    return f"\n=== Final Score: {passed_total} / {total_tests} passed ==="

def main():
    # Set your variables here instead of using command-line arguments.
    # Set evaluation_mode to True to run evaluate_translations_against_tests,
    # or False to run the regular test mode.
    evaluation_mode = True
    timeout = DEFAULT_TIMEOUT
    
    systems = ["small","medium","large"]
    models = [
    "Meta-Llama-3.3-70B-Instruct",
    "Meta-Llama-3.1-70B-Instruct",
    "Meta-Llama-3.1-405B-Instruct",
]
    languages = ["python","java","cpp"]

    results = {}
    for language in languages:
        for language2 in languages:
            if language == language2:
                continue
            for model in models:
                for system in systems:
                    if evaluation_mode:
                        translation_json_path = f"outputs/{language2}/{language}_to_{language2}_{model}_{system}.json"
                        test_json_path = "run_evals/codes_and_tests.json"
                        result = evaluate_translations_against_tests(translation_json_path, test_json_path, language2, timeout)
                        results[f"{language}_to_{language2}_{model}_{system}"] = result
                    


    print(results)


if __name__ == "__main__":
    main()
