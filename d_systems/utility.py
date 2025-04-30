import re
from langchain.schema import AIMessage
from AgenticFramework.AgenticSystem import Node
from dbConnector import chromadbConnector
from dotenv import load_dotenv
import os
load_dotenv()
from prompts import Prompts
prompt = Prompts()
class utility_functions():
    vectors = 0


    @staticmethod
    def extract_steps(output: str):
        step_pattern = r'\$(.*?)(?=\$)'  # Extract everything between pairs of $
        steps = re.findall(step_pattern, output, re.DOTALL)  # Capture multiline content
        response = [
            step.strip()
            for step in steps
            if step.strip() and len(step.strip()) > 10
        ]
        if not response:
            return [output]
        return response

    @staticmethod
    def get_step(outputs: list, step: int):
        """
        Retrieves a single step from the list of steps by index.
        """
        return outputs[step]

    @staticmethod
    def update_step(step: int):
        """
        Increments the provided step index by 1.
        """
        return step + 1

    @staticmethod
    def if_contains_error(answer, memory):
        node = Node(prompt.get_checking_if_ran_instructions(),'',False,False)
        response = node.generate(answer)
        if isinstance(response, AIMessage):
            response = response.content

        return "problem" in response.lower() or "error" in response.lower() or '0' in response.lower()

    @staticmethod
    def answer_ends_in_zero(answer, memory):
        """
        Checks if the node's output (answer) ends in '0'.
        """
        if isinstance(answer, AIMessage):
            answer = answer.content
        return answer.strip().endswith("0")

    @staticmethod
    def check_vector_length(answer, memory):
        """
        Determines if the system should continue retrieving more vectors.
        """
        current_number = memory.get("current_vector_number")
        return current_number < 5
    
    @staticmethod
    def vector_search(query: str):
        """
        Performs a vector search against a ChromaDB (or other DB) instance.
        Returns top-n results (set to 5 here).
        """
        db = chromadbConnector(path=os.environ("CHROMA_PATH"), collection=os.environ("COLLECTION"))
        results = db.perform_vector_search(query=query, n_results=3)
        docs = results.get("documents")[0][0:5]
        metadata = results.get('metadatas')[0][0:5]
        zipped = zip(docs, metadata)
        listed = list(zipped)
        print(f"\n\nDocuments: {docs}\nMetadata: {metadata}\nListed: {listed}\n")
        return listed

    @staticmethod
    def check_question_length(answer, memory):
        memory['generating_code_rephrase'] = ''
        current_num = memory.get("current_step_number")
        outputs = memory.get("parsed_outputs")

        return current_num < len(outputs)

    @staticmethod
    def add_code(all_code: list, code: str):
        all_code.append(code)
        return all_code

    @staticmethod
    def append_to_list(code: str, code_list: list):
        code_list.append(code)
        return code_list

    @staticmethod
    def check_questions(answer, memory):
        return memory["executions"] < 3

    @staticmethod
    def checking_generations(answer, memory):
        return answer < 3

    @staticmethod
    def checking_for_context(answer, memory):
        return re.search("MORE CONTEXT NEEDED", answer)

    @staticmethod
    def max_retries(answer, memory):
        return answer < 5

    @staticmethod
    def reset_vector(no):
        return 0

    @staticmethod
    def ret(name=''):
        return ''
