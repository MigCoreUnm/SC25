import os
import json
import sys 

HERE = os.path.dirname(__file__) 
DSYS = os.path.join(HERE, "d_systems")
sys.path.insert(0, DSYS)

from AgenticFramework.AgenticSystem import Node
from full_systemTC import full_system
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
languages =["python","cpp","java"]
files = {
    "python": f"{BASE_DIR}/run_evals/python_tests.json",
    "cpp": f"{BASE_DIR}/run_evals/cpp_tests.json",
    "java": f"{BASE_DIR}/run_evals/java_tests.json"
}
models = [
    "Meta-Llama-3.1-405B-Instruct",
    "Meta-Llama-3.3-70B-Instruct"
]

output_dir = "outputs"

os.makedirs(output_dir, exist_ok=True)





def load_tests(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def save_incremental(base_lang, target_lang, model, system_size, records):
    file_name = f"{base_lang}_to_{target_lang}_{model}_{system_size}.json"
    out_path = os.path.join(output_dir, f"{target_lang}")
    out_path = os.path.join(out_path, file_name)
    with open(out_path, 'w') as f:
        json.dump(records, f, indent=2)




for model in models:
    print(f"\nRunning translations with model: {model}")

    for base_lang in languages:
        print(f"  Base language: {base_lang}")
        test_data = load_tests(files[base_lang])

        for target_lang in languages:
            if target_lang == base_lang:
                continue



            # Store translations for all 3 system sizes
            small_records = []
            medium_records = []
            large_records = []

            for test in test_data:
                function_id = test.get("function_id", "unknown_function")
                function_signature = test.get("function_signature", "")
                function_code = test.get("function_code", "")
                full_code = f"{function_signature} {function_code}"

                record_base = {
                    "function_id": function_id,
                    "original_language": base_lang,
                    "function_signature": function_signature,
                    "function_code": function_code,
                }

                prompt = (
                    f"Your role is to translate the following function from {base_lang} to {target_lang}:\n\n"
                    f"{full_code}\n\n"
                    "\n Do not include any extra commentary, error statements, or unit tests.  simply translate the code. \n"
                )
                prompt2 = prompt + "Do not provide any additional commentary. Return only the translated code."

                # Small system (Node)
                try:
                    small_system = Node(instructions=prompt2, cot='', model=model)
                    result_small = small_system.generate("").content
                    print(result_small)
                    small_records.append({**record_base, "translated_code": result_small})
                except Exception as e:
                    small_records.append({**record_base, "translated_code": f"ERROR: {str(e)}"})

                # Medium and Large systems (from full_system)
                try:
                    medium_system, large_system, regens, time = full_system(prompt, model=model)
                    medium_records.append({**record_base, "translated_code": medium_system})
                    print(medium_records)
                    large_records.append({**record_base, "translated_code": large_system,"regens" :regens,"time":time})
                    print(large_records)

                except Exception as e:
                    err_msg = f"ERROR: {str(e)}"
                    medium_records.append({**record_base, "translated_code": err_msg})
                    large_records.append({**record_base, "translated_code": err_msg})
                

            # Save outputs per target
            save_incremental(base_lang, target_lang, model, "small", small_records)
            save_incremental(base_lang, target_lang, model, "medium", medium_records)
            save_incremental(base_lang, target_lang, model, "large", large_records)

            print(f"      Saved: {base_lang}_to_{target_lang}_{model}_*.json")
