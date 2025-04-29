#!/usr/bin/env python3
# arc_system.py

import argparse
import json
import time

from lanlCodeGeneration import generate_code
from lanlTestingSuite import run_unit_tests_and_analysis
from lanlQBreakdown import breakdown_system_lanl
from codeGenerationSystemRolling import generate_code_roll
from questionBreakdownSystem import breakdown_system

def full_system(question: str,
                collection: str = "",
                model: str = "Meta-Llama-3.3-70B-Instruct",
                temp: float = 0.1):
    start_time = time.time()
    if collection == "":
        prompts = breakdown_system(question, model, temp)
        code = generate_code_roll(question, prompts, model= model)
    else:     
        prompts, files = breakdown_system_lanl(question, model, temp)
        code = generate_code(question, prompts,collection=collection,model= model)
    try:
        tested_code, regenerations = run_unit_tests_and_analysis(code, question, model, temp)
    except Exception as e:
        tested_code = str(e)
        regenerations = None
    elapsed_time = time.time() - start_time
    return code, tested_code, regenerations, elapsed_time

def main():
    parser = argparse.ArgumentParser(
        description="Run the LANL ARC full_system pipeline from the CLI."
    )
    parser.add_argument(
        "--prompt", "-p", required=True,
        help="The user’s prompt to feed into the full_system pipeline."
    )
    parser.add_argument(
        "--collection", "-c", default="",
        help="(Optional) collection name."
    )
    parser.add_argument(
        "--model", "-m", default="Meta-Llama-3.3-70B-Instruct",
        help="(Optional) model identifier (default: Meta-Llama-3.3-70B-Instruct)."
    )
    parser.add_argument(
        "--temp", "-t", type=float, default=0.1,
        help="(Optional) temperature for sampling (default: 0.1)."
    )

    args = parser.parse_args()

    code, tested_code, regenerations, elapsed = full_system(
        args.prompt,
        collection=args.collection,
        model=args.model,
        temp=args.temp
    )

    result = {
        "code": code,
        "tested_code": tested_code,
        "regenerations": regenerations,
        "elapsed_time": elapsed
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
