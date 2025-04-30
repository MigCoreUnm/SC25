from AgenticFramework.AgenticSystem import AgenticSystem, Node
from dotenv import load_dotenv
from langchain.schema import AIMessage
from prompts.TC_prompts import Prompts
from AgenticFramework.d_systems.utility import utility_functions
load_dotenv()

prompts = Prompts()
classifier = prompts.get_classify_question()
breaking_into_steps = prompts.get_break_into_steps()
combine_steps = prompts.get_combine_steps()
utility = utility_functions()

def breakdown_system(question, model="Meta-Llama-3.3-70B-Instruct", temperature=0.1):
    system = AgenticSystem()
    system.add_to_memory("parsed_outputs")
    
    # -- Return Node: Returns instructions to retrieve file --
    system.add_function_node(
        'return',
        function=utility.ret,
        input_params=['question'],
        outputs=['retrieve_file']
    )

    # -- Combine Steps Node: Combines steps into a single output --
    system.add_node(
        combine_steps,
        "",
        "combine_steps",
        inputNodes=[
            ('Original question\n', 'question'),
            ('These are the steps that possibly need combination\n', 'breaking_into_steps_node')
        ],
        model=model,
        temperature=temperature
    )

    # -- End Node: Terminal node --
    system.add_function_node(
        "end_node",
        function=lambda y: None,
        is_end_node=True
    )

    # -- Breaking into Steps Node: Splits the question into multiple steps --
    system.add_node(
        instructions=breaking_into_steps,
        cot="",
        name="breaking_into_steps_node",
        tool_caller=False,
        tools=None,
        inputNodes=[("lable", "classifier"), ("request", "question")],
        is_end_node=False,
        onPrem=False,
        outputs=None,
        model=model,
        temperature=temperature
    )

    system.add_function_node(
        "output_parsing",
        utility.extract_steps,
        ["combine_steps"],
        is_end_node=True,
        outputs=["parsed_outputs"]
    )

    # -- Classifier Node: Classifies the question --
    system.add_node(
        classifier,
        "",
        'classifier',
        inputNodes=[("\nprompt:\n", 'question')],
        model=model,
        temperature=temperature
    )

    system.add_edge("classifier", "breaking_into_steps_node")
    system.add_edge("breaking_into_steps_node", "combine_steps")
    system.add_edge("combine_steps", "output_parsing")

    system.define_start("classifier")

    system.generate_answer(question, starting=True)

    result_prompts = system.memory["parsed_outputs"]
    print(result_prompts)
    return result_prompts

# Example usage:
# prompt_text = "Explain how to implement binary search in Python."
# breakdown_system(prompt_text, model="Your-Model-Name", temperature=0.5)
