import time
import os
from dotenv import load_dotenv
import textwrap  
import datetime
from AgenticFramework.OnPremLLM.myLLM import LLM
from AgenticFramework.OnPremLLM.toolCallingClass import toolCallingLLM

from langchain_community.chat_models.sambanova import ChatSambaNovaCloud
from AgenticFramework.sambaNovaCode.function_calling.src.function_calling import FunctionCallingLlm
from langchain.schema import AIMessage

load_dotenv()
key = os.getenv("SAMBANOVA_API_KEY2")

###############################################################################
# Node classes
###############################################################################
class Node:
    """
    Represents a node in the agentic system graph.

    Each node encapsulates:
    - A language model (LLM) configuration.
    - A set of instructions that guide its response.
    - Optional tool integration logic for function calling.
    - An optional list of input node dependencies.
    - An optional flag to designate the node as an end node.
    
    Now supports dynamic model and temperature parameters.
    """

    def __init__(
        self,
        instructions,
        cot,
        is_end_node=False,
        onPrem=False,
        outputs=[],
        path="/lustre/vescratch1/miguelcord/llms/llama321b/checkpoints",
        model="Meta-Llama-3.1-70B-Instruct",
        temperature=0.1
    ):
        """
        Initialize a Node object.
        
        :param instructions: The prompt/instructions for the LLM.
        :param cot: Chain-of-Thought examples (if any).
        :param is_end_node: Flag indicating if this is an end node.
        :param onPrem: Boolean flag to decide if using on-prem model.
        :param outputs: List of keys to store node outputs in memory.
        :param path: Path for on-prem models.
        :param model: Model name to use (for both on-prem and SambaNova Cloud).
        :param temperature: Temperature parameter for model generation.
        """
        self.onPrem = onPrem
        self.sambaNovaTool = False
        self.functionCaller = False

        # Store dynamic model and temperature parameters
        self.model = model
        self.temperature = temperature
        
        self.llm = self.initilize_model(onPrem, path)
        self.instruct = self.initilize_behavior(instructions, cot)
        self.tools = None
        self.inputs = []
        self.outputs = outputs
        self.is_end_node = is_end_node

    def initilize_model(self, onPrem, path):
        """
        Initialize the LLM model for this node, either on-prem or SambaNova Cloud,
        using the dynamic model and temperature parameters.
        """
        if onPrem:
            # If your on-prem LLM supports dynamic parameters, pass them here:
            return LLM(path, model=self.model, temperature=self.temperature)
        else:
            # SambaNova approach
            return ChatSambaNovaCloud(
                api_key=key,
                model=self.model,
                max_tokens=4096,
                temperature=self.temperature,
                top_k=1,
                top_p=0.01,
            )

    def initilize_behavior(self, instruction, cot):
        """
        Prepare the node's instruction prompt.
        """
        instruction = instruction
        # Optionally, integrate Chain-of-Thought (COT) here:
        # instruction += f"\nThese are examples of your output: {cot}"
        return instruction

    def set_input_nodes(self, input_nodes):
        """
        Set the input node dependencies.
        """
        if isinstance(input_nodes, list):
            self.inputs = input_nodes
        else:
            self.inputs = [input_nodes]

    def toolCalling(self, tools):
        """
        Integrate tool logic. For on-prem, we attach tools using 'toolCallingLLM()'.
        For SambaNova, we integrate function-calling LLM logic.
        """
        if self.onPrem:
            self.llm = toolCallingLLM()
            self.llm = self.llm.attach_tools(tools)
            self.functionCaller = True
        else:
            self.llm = FunctionCallingLlm(tools)
            print(tools)
            self.tools = {tool.name: tool for tool in tools}
            self.sambaNovaTool = True

    def generate(self, questions):
        """
        Generate a response using the node’s LLM configuration.
        """
        final_instruction = self.instruct + f"{questions}"
        # Introduce a short delay

        if self.sambaNovaTool:
            try:
                # SambaNova function-calling approach
                response = self.llm.function_call_llm(questions)
                print("SambaNova function-call response:", response)
                return response
            except Exception as e:
                return "problem with generating tests"
        

        elif self.functionCaller:
            # On-prem with tool calling
            response = self.llm.generate(final_instruction)
            print(f"Tool outputs (on-prem): {response}")
            return response

        else:
            # Basic LLM invocation
            if self.onPrem:
                response = self.llm.generate(final_instruction)
            else:
                response = self.llm.invoke(final_instruction)
            return response


###############################################################################
# FunctionNode class
###############################################################################
class FunctionNode:
    """
    Represents a function node in the agentic system graph.

    Instead of interacting with an LLM, this node executes a user-defined function
    with the provided inputs.
    """

    def __init__(self, function, input_params=None, is_end_node=False, outputs=None):
        """
        Initialize a FunctionNode object.

        :param function: The callable Python function to execute.
        :param input_params: List of memory keys to use as input arguments for the function.
        :param is_end_node: Whether this node is an end node.
        :param outputs: List of memory keys to which the node's output will be saved.
        """
        self.function = function
        self.inputs = input_params if input_params else []
        self.is_end_node = is_end_node
        self.outputs = outputs if outputs else []

    def execute_function(self, inputs):
        """
        Execute the associated function with inputs retrieved from memory.
        """
        print(inputs)
        return self.function(*inputs)

    def generate(self, inputs):
        """
        Execute the function and return its result.
        """
        print(inputs)
        return self.execute_function(inputs)


###############################################################################
# Edges & System
###############################################################################
class Edge:
    """
    Represents a directed edge in the graph.
    
    - For an unconditional edge, condition=None, true_node is used,
      and false_node is None.
    - For a conditional edge, condition is a function taking (answer, memory)->bool,
      and both true_node/false_node must be specified.
    """

    def __init__(self, condition=None, true_node=None, false_node=None, repeating=False):
        """
        Initialize an Edge object.
        
        :param condition: A callable taking (answer, memory)->bool or None for unconditional.
        :param true_node: If condition is None, this is the single next node.
                          If condition is not None, this is the "true" branch node.
        :param false_node: Used only if condition is not None, the "false" branch node.
        :param repeating: If True, this edge can be traversed multiple times.
        """
        self.condition = condition
        self.true_node = true_node
        self.false_node = false_node
        self.repeating = repeating


class AgenticSystem:
    """
    Manages a directed graph of nodes, their dependencies, and edges determining
    the flow of control between nodes based on conditions.
    """

    def __init__(self):
        # Graph is a dictionary: { node_name: [Edge(...), ...] }
        self.graph = {}
        # Nodes is a dictionary: { node_name: Node(...) or FunctionNode(...) }
        self.nodes = {}
        # Memory stores output of each node: { node_name: answer_str }
        self.memory = {}
        # The name of the node where the reasoning starts
        self.starting_node = None

    def generate_answer(self, question, node=None, visited_edges=None, starting=False):
        """
        Generate an answer starting from the specified node (or the starting node if none specified).
        """
        function_inputs=[]
        if visited_edges is None:
            visited_edges = set()

        # If no node specified and initial question not recorded, assume starting node
        if node is None and starting:
            node = self.starting_node
            self.memory["question"] = question

        if node not in self.nodes:
            raise ValueError(f"Node '{node}' not found in the system.")

        current_node = self.nodes[node]

        # --- UPDATED: Collect all labeled inputs first, then call generate() once ---
        if current_node.inputs:
            labeled_inputs = []  # This will hold strings like "Label: <value>"
            
            # Gather each declared input from memory (or generate it if not present)
            for input_item in current_node.inputs:
                # Allow input_item to be a tuple (label, node_name) or just a string
                if isinstance(input_item, tuple) and len(input_item) == 2:
                    label, input_node_name = input_item
                else:
                    # If not a tuple, use the node name as the label
                    label = input_item
                    input_node_name = input_item

                # Special handling for "memory" or "all" keywords
                if input_node_name.lower() == "memory":
                    input_value = self.memory
                elif input_node_name.lower() == "all":
                    input_value = "\n".join([f"{k}: {v}" for k, v in self.memory.items()])
                else:
                    # If the answer from the input node isn't computed yet, generate it now
                    if self.memory.get(input_node_name) is None:
                        self.generate_answer(
                            self.memory.get("question", ""),
                            node=input_node_name,
                            visited_edges=visited_edges
                        )
                    input_value = self.memory.get(input_node_name, "")

                # If the input_value is an AIMessage, convert it to a string
                if isinstance(input_value, AIMessage):
                    input_value = input_value.content

                # Format the input with its label
                function_inputs.append(input_value)
                labeled_value = f"{label}:\n{input_value}"
                labeled_inputs.append(labeled_value)

            # Combine all labeled inputs into one string
            if isinstance(current_node, FunctionNode):
                # Function node expects a list of positional arguments
                answer = current_node.generate(function_inputs)
            else:
                combined_input = "\n\n".join(labeled_inputs)
                answer = current_node.generate(combined_input)
        else:
            # No inputs defined; pass the question as input
            answer = current_node.generate(question)

        # Store the node's output in memory
        if isinstance(answer, AIMessage):
            answer = answer.content

        self.memory[node] = answer

        # Let all nodes (including FunctionNode) store output to multiple keys
        if current_node.outputs:
            for out_key in current_node.outputs:
                self.memory[out_key] = answer

        # Logging
        self.log_node_io(
            node_name=node,
            input_data=(labeled_inputs if current_node.inputs else question),
            output_data=answer
        )

        # If this is an end node, stop the chain
        if current_node.is_end_node:
            print(f"Reached end node: '{node}'. Stopping the reasoning chain.")
            return self.memory.get(node, "")

        # Otherwise, traverse edges from this node (if any)
        if node in self.graph:
            for edge in self.graph[node]:
                # Decide where to go next
                if edge.condition is not None:
                    # Conditional edge
                    condition_result = edge.condition(answer, self.memory)
                    next_node = edge.true_node if condition_result else edge.false_node
                else:
                    # Unconditional edge
                    next_node = edge.true_node

                # If there's no next_node (e.g., a conditional edge with no false_node), skip
                if not next_node:
                    continue

                # Check repeating vs. visited
                edge_identifier = (node, next_node)
                if edge_identifier in visited_edges and not edge.repeating:
                    print(
                        f"Already traversed edge from '{node}' to '{next_node}'. "
                        f"Skipping to prevent cycles."
                    )
                    continue

                # Mark edge as traversed if not repeating
                if not edge.repeating:
                    visited_edges.add(edge_identifier)

                # Recursively continue the chain
                return self.generate_answer(
                    self.memory[node],
                    node=next_node,
                    visited_edges=visited_edges
                )

        # If no edges triggered or we got here, return the current node's output
        return self.memory[node]


    ###########################################################################
    # Methods to add nodes/edges
    ###########################################################################
    
    def add_to_memory(self, name, base=''):
        """
        Initialize or update an entry in memory directly.
        """
        self.memory[name] = base
        
    def add_function_node(self, name, function, input_params=None, is_end_node=False, outputs=None):
        """
        Add a new FunctionNode to the system.
        """
        node = FunctionNode(
            function=function,
            input_params=input_params,
            is_end_node=is_end_node,
            outputs=outputs
        )
        self.nodes[name] = node
        self.memory[name] = ''

    def define_start(self, name):
        """
        Define the starting node in the graph.
        """
        self.starting_node = name

    def add_edge(self, nodeA, nodeB, repeating=False):
        """
        Add an UNCONDITIONAL edge from nodeA to nodeB.
        """
        if nodeA not in self.graph:
            self.graph[nodeA] = []
        # condition=None => unconditional
        edge = Edge(
            condition=None,
            true_node=nodeB,
            false_node=None,
            repeating=repeating
        )
        self.graph[nodeA].append(edge)

    def add_conditional_edge(self, nodeA, true_node, false_node, condition, repeating=False):
        """
        Add a CONDITIONAL edge from nodeA with separate true/false branches.

        :param nodeA: The node from which this conditional edge departs.
        :param true_node: The node to go to if condition(answer, memory) == True.
        :param false_node: The node to go to if condition(answer, memory) == False.
        :param condition: A function taking (answer, memory)->bool
        :param repeating: Whether this edge can be traversed multiple times.
        """
        if nodeA not in self.graph:
            self.graph[nodeA] = []
        edge = Edge(
            condition=condition,
            true_node=true_node,
            false_node=false_node,
            repeating=repeating
        )
        self.graph[nodeA].append(edge)

    def add_node(
        self,
        instructions,
        cot,
        name: str,
        tool_caller: bool = False,
        tools=None,
        inputNodes=None,
        is_end_node=False,
        onPrem=False,
        outputs=None,
        model="Meta-Llama-3.1-70B-Instruct",
        temperature=0.1
    ):
        """
        Add a new LLM-based node to the system.

        Now accepts dynamic model and temperature parameters.
        """
        node = Node(
            instructions,
            cot,
            is_end_node=is_end_node,
            onPrem=onPrem,
            outputs=outputs,
            model=model,
            temperature=temperature
        )

        if inputNodes:
            node.set_input_nodes(inputNodes)

        if tool_caller and tools:
            node.toolCalling(tools=tools)

        self.nodes[name] = node
        self.memory[name] = ''

    ###########################################################################
    # Debugging Helpers
    ###########################################################################

    def log_node_io(self, node_name, input_data, output_data):
        """
        Log the input and output of a node in a formatted manner to a file called "runs".
        Each call appends to the file so that logs from different runs are gathered together.
        """
        # Optionally, include a timestamp for each log entry.
        timestamp = datetime.datetime.now().isoformat()
        separator = "=" * 50
        # Build the log string.
        log_lines = [
            separator,
            f"Timestamp: {timestamp}",
            f"Node: {node_name}",
            "-" * 50,
            "Input:",
            textwrap.fill(str(input_data), width=80),
            "-" * 50,
            "Output:",
            textwrap.fill(str(output_data), width=80),
            separator + "\n"
        ]
        log_str = "\n".join(log_lines)
        # Append the log string to the file "runs"
        print(log_str)
        print(f"\n\ninput: {input_data}\n\n")
        print(f"\n\noutput: {output_data}\n\n")
        with open("runs_practice.txt", "a") as file:
            file.write(log_str + "\n")

    def print_system_state(self):
        """
        Print current system state: memory, nodes, edges.
        """
        print("\n------ AgenticSystem State ------")

        print("Memory (Node Outputs):")
        if not self.memory:
            print("  No memory outputs available.")
        else:
            for node_name, output in self.memory.items():
                if isinstance(output, dict):
                    output = output.get('content', str(output))
                print(f"  {node_name}: {output}")

        print("\nNodes and their input dependencies:")
        if not self.nodes:
            print("  No nodes available.")
        else:
            for node_name, node_obj in self.nodes.items():
                input_deps = ", ".join(node_obj.inputs) if node_obj.inputs else "None"
                end_flag = " (End Node)" if getattr(node_obj, 'is_end_node', False) else ""
                print(f"  Node '{node_name}': input nodes = {input_deps}{end_flag}")

        print("\nGraph Structure (Edges):")
        if not self.graph:
            print("  No graph structure defined.")
        else:
            for node_name, edges in self.graph.items():
                for edge in edges:
                    if edge.condition is None:
                        cond_str = "Unconditional"
                        targ_str = edge.true_node
                    else:
                        cond_str = "Conditional"
                        targ_str = f"(true_node={edge.true_node}, false_node={edge.false_node})"
                    repeat_str = " (repeating)" if edge.repeating else ""
                    print(f"  {node_name} --({cond_str}{repeat_str})--> {targ_str}")

        print("---------------------------------\n")
