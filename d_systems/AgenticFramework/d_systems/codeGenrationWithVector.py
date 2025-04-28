from AgenticFramework.AgenticSystem import AgenticSystem, Node

from dotenv import load_dotenv
from langchain.schema import AIMessage
from prompts import Prompts
import prompts2 
from dbConnector import chromadbConnector

from agenticSystemPaper.AgenticFramework.d_systems.utility import utility_functions
load_dotenv()
prompt = prompts2.Prompts()
prompts = Prompts()
combine = prompts.combine
implment_edge = prompts.get_implementing()
validation = prompts.get_validation()
generate_codes = prompts.get_code_generation_prompt()
evaluate_generated_code = prompts.get_evaluate_generated_code()
execution_node_instructions = prompts.get_execution_node_instructions()
checking_if_ran_instructions = prompts.get_checking_if_ran_instructions()
fixing_node_instructions = prompts.get_fixing_prompt()
putting_everything_together_instructions = prompt.get_putting_everything_together_instructions()
checking_step = prompts.get_checking_step()
combine_steps = prompts.get_combine_steps()
generate_function_steps = prompt.get_plan_out_code_generation()
edge_cases = prompts.get_edge()
vector_summary = prompts.vector_summary
utility = utility_functions()
def generate_code(question, prompts, collection):
    system = AgenticSystem()

    node = Node("Generate python code to solve the below mentioned problem(don not include any additional commentary):","")

    # =============================================================================
    # Memory Setup
    # =============================================================================
    system.add_to_memory("question", question)
    system.add_to_memory("parsed_outputs",prompts)
    system.add_to_memory("current_step_number", 0)
    system.add_to_memory("current_vector_number", 0)
    system.add_to_memory("number_of_regens", 0)
    system.add_to_memory("generating_code_rephrase")
    system.add_to_memory("code")
    system.add_to_memory("stored_code", [])
    system.add_to_memory("final_code")
    # =============================================================================
    # Node Definitions
    # =============================================================================


    # -- Return Node: Returns instructions to retrieve file --
    system.add_function_node(
        'return',
        function=utility.ret,
        input_params=['question'],
        outputs=['retrieve_file']
    )

    # -- End Node: Terminal node --
    system.add_function_node(
        "end_node",
        function=lambda y: None,
        is_end_node=True
    )
    system.add_function_node("vector", utility.vector_search,["get_individual_step"])


    # -- Get Individual Step Node: Retrieves one step at a time --
    system.add_function_node(
        "get_individual_step",
        utility.get_step,
        input_params=["parsed_outputs", "current_step_number"],
        is_end_node=False
    )


    # -------------------- Code Evaluation & Generation -------------------------
    system.add_node(
        instructions=generate_function_steps,
        cot="",
        name="function_steps",
        inputNodes=[
            ("\nPrompt\n", "get_individual_step"), ("\nThis is the sumary of the vector search results:\n", "vector_summary")
        ],
    )

    system.add_node(
        instructions=vector_summary,
        cot='',
        name="vector_summary",
        inputNodes=[("\nThis is the relevant documents to the question:\n ","vector"),("\nthis is the question needs to get answered:\n","get_individual_step")]
    )


    # -- Generate Code Node: Generates code based on previous steps and evaluation --
    system.add_node(
        instructions=generate_codes,
        cot="",
        name="generate_code",
        inputNodes=[
            ("The code that has been generated so far", "code"),
            ("Current step to complete:", "get_individual_step"),
            ("Steps to complete this task:","function_steps"),
        ],
        outputs=["code"]
    )
    system.add_function_node("update_regen", utility.update_step, input_params=['number_of_regens'], outputs=['number_of_regens'])

    # -- Evaluate Generated Code Node: Evaluates the generated code for modifications --
    system.add_node(
        instructions=evaluate_generated_code,
        cot="",
        name="evaluate_generated_code",
        inputNodes=[
            ("\nPrompt\n", "get_individual_step"),
            ("\nGenerated Code:\n", "code")
        ],
        outputs=["generating_code_rephrase"]
    )
    system.add_node(
        instructions=fixing_node_instructions,
        cot="",
        name="fix_based_off_evaluation",
        inputNodes=[
            ("\nCode to refactor:\n", "code"),
            ("Steps to change the code:","generating_code_rephrase")
        ],
        outputs=["code"]
    )



    # -- Extract Code Node: Extracts the code without any additional commentary --
    extract_code = """
    Your role is to simply extract the code and return it.
    Do not give any extra commentary.
    """

    system.add_node(
        instructions=extract_code,
        cot='',
        name='storing_code',
        inputNodes=['code'],
        outputs=['code']
    )

    # -- Update Step Node: Updates the current step index --
    system.add_function_node(
        "update_step",
        utility.update_step,
        input_params=["current_step_number"],
        outputs=["current_step_number"]
    )

    # -- Putting Everything Together Node: Combines generated code for final output --
    system.add_node(
        instructions=putting_everything_together_instructions,
        cot='',
        name="putting_everything_together",
        inputNodes=[
            ("\nThis is the code that was generated and will help assist you in writing code for the task description:\n", "code"),
            ('\n.this is the main goal assure the code written has the name of funcionality of this goal. Task Description\n', 'question'),
        ],
        outputs=['final_code']

    )
    system.add_node(
        instructions=validation,
        cot='',
        name="align",
        is_end_node=True,
        inputNodes=[
            ("\nThe code that was produced:\n", "final_code"),
            ('\nGenerate python code to solve the below mentioned problem(do not include any additional commentary):\n', 'question')
        ],
        outputs=['final_code'],
    )


    
    # =============================================================================
    # Edge & Conditional Connections
    # =============================================================================


    system.add_edge("get_individual_step", "vector", repeating=True)
    system.add_edge("vector", "vector_summary", repeating=True)
    system.add_edge("vector_summary", "function_steps", repeating=True)


    system.add_edge("function_steps", "generate_code", repeating=True)

    system.add_edge("generate_code", "evaluate_generated_code", repeating=True)

    # --- Undefined Condition: answer_ends_in_zero ---
    system.add_conditional_edge("evaluate_generated_code", "update_regen", "storing_code", condition=utility.answer_ends_in_zero, repeating=True)
    system.add_conditional_edge("update_regen", "fix_based_off_evaluation", "storing_code", utility.checking_generations, True)
    system.add_edge("fix_based_off_evaluation","evaluate_generated_code",True)

    # --- Undefined Condition: check_question_length ---
    system.add_conditional_edge("storing_code", "update_step", "putting_everything_together", condition=utility.check_question_length, repeating=True)
    system.add_conditional_edge("update_step", "get_individual_step", "putting_everything_together", condition=utility.check_question_length, repeating=True)
    system.add_edge("putting_everything_together", "align")




    # =============================================================================
    # Define Start Node and Generate the Final Answer
    # =============================================================================
    system.define_start("get_individual_step")

    response = system.generate_answer(
        question,
        starting=True
    )
    return system.memory['final_code']

# prompt ="""
# from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    \"\"\" Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    \"\"\"\n", "entry_point": "has_close_elements"
# = """
# testing = ["""'1. Write a function named `has_close_elements` that:\n- Accepts a list of floating-point numbers and a threshold value.\n- Returns a boolean indicating whether any two numbers in the list are closer than the given threshold.""" ]
# print(generate_code(prompt,testing))