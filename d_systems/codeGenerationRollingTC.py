from AgenticFramework.AgenticSystem import AgenticSystem, Node
from dotenv import load_dotenv
from langchain.schema import AIMessage
from prompts.TC_prompts import Prompts

from AgenticFramework.d_systems.utility import utility_functions
load_dotenv()
prompts = Prompts()

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

def generate_code(question, prompts, model="Meta-Llama-3.1-70B-Instruct", temperature=0.1):
    system = AgenticSystem()

    # Create an initial Node (not used further but can be used for debugging)
    
    # =============================================================================
    # Memory Setup
    # =============================================================================
    system.add_to_memory("question", question)
    system.add_to_memory("parsed_outputs", prompts)
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
        inputNodes=[("\nprompts\n", "get_individual_step")],
        model=model,
        temperature=temperature
    )

    # -- Generate Code Node: Generates code based on previous steps and evaluation --
    system.add_node(
        instructions=generate_codes,
        cot="",
        name="generate_code",
        inputNodes=[
            ("The code that has been generated so far", "code"),
            ("Current step to complete:", "get_individual_step"),
            ("Steps to complete this task:", "function_steps")
        ],
        outputs=["code"],
        model=model,
        temperature=temperature
    )
    
    system.add_function_node(
        "update_regen",
        utility.update_step,
        input_params=['number_of_regens'],
        outputs=['number_of_regens']
    )

    # -- Evaluate Generated Code Node: Evaluates the generated code for modifications --
    system.add_node(
        instructions=evaluate_generated_code,
        cot="",
        name="evaluate_generated_code",
        inputNodes=[
            ("\nprompts\n", "get_individual_step"),
            ("\nGenerated Code:\n", "code")
        ],
        outputs=["generating_code_rephrase"],
        model=model,
        temperature=temperature
    )
    
    system.add_node(
        instructions=fixing_node_instructions,
        cot="",
        name="fix_based_off_evaluation",
        inputNodes=[
            ("\nCode to refactor:\n", "code"),
            ("Steps to change the code:", "generating_code_rephrase")
        ],
        outputs=["code"],
        model=model,
        temperature=temperature
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
        outputs=['code'],
        model=model,
        temperature=temperature
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
            ("\nThis is the main goal: assure the code written has the name of functionality of this goal. Task Description\n", "question")
        ],
        outputs=['final_code'],
        model=model,
        temperature=temperature
    )
    
    system.add_node(
        instructions=validation,
        cot='',
        name="align",
        is_end_node=True,
        inputNodes=[
            ("\nThe code that was produced:\n", "final_code"),
            ("\ngenerate code to solve mentioned problem (do not include any additional commentary):\n", "question")
        ],
        outputs=['final_code'],
        model=model,
        temperature=temperature
    )
    
    # =============================================================================
    # Edge & Conditional Connections
    # =============================================================================
    system.add_edge("get_individual_step", "function_steps", repeating=True)
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
        "update_step",
        "putting_everything_together",
        condition=utility.check_question_length,
        repeating=True
    )
    
    system.add_conditional_edge(
        "update_step",
        "get_individual_step",
        "putting_everything_together",
        condition=utility.check_question_length,
        repeating=True
    )
    
    system.add_edge("putting_everything_together", "align")
    system.add_edge("edge_cases", "implement")
    system.add_edge("implement", "align")
    system.add_edge("align", "combine")

    # =============================================================================
    # Define Start Node and Generate the Final Answer
    # =============================================================================
    system.define_start("get_individual_step")

    response = system.generate_answer(
        question,
        starting=True
    )
    return system.memory['final_code']

# Example usage:
# prompts_text = "Write a function to check if a list of numbers has any two numbers closer than a given threshold."
# test_prompts = ["1. Write a function named `has_close_elements` that accepts a list of floats and a threshold."]
# print(generate_code(prompts_text, test_prompts, model="Your-Model-Name", temperature=0.5))
