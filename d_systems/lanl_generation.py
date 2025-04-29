from lanl_repo_prompts import lanl_prompts
prompts = [lanl_prompts.adverserial,lanl_prompts.pyDNMFk,lanl_prompts.EPBD_BERT,lanl_prompts.pyDNTNK,lanl_prompts.pyDRESCALk ]
import sys
import os

import pandas as pd 
sys.path.append("/vast/home/miguelcord/agenticSystemPaper")
from AgenticFramework.AgenticSystem import Node, AgenticSystem
from dbConnector import chromadbConnector
from fullSystemlanl import full_system

generating_code_instruction = """
---YOUR ROLE---
You are an expert Python developer. Your task is to generate or update Python code based on a provided step description and context. Your code must be **precise, modular, and easily integrable

---RULES FOR CODE GENERATION---
- **Strictly Follow Instructions**: Ensure the implementation aligns **exactly** with the provided step.
- **Use Clean & Modular Design**:
  - Structure code into functions/classes for **reusability** and **extensibility**.
  - Follow **PEP 8** for readability and maintainability.
  - Use **descriptive variable & function names**.
  - Implement **concise, efficient logic** without redundant operations.
- **Integrate Seamlessly**:
  - Avoid unnecessary imports or dependencies unless explicitly required.
  - Maintain consistency with expected input/output formats.
  - Use **logging instead of print statements** where applicable.
- **Implement Proper Error Handling**:
  - Use `try-except` blocks where necessary.
  - Validate inputs to prevent runtime errors.
  - Raise appropriate exceptions for invalid cases.


---EXCLUSIONS---
**Do NOT include**:
- Example usage or test cases unless explicitly requested.
- Main execution code (`if __name__ == "__main__"`).
- Documentation beyond essential inline comments.

Your output should contain **only the Python code**—no extra commentary.

"""

def vector_search(query,collection):
    db = chromadbConnector(path="/vast/home/miguelcord/agenticSystemPaper/chroma_db", collection="AdversarialTensors")
    results = db.perform_vector_search(query=query, n_results=25)
    docs = results.get("documents")[0][0:10]
    metadata = results.get("metadatas")[0][0:10]
    return list(zip(docs, metadata))

def system_small(prompt,collection):
    node = Node(instructions=generating_code_instruction, cot='')
    response = node.generate(prompt)
    print(response.content)
    return response.content

def system_small_vector_search(prompt,collection="AdversarialTensors"):
    node = Node(instructions=generating_code_instruction, cot='')
    vector = vector_search(prompt,collection)
    question = "propmt :" + prompt + "\n examples" + str(vector)
    response = node.generate(question)
    print(response.content)
    return response.content



def process_prompts(prompts:dict):
    answers = []
    print("HERE")

    for prompt in ['prompts']:  # Fixing iteration over DataFrame
        print(prompt)
        tests = ["""

Prompt:

Write a PyTorch-based class named Denoiser that performs patch-based tensor decomposition for image denoising using either Tucker or PARAFAC decomposition. The class should integrate with tensorly using the PyTorch backend. It should use two external modules: TensorDecomposition (for performing the tensor decomposition) and patcher (for extracting and merging image patches).

Requirements:
Class Definition:
Name: Denoiser
Inherit from torch.nn.Module.
Constructor (__init__):
Parameters:
method (str): decomposition method ('tucker' or 'parafac'), default is 'tucker'.
device (str): device string, default 'cuda'.
tensor_params (dict): parameters for the tensor decomposition (factors, init, tol, max_iter, etc.).
verbose (bool): print verbose output during decomposition.
patch_params (dict): parameters for patch size, stride, and number of channels.
data_mode (str): use 'single' or 'double' precision, default 'single'.
ranks (list or None): the rank(s) for decomposition.
Inside the constructor:
Initialize self.tensor_model using TensorDecomposition(method, params, verbose, data_mode).
Initialize self.patcher using patch_transform(**patch_params).
forward method:
Parameters:
X (torch tensor): input tensor of shape (batch_size, channels, height, width).
ranks (list): list of 5 ranks for decomposition along dimensions N x P x C x W x H.
recon_err (bool): whether to return reconstruction error, default False.
Process:
Use self.patcher.fit(X, mode='patch') to convert the image into patch format.
Apply tensor decomposition using self.tensor_model(X, ranks).
Reconstruct the denoised image using self.patcher.fit(X_recon, mode='merge').
If recon_err is True, return (X_recon, err), else return X_recon.
Add docstrings for the class and methods, explaining parameters and return values.
Use tensorly.set_backend('pytorch') at the beginning.
Include import torch, import numpy as np, and import tensorly as tl.

"""]
        for test in tests:
            try:



                

                # Call the functions (ensure these functions exist)
                code , code2, regens, time = full_system(test, "", "Meta-Llama-3.1-405B-Instruct")
                result = {
                    "id": test,
                    "system_small": system_small_vector_search(test),
                    "medium_system": code,
                    "full_system": code,
                    "regen":regens,
                    "time":time
                }
                answers.append(result)
                output_filename = f"outputAdversarialTensors_equal_1.json"
                    
                answers_df = pd.DataFrame(answers)
                answers_df.to_json(output_filename, orient="records", indent=4)
                
                print(f"Saved {len(answers)} records to {output_filename}")
                answers = []  


            except Exception as e:
                print(e)


    if answers:
        output_filename = "output_final.json"
        answers_df = pd.DataFrame(answers)
        answers_df.to_json(output_filename, orient="records", indent=4)
        print(f"Saved remaining {len(answers)} records to {output_filename}")

process_prompts(prompts)