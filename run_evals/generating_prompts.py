import sys
import os
import pandas as pd
import time

# Ensure proper module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from SC25code.full_systemHE import full_system
from prompts2 import Prompts
from AgenticFramework.AgenticSystem import Node

# Initialize prompt system
prom = Prompts()

def system_small(prompt):
    """Generate response using a small system."""
    node = Node(instructions="Generate python code to solve the below mentioned problem(don not include any additional commentary):", cot='')
    response = node.generate(prompt)
    return response.content

def process_data(input_file, checkpoint_prefix="results_checkpoint_final_70b1", final_output="results_70b1.jsonl", max_retries=20, retry_delay=1):
    """
    Process dataset and integrate full system call with retries and checkpointing.

    :param input_file: Path to the input JSONL file.
    :param checkpoint_prefix: Prefix for checkpoint files.
    :param final_output: Final output file name.
    :param max_retries: Max number of retries for API calls.
    :param retry_delay: Initial retry delay in seconds.
    """
    df = pd.read_json(input_file, lines=True)
    records = []

    for index, row in df.iterrows():
        attempt = 0
        while attempt < max_retries:
            try:
                # Generate responses
                medium, full = full_system(row["prompt"])
                small = system_small(row["prompt"])
                
                # Store results
                record = {
                    "small_system": small,
                    "medium_system": medium,
                    "large_system": full,
                    "tests": row["test"],
                    "id": row["task_id"]
                }
                records.append(record)
                break  # Break loop on success
            
            except Exception as e:
                if "rate limit" in str(e).lower():
                    sleep_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Rate limit hit. Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    attempt += 1
                elif "timeout" in str(e).lower():
                    print(f"Request timed out. Skipping task ID {row['task_id']}")
                    break
                else:
                    print(f"Unexpected error: {e}. Skipping task ID {row['task_id']}")
                    break
        
        # Save checkpoint every 10 iterations
        if (index + 1) % 10 == 0:
            temp_df = pd.DataFrame(records)
            checkpoint_file = f"{checkpoint_prefix}_{index+1}.jsonl"
            temp_df.to_json(checkpoint_file, orient="records", lines=True)
            print(f"Checkpoint saved at index {index + 1}")

    # Save final results
    final_df = pd.DataFrame(records)
    final_df.to_json(final_output, orient="records", lines=True)
    print("Final results saved.")

# Run processing
process_data("Evaluation/humanEval.jsonl")
