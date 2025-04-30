from AgenticFramework.AgenticSystem import AgenticSystem, Node
from dotenv import load_dotenv
from langchain.schema import AIMessage
from prompts.ARCprompts import Prompts
from AgenticFramework.d_systems.utility import utility_functions
import os 
from dbConnector import chromadbConnector

import re
load_dotenv()

prompts = Prompts()
classifier = prompts.get_classify_question()
breaking_into_steps = prompts.get_break_into_steps()
combine_steps = prompts.get_combine_steps()
utility = utility_functions()

checking_description = """
---YOUR ROLE--


---ROLE--- 
Your goal is to parse out the file path from the info that would be relavnt to the given question

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


Do not provide any additional commentary. Just return The function names and  
the aggregated file paths with a 1 after the entire thing. Make sure to follow the example. 

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



def breakdown_system_lanl(question, model="Meta-Llama-3.3-70B-Instruct", temperature=0.1,collection="pyDRESCALk"):
    system = AgenticSystem()
    system.add_to_memory("parsed_outputs")

        # VECTOR SEARCH
    system.add_function_node(
        name="vector_search",
        function=lambda step: vector_search(step, os.getenv("COLLECTION")),
        input_params=["question"],
        is_end_node=False
    )



    # JUDGING VECTOR SEARCH
    system.add_node(
        instructions=checking_description,
        cot="",
        name="judging_vector_search",
        inputNodes=["question", "vector_search"],
        model=model,
        temperature=temperature
    )
    

    def vector_search(query: str, collection_name: str):
        """
        Performs a vector search against a ChromaDB (or other DB) instance.
        Returns up to 25 results.
        """
        collection = os.getenv("COLLECTION")
        db_path =  os.getenv("CHROMA_PATH")
        db = chromadbConnector(path=db_path, collection=collection)
        results = db.perform_vector_search(query=query, n_results=2)

        # Extract top docs & metadata
        docs = results.get("documents")[0]  # entire top chunk
        metadata = results.get("metadatas")[0]
        # You can slice further if you want: [1:25] or so.

        return list(zip(docs, metadata))  # e.g. [ (doc, meta), (doc, meta), ... ]


    # -- Return Node: Returns instructions to retrieve file --
    system.add_function_node(
        'return',
        function=utility.ret,
        input_params=['question'],
        outputs=['retrieve_file']
    )
    system.add_function_node(
        "file", retrieve_file, [("","judging_vector_search")], outputs=["file"]
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
        inputNodes=[("lable", "classifier"), ("request", "question"), ("relevant context","file")],
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



    system.add_edge("classifier", "vector_search")
    system.add_edge("vector_search", "judging_vector_search")
    system.add_edge("judging_vector_search","file")
    system.add_edge("file","breaking_into_steps_node")
    system.add_edge("breaking_into_steps_node", "combine_steps")
    system.add_edge("combine_steps", "output_parsing")

    system.define_start("classifier")

    system.generate_answer(question, starting=True)

    result_prompts = system.memory["parsed_outputs"]
    print(result_prompts)
    return result_prompts, system.memory["file"]

# Example usage:
# prompt_text = "Explain how to implement binary search in Python."
# breakdown_system(prompt_text, model="Your-Model-Name", temperature=0.5)
