#!/usr/bin/env python3
"""
Integration script demonstrating how to:
1) Install and enable the HumanEval framework
2) Generate completions from your own data
3) Evaluate them with the `evaluate_functional_correctness` CLI

IMPORTANT: Running arbitrary, model-generated code is a security risk.
Only do so in a secure sandbox or container.
"""

import os
import subprocess
import pandas as pd
import re
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# If you haven't already, install human-eval:
#   pip install human-eval
# or clone from GitHub: https://github.com/openai/human-eval
# and install locally.
class get_answer():
    def __init__(self):
        self.df = pd.read_json("results_70b3.jsonl", lines=True)
    
    def get_response(self, system: str, id: str):
        # Filter to the row matching `id` and select the `system` column
        # This returns a Series containing one element if `id` is unique
        series = self.df.loc[self.df['id'] == id, system]
        
        # If there's no matching row, return None (or raise an error)
        if series.empty:
            return None
        
        # Return the single value (rather than a Series)
        return series.iloc[0]

    def clean_code_wrapper(self,code_str):
        code_str = re.sub(r'^```python\n?', '', code_str)
        code_str = re.sub(r'```$', '', code_str)
        return code_str.strip()


    # Provide the `generate_one_completion` function:
    def generate_one_completion(self,id: str,system:str) -> str:
        """
        Implement logic to generate or retrieve a single completion for a prompt.
        Below is a placeholder showing how you might retrieve code from a local DataFrame.

        Replace this dummy logic with your actual generation code
        or retrieval of model-generated code from your DataFrame or other source.
        """
        code = self.get_response(system, id)
        print(code)
        clean_code = self.clean_code_wrapper(code)
        return  clean_code



def main():
    # 1) Read the HumanEval problems (requires `human-eval` to be installed).
    from human_eval.human_eval.data import write_jsonl, read_problems
    
    problems = read_problems()  # Dictionary of {task_id: {...problem data...}}
    answer = get_answer()
    systems = ["small_system","medium_system","large_system"]

    # 2) Create a list of completions for each problem.
    # Adjust num_samples_per_task as needed; for demonstration, we'll do 1.
    for system in systems:
        num_samples_per_task = 1
        samples = []
        for task_id, problem_data in problems.items():
            for _ in range(num_samples_per_task):
                id = problem_data["task_id"]
                completion = answer.generate_one_completion(id, system)
                samples.append({
                    "task_id": task_id,
                    "completion": completion  # Completion only, no prompt
                })

        # 3) Write samples to a JSONL file
        output_file = f"{system}_samples.jsonl"
        write_jsonl(output_file, samples)
        print(f"Generated {len(samples)} samples and wrote to {output_file}.")

    # 4) (Optional) Evaluate using the CLI tool
    #    You can run `evaluate_functional_correctness` in a subprocess:
    #    (Make sure `evaluate_functional_correctness` is on your PATH or specify full path.)
        try:
            command = ["evaluate_functional_correctness", output_file]
            print("Running:", " ".join(command))
            subprocess.run(command, check=True)
        except FileNotFoundError:
            print("ERROR: `evaluate_functional_correctness` not found on PATH.")
            print("Make sure you installed human-eval and your environment is active.")
        except subprocess.CalledProcessError as e:
            print("Evaluation script failed with error:")
            print(e)

if __name__ == "__main__":
    """
    IMPORTANT: Make sure you have enabled code execution in the human_eval package
    by uncommenting the relevant line in `execution.py` (within the human_eval repository).
    This is not recommended unless you're running in a robust security sandbox.
    """
    main()
