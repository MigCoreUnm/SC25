#!/usr/bin/env python3
# arc_system.py
import os
import argparse
import json
import time
from dotenv import load_dotenv
from lanlCodeGeneration import generate_code
from lanlTestingSuite import run_unit_tests_and_analysis
from lanlQBreakdown import breakdown_system_lanl
from codeGenerationSystemRolling import generate_code_roll
from questionBreakdownSystem import breakdown_system
from AgenticFramework.AgenticSystem import Node
from utility import utility_functions
from prompts.ARCprompts import Prompts

prompts = Prompts()
ut = utility_functions()
load_dotenv()

def full_system(question: str,
                collection: str = "",
                model: str = "Meta-Llama-3.3-70B-Instruct",
                temp: float = 0.1):
    start_time = time.time()
    if collection:
        prompts_bundle, files = breakdown_system_lanl(question, model, temp)
        code = generate_code(question, prompts_bundle, collection=collection, model=model)
    else:
        prompts_bundle = breakdown_system(question, model, temp)
        code = generate_code_roll(question, prompts_bundle, model=model)
    try:
        tested_code, regenerations = run_unit_tests_and_analysis(code, question, model, temp)
    except Exception as e:
        tested_code = str(e)
        regenerations = None
    elapsed_time = time.time() - start_time
    return code, tested_code, regenerations, elapsed_time


def medium_system(question: str,
                  collection: str = "",
                  model: str = "Meta-Llama-3.3-70B-Instruct",
                  temp: float = 0.1):
    if collection:
        prompts_bundle, files = breakdown_system_lanl(question, model, temp)
        code = generate_code(question, prompts_bundle, collection=collection, model=model)
    else:
        prompts_bundle = breakdown_system(question, model, temp)
        code = generate_code_roll(question, prompts_bundle, model=model)
    return code


def system_small_vector_search(prompt: str,
                               collection: str = "") -> str:
    node = Node(instructions=prompts.generating_code_prompt, cot='')
    vector = ut.vector_search(prompt, collection) if collection else []
    question = f"prompt: {prompt}\nexamples: {vector}"
    response = node.generate(question)
    return response.content


def main():
    parser = argparse.ArgumentParser(
        description="Run the ARC pipeline from the CLI."
    )
    parser.add_argument(
        "--prompt", "-p", required=True,
        help="The user’s prompt to feed into the pipeline."
    )
    parser.add_argument(
        "--collection", "-c", default="",
        help="(Optional) collection name."
    )
    parser.add_argument(
        "--model", "-m", default="Meta-Llama-3.3-70B-Instruct",
        help="(Optional) model identifier."
    )
    parser.add_argument(
        "--temp", "-t", type=float, default=0.1,
        help="(Optional) temperature for sampling."
    )
    parser.add_argument(
        "--system", "-s", choices=["full", "medium", "small"], default="full",
        help="Which system to run: full, medium, or small."
    )

    args = parser.parse_args()
    sys_type = args.system

    if sys_type == "full":
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
    elif sys_type == "medium":
        code = medium_system(
            args.prompt,
            collection=args.collection,
            model=args.model,
            temp=args.temp
        )
        result = {"code": code}
    else:  # small
        response = system_small_vector_search(
            args.prompt,
            collection=args.collection
        )
        result = {"response": response}

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
