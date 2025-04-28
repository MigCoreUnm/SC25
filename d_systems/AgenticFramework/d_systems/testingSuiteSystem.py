from AgenticFramework.AgenticSystem import AgenticSystem
from dotenv import load_dotenv
from AgenticFramework.sambaNovaCode.myTools import run_py, run_tests,run_c,run_java

load_dotenv()
from agenticSystemPaper.prompts.TC_prompts import Prompts
from agenticSystemPaper.AgenticFramework.d_systems.utility import utility_functions

prompts = Prompts()
ut = utility_functions()

validation = prompts.validation_step
checking_step = prompts.get_test_checking_step()
fixing_node_instructions = prompts.get_fixing_prompt()
unit_testing_step = prompts.get_unit_testing_step()
create_ranking = prompts.get_create_ranking()
node2_test_execution_instructions = prompts.get_test_execution_instructions()

def run_unit_tests_and_analysis(code, purpose, model="Meta-Llama-3.1-70B-Instruct", temperature=0.1):
    system2 = AgenticSystem()

    # --- SETUP MEMORY ---
    system2.add_to_memory("refactor_count", 0)
    system2.add_to_memory("purpose_of_code", purpose)
    system2.add_to_memory("code", code)
    system2.add_to_memory("unit_testing_result")
    system2.add_to_memory("tests")
    system2.add_to_memory("ranking")
    system2.add_to_memory("execution_after", 0)

    # --- DEFINE NODES ---
    # Node: Generate Unit Tests
    system2.add_node(
        instructions=unit_testing_step,
        cot="",
        name="unit_test_generation_node",
        tool_caller=False,
        tools=None,
        inputNodes=[
            ("This is the original purpose of the code", "purpose_of_code"),
            ("This is the code: ", "code"),
            ("These are the different unit tests to generate", "generate_steps")
        ],
        outputs=["code"],
        is_end_node=False,
        onPrem=False,
        model=model,
        temperature=temperature
    )

    # Node: Execute Unit Tests
    system2.add_node(
        instructions=node2_test_execution_instructions,
        cot="",
        name="test_execution_node",
        tool_caller=True,
        tools=[run_py,run_c,run_java],
        inputNodes=["code"],
        outputs=["unit_testing_result"],
        is_end_node=False,
        onPrem=False,
        model=model,
        temperature=temperature
    )

    # Node: Update refactor count (function node)
    system2.add_function_node(
        "updater", ut.update_step, input_params=["refactor_count"], outputs=["refactor_count"]
    )

    # Node: Fix Code Based on Unit Test Results
    system2.add_node(
        instructions=fixing_node_instructions,
        cot="",
        name="fixing_node",
        inputNodes=[
            ("This is the code that needs to be changed:\n", "code"),
            ("This is the purpose of the code that it is trying to fulfill:\n", "purpose_of_code"),
            ("These are the parts that need to be refactored:\n", "problems")
        ],
        outputs=["code"],
        is_end_node=False,
        onPrem=False,
        model=model,
        temperature=temperature
    )

    # Node: Remove unit tests or main functions
    system2.add_node(
        instructions=prompts.get_remover(),
        cot="",
        name="remover",
        inputNodes=["code"],
        is_end_node=False,
        outputs=[
            ("This is the question that has been answered with the code", "purpose_of_code"),
            ("This code to remove any debugging or main function. Type of functionality", "code")
        ],
        model=model,
        temperature=temperature
    )

    # Node: Add main function to the code
    system2.add_node(
        instructions=prompts.get_add_main(),
        cot="",
        name="code_add_main",
        inputNodes=["code"],
        outputs=["code"],
        is_end_node=False,
        onPrem=False,
        model=model,
        temperature=temperature
    )

    # Node: Re-run tests on the modified code (Test Analysis)
    system2.add_node(
        instructions=node2_test_execution_instructions,
        cot="",
        name="test_analysis",
        tool_caller=True,
        tools=[run_tests],
        inputNodes=["code"],
        is_end_node=False,
        onPrem=False,
        model=model,
        temperature=temperature
    )

    # Node: Create ranking based on test results and analysis
    system2.add_node(
        instructions=create_ranking,
        cot="",
        name="ranking_node",
        tool_caller=False,
        tools=None,
        inputNodes=[
            ("This is the original purpose of the code:\n", "purpose_of_code"),
            ("This is the code that was given to analyze:", "code"),
            ("These are the unit testing results", "unit_testing_result"),
            ("This is static and dynamic analysis of code using different  modules:", "tests")
        ],
        outputs=["ranking"],
        is_end_node=False,
        onPrem=False,
        model=model,
        temperature=temperature
    )

    # Node: Final refactoring based on analysis ranking
    system2.add_node(
        instructions=checking_step,
        cot="",
        name="refactor",
        inputNodes=[
            ("\nThis is the purpose of the code when refactoring; make sure to adhere to this purpose:\n", "purpose_of_code"),
            ("\nThis is the code to refactor:\n", "code"),
            ("\nThis is the ranking and results of analyzing the code:\n", "ranking")
        ],
        outputs=["code"],
        model=model,
        temperature=temperature
    )

    system2.add_node(
        instructions="Your task is to take the given code and add a main function that runs it. Return the modified code with the main function integrated, and assure that no user input is required for the main function.",
        cot="",
        name="code_add_main_2",
        inputNodes=["code"],
        outputs=["code"],
        is_end_node=False,
        onPrem=False,
        model=model,
        temperature=temperature
    )

    system2.add_node(
        instructions="Your role is to run the code given",
        cot="",
        name="execute_refactor",
        tool_caller=True,
        tools=[run_py,run_c,run_java],
        inputNodes=["code"],
        model=model,
        temperature=temperature
    )

    system2.add_node(
        instructions=fixing_node_instructions,
        cot="",
        name="fixing_node2",
        inputNodes=[
            ("\nThis is the purpose of the code when refactoring; make sure to adhere to this purpose:\n", "purpose_of_code"),
            ("This is the code that needs to be changed:\n", "code"),
            ("These are the results of the execution of the code and errors that occurred:\n", "execute_refactor")
        ],
        outputs=["code"],
        is_end_node=False,
        onPrem=False,
        model=model,
        temperature=temperature
    )

    system2.add_function_node("updater2", ut.update_step, input_params=["execution_after"], outputs=["execution_after"])

    system2.add_node(
        instructions=prompts.get_remover(),
        cot="",
        name="remover2",
        inputNodes=[
            ("\nThis is the code\n", "code"),
            ("\nThis is the purpose of the code when refactoring; make sure to adhere to this purpose:\n", "purpose_of_code")
        ],
        outputs=["code"],
        is_end_node=False,
        model=model,
        temperature=temperature
    )

    system2.add_node(
        instructions=prompts.get_unit_testing_step(),
        cot="",
        name="generate_steps",
        inputNodes=[("\nThis is the code\n", "code")],
        model=model,
        temperature=temperature
    )

    system2.add_node(
        instructions=prompts.get_explaining_corrections_needed(),
        cot="",
        name="problems",
        inputNodes=[
            ("The prompt this code is attempting to solve", "purpose_of_code"),
            ("code to analyze", "code"),
            ("execution results", "test_execution_node")
        ],
        model=model,
        temperature=temperature
    )

    system2.add_node(
        instructions=validation,
        cot="",
        name="align",
        is_end_node=True,
        inputNodes=[
            ("\nThe code that was produced:\n", "code"),
            ("\nGenerate the translated code to solve the below mentioned problem (do not include any additional commentary):\n", "purpose_of_code")
        ],
        outputs=["code"],
        model=model,
        temperature=temperature
    )

    # --- ADDING EDGES ---
    # Edge: Add Main Function → Test Analysis
    system2.add_edge("code_add_main", "test_analysis")
    # Edge: Test Analysis → Ranking
    system2.add_edge("test_analysis", "ranking_node")
    # Edge: Ranking → Final Refactoring
    system2.add_edge("ranking_node", "refactor")
    system2.add_edge("refactor", "remover2")
    system2.add_edge("remover2", "generate_steps")
    system2.add_edge("generate_steps", "unit_test_generation_node")
    system2.add_edge("unit_test_generation_node", "test_execution_node")
    # Conditional Edge: Test Execution → Fixing Node (if errors detected)
    system2.add_conditional_edge(
        "test_execution_node", "problems", "remover", ut.if_contains_error, True
    )
    system2.add_edge("problems", "fixing_node", True)
    # Edge: Fixing Node → Updater (always true)
    system2.add_edge("fixing_node", "updater", True)
    # Conditional Edge: Updater → Test Execution (if max retries not reached)
    system2.add_conditional_edge(
        "updater", "test_execution_node", "remover", ut.max_retries, True
    )
    system2.add_edge("remover", "align")

    # --- DEFINE START ---
    system2.define_start("generate_steps")

    # Generate the answer using the system starting at the defined node
    answer = system2.generate_answer(code, starting=True)

    # Retrieve the final code from memory and return it
    code = system2.memory["code"]
    return code, system2.memory["refactor_count"]

# Example usage:
# purpose_text = "Implement a function to check if any two numbers in a list are closer than a given threshold."
# code_text = "def has_close_elements(numbers, threshold):\n    # implementation here\n    pass"
# print(run_unit_tests_and_analysis(code_text, purpose_text, model='Your-Model-Name', temperature=0.5))
