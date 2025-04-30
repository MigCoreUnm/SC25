import os
import re
from AgenticFramework.AgenticSystem import AgenticSystem, Node
from dotenv import load_dotenv
from langchain.schema import AIMessage

# Your custom modules
from prompts.ARCprompts import Prompts
from dbConnector import chromadbConnector
from AgenticFramework.d_systems.utility import utility_functions

load_dotenv()
extract_code = """
    Your role is to simply extract the code and return it.
    Do not give any extra commentary.
    """
# --------------------------------------------------------------------------------
# 1) PROMPTS & UTILITY
# --------------------------------------------------------------------------------
prompts = Prompts()

checking_description = """
---YOUR ROLE--
Assess the retrieved vector search results to determine whether the provided code (based on its description) 
is useful for building the current step in the pipeline.

TASKS
Analyze the retrieved vector data and its description to determine if the code can contribute to building 
the expected code. If the retrieved code is relevant, functional, or applicable for the pipeline step, then 
gather all relevant file paths from the code, separate them by $, and append a "1" after each file path. 
Return this aggregated result. If the retrieved code does not align with the required functionality or cannot 
be used effectively for this step, return "0".

---ROLE--- 
Your goal is to assess retrieved vector search results to determine whether the provided code can be used 
for the current step. Deconstruct the prompt into clear, actionable steps that a developer can follow. 
If the question is not specific enough, respond with "0" or the aggregated file paths with 1's.

---EXAMPLE---
Input: 
Retrieved code snippet description indicates that the code performs user authentication,

Process:
$ Examine the retrieved code’s description and functionality, checking if it aligns with the step’s purpose.
$ Confirm that the code is applicable and relevant for user authentication.
$ Gather the relevant file paths, separate each with a $, and append a "1" after each file path.
$ Assure each file path has this attached to it /projects/asc_llm/Manish_Datagen/lanl_repos This is required

Output:
{path to file}
"1"

If the code is not applicable, return:
"0"

Do not provide any additional commentary. Just return 0 or The function names and  
the aggregated file paths with a 1 after the entire thing. Make sure to follow the example. 
NOTE: REMEMBER THIS CODE IS A PART OF A SYSTEM FOR GENERATING CODE AND SOME NEEDED 
FUNCTIONALITY MIGHT BE IN OTHER STEPS.
"""
def parse_file_paths(response: str) -> list:
    """
    Parse the aggregated response string to extract file paths.
    
    The response is expected to be in the format:
    "/path/to/file1.py1$/path/to/file2.py1"
    
    If the response is "0", return an empty list.
    """
    if response.strip() == "0":
        return []
    
    # Split the response by the '$' delimiter
    parts = response.split('$')
    file_paths = []
    
    # Iterate through each part and remove the trailing "1" if present
    for part in parts:
        part = part.strip()
        if part.endswith("1"):
            file_paths.append(part[:-1])
        elif part:
            file_paths.append(part)
            
    return file_paths
def retrieve_file(file_info: str):
    """
    Placeholder function to simulate file retrieval from a path or location.
    """
    print(file_info)
    r_code = []
    file_info = parse_file_paths(file_info)
    for i in file_info:
            file_path = i
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as file:
                        code = file.read()
                        r_code.append(code)
                except Exception as e:
                    print(f"An error occurred while reading {file_path}: {e}")
            else:
                print(f"Error: The file at {file_path} was not found.")

    return str(r_code)

validation = prompts.get_validation()
generate_codes = prompts.generating_code_prompt
evaluate_generated_code = prompts.get_evaluate_generated_code()
execution_node_instructions = prompts.get_execution_node_instructions()
checking_if_ran_instructions = prompts.get_checking_if_ran_instructions()
fixing_node_instructions = prompts.fixing_prompt
putting_everything_together_instructions = prompts.get_putting_everything_together_instructions()
checking_step = prompts.get_checking_step()
combine_steps = prompts.get_combine_steps()
generate_function_steps = prompts.get_plan_out_code_generation()

utility = utility_functions()


# --------------------------------------------------------------------------------
# 2) VECTOR-SEARCH HELPER FUNCTIONS
# --------------------------------------------------------------------------------
def vector_search(query: str, collection_name: str):
    """
    Performs a vector search against a ChromaDB (or other DB) instance.
    Returns up to 25 results.
    """
    db_path =  os.getenv("CHROMA_PATH")
    collection_name = os.getenv("COLLECTION")
    db = chromadbConnector(path=db_path, collection=collection_name)
    results = db.perform_vector_search(query=query, n_results=10)

    # Extract top docs & metadata
    docs = results.get("documents")[0]  # entire top chunk
    metadata = results.get("metadatas")[0]
    # You can slice further if you want: [1:25] or so.

    return list(zip(docs, metadata))  # e.g. [ (doc, meta), (doc, meta), ... ]

def get_n_vector_searches(outputs: list, chunk_index: int):
    """
    Return up to 3 items from the list of vector search results at a time.
    For example, outputs[(chunk_index*3): (chunk_index*3 + 3)].
    """
    return outputs[(chunk_index):(chunk_index+1)]

def update_step(step_val: int):
    """
    Increments the provided step index by 1.
    """
    return step_val + 1

def reset_vector(_):
    """
    Reset vector index to 0 after finishing a step.
    """
    return 0

def answer_ends_in_zero(answer, memory):
    """
    True if the node's output ends in '0'.
    This typically signals "not relevant" or "needs fix".
    """
    if isinstance(answer, AIMessage):
        answer = answer.content
    return answer.strip().endswith("0")

def check_vector_length(answer, memory):
    """
    Decide if we should keep retrieving more vector chunks or not.
    Example logic: repeat up to 5 times.
    """
    cur_num = memory.get("current_vector_number", 0)
    return cur_num < 10  # or any other logic you prefer

def check_question_length(answer, memory):
    """
    Checks if more steps remain by comparing 'current_step_number' with
    the total number of 'parsed_outputs'.
    """
    current_num = memory.get("current_step_number", 0)
    outputs = memory.get("parsed_outputs", [])
    return current_num < len(outputs)

# --------------------------------------------------------------------------------
# 3) MAIN generate_code FUNCTION (ROLLING CODE + VECTOR SEARCH)
# --------------------------------------------------------------------------------
def generate_code(question, step_prompts, collection="pyDRESCALk", model="Meta-Llama-3.3-70B-Instruct", temperature=0.1,files=""):
    """
    Merges rolling code generation with multi-chunk vector search & relevancy checks.
    We store code in a single 'code' memory key that is continuously updated.
    """
    system = AgenticSystem()

    # -------------------------------------------------------------------------
    # 3a) Memory Setup
    # -------------------------------------------------------------------------
    system.add_to_memory("question", question)
    system.add_to_memory("parsed_outputs", step_prompts)     # Steps or instructions
    system.add_to_memory("current_step_number", 0)
    system.add_to_memory("current_vector_number", 0)
    system.add_to_memory("number_of_regens", 0)
    system.add_to_memory("original_file", files)
    system.add_to_memory("code", "")            # Rolling code
    system.add_to_memory("final_code", "")      # Final output code
    system.add_to_memory("generating_code_rephrase", "")  # fix instructions
    system

    # -------------------------------------------------------------------------
    # 3b) DEFINE NODES
    # -------------------------------------------------------------------------

    # STEP RETRIEVAL
    system.add_function_node(
        name="get_individual_step",
        function=utility.get_step,
        input_params=["parsed_outputs", "current_step_number"],
        is_end_node=False
    )

    # VECTOR SEARCH
    system.add_function_node(
        name="vector_search",
        function=lambda step: vector_search(step, collection),
        input_params=["get_individual_step"],
        is_end_node=False
    )

    # GET INDIVIDUAL VECTOR (3 at a time)
    system.add_function_node(
        name="get_individual_vector",
        function=get_n_vector_searches,
        input_params=["vector_search", "current_vector_number"],
        is_end_node=False
    )

    # JUDGING VECTOR SEARCH
    system.add_node(
        instructions=checking_description,
        cot="",
        name="judging_vector_search",
        inputNodes=["get_individual_step", "get_individual_vector"],
        model=model,
        temperature=temperature
    )

    # UPDATE VECTOR
    system.add_function_node(
        name="update_vector",
        function=update_step,
        input_params=["current_vector_number"],
        outputs=["current_vector_number"]
    )

    # RESET VECTOR
    system.add_function_node(
        name="reset_vector",
        function=reset_vector,
        input_params=["current_vector_number"],
        outputs=["current_vector_number"]
    )

    # VECTOR SUMMARY: Summarize relevant doc pieces
    system.add_node(
        name="vector_summary",
        instructions=prompts.vector_summary,  # or your own summary instructions
        cot="",
        inputNodes=[
            ("\nThis is the relevant documents to the question:\n", "file"),
            ("\nCurrent step prompt:\n", "get_individual_step")
        ],
        model=model,
        temperature=temperature
    )

    # FUNCTION STEPS: Plan the sub-steps for code generation
    system.add_node(
        name="function_steps",
        instructions=generate_function_steps,
        cot="",
        inputNodes=[
            ("\nPrompt\n", "get_individual_step"),
            ("\nVector search summary:\n", "vector_summary")
        ],
        model=model,
        temperature=temperature
    )

    # GENERATE CODE: updates 'code' in a rolling fashion
    system.add_node(
        name="generate_code",
        instructions=generate_codes,
        cot="",
        inputNodes=[
            ("The code that has been generated so far", "code"),
            ("Current step to complete:", "get_individual_step"),
            ("Steps to complete this task:", "function_steps"),
            ("\nimplemenation to follow","vector_summary")
        ],
        outputs=["code"],
        model=model,
        temperature=temperature
    )

    # EVALUATE GENERATED CODE
    system.add_node(
        name="evaluate_generated_code",
        instructions=evaluate_generated_code,
        cot="",
        inputNodes=[
            ("\nCurrent step prompt\n", "get_individual_step"),
            ("\nGenerated Code:\n", "code")
        ],
        outputs=["generating_code_rephrase"],
        model=model,
        temperature=temperature
    )

    # UPDATE REGEN COUNT
    system.add_function_node(
        name="update_regen",
        function=utility.update_step,
        input_params=["number_of_regens"],
        outputs=["number_of_regens"]
    )

    # FIX CODE IF NEEDED
    system.add_node(
        name="fix_based_off_evaluation",
        instructions=fixing_node_instructions,
        cot="",
        inputNodes=[
            ("\nCode to refactor:\n", "code"),
            ("Steps to change the code:", "generating_code_rephrase")
        ],
        outputs=["code"],
        model=model,
        temperature=temperature
    )

    # UPDATE STEP
    system.add_function_node(
        name="update_step",
        function=update_step,
        input_params=["current_step_number"],
        outputs=["current_step_number"]
    )

    # PUTTING EVERYTHING TOGETHER: Merge final code
    system.add_node(
        name="putting_everything_together",
        instructions="Your role is to extract the code without additional commentary and remove any comments from inside the code",
        cot="",
        is_end_node=True,
        inputNodes=[
            ("\nThis is the code that was generated", "code"),
        ],
        outputs=["final_code"],
        model=model,
        temperature=temperature
    )

    # VALIDATION (END NODE)
    system.add_node(
        name="align",
        instructions=validation,
        cot="",
        is_end_node=True,
        inputNodes=[
            ("\nThe code that was produced try to implement saas much of this as possible.:\n", "code"),
            ("This is the code context adhere to this as strictly as posible", "original_file"),
            ("\ngenerate code to solve mentioned problem return only the code and remove any extra comments inside the code:\n", "question")
        ],
        outputs=["final_code"],
        model=model,
        temperature=temperature
    )
    system.add_node(
        instructions=extract_code,
        cot='',
        name='storing_code',
        inputNodes=['code'],
        outputs=['code'],
        model=model,
        temperature=temperature
    )
    system.add_function_node(
        "file", retrieve_file, [("","judging_vector_search")], outputs=["file"]
    )

    # -------------------------------------------------------------------------
    # 3c) EDGES & FLOW
    # -------------------------------------------------------------------------
    # STEP & VECTOR
    system.add_edge("get_individual_step", "vector_search", repeating=True)
    system.add_edge("vector_search", "get_individual_vector", repeating=True)
    system.add_edge("get_individual_vector", "judging_vector_search", repeating=True)
    

    # If 'judging_vector_search' ends with 0 => update_vector => try next chunk
    system.add_conditional_edge(
        "judging_vector_search",
        "update_vector",
        "file",
        condition=answer_ends_in_zero,
        repeating=True
    )

    # If we still have more vectors, keep retrieving them. Otherwise proceed to summary
    system.add_conditional_edge(
        "update_vector",
        "get_individual_vector",
        "vector_summary",
        condition=check_vector_length,
        repeating=True
    )
    system.add_edge("file","vector_summary", repeating=True)

    # Summarize vectors, then plan code steps
    system.add_edge("vector_summary", "function_steps", repeating=True)
    system.add_edge("function_steps", "generate_code", repeating=True)
    system.add_edge("generate_code", "evaluate_generated_code", repeating=True)

    
    # --- Undefined Condition: answer_ends_in_zero ---
    system.add_conditional_edge(
        "evaluate_generated_code",
        "update_regen",
        "storing_code",
        condition=utility.answer_ends_in_zero,
        repeating=True
    )
    
    system.add_conditional_edge(
        "update_regen",
        "fix_based_off_evaluation",
        "storing_code",
        condition=utility.checking_generations,
        repeating=True
    )
    
    system.add_edge("fix_based_off_evaluation", "evaluate_generated_code", repeating=True)
    
    
    # --- Undefined Condition: check_question_length ---
    system.add_conditional_edge(
        "storing_code",
        "reset_vector",
        "align",
        condition=utility.check_question_length,
        repeating=True
    )
    system.add_edge("reset_vector", "update_step",repeating=True)

    
    system.add_conditional_edge(
        "update_step",
        "get_individual_step",
        "align",
        condition=utility.check_question_length,
        repeating=True
    )
    

    # -------------------------------------------------------------------------
    # 3d) START & RUN
    # -------------------------------------------------------------------------
    system.define_start("get_individual_step")
    system.generate_answer(question, starting=True)

    return system.memory["final_code"]
