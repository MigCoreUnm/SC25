from AgenticFramework.OnPremLLM.myLLM import LLM
from dotenv import load_dotenv
import os


class toolCallingLLM():
    def __init__(self):
        path = "/lustre/vescratch1/miguelcord/llms/llama321b/checkpoints"
        self.tools = {}
        self.prompt = None
        self.llm = LLM(path,max_new_tokens=4096,temperature=0.1, top_p=.9)
    
    def attach_tools(self, tools):
        tool_descriptions = {}
        for tool in tools:
            name = tool.__name__
            self.tools[name] = tool
            tool_descriptions[name] = getattr(tool, 'custom_data', None)
            
        
        self.prompt = f"""
        IINSTRUCTIONS:
        You always respond with a JSON object that has two required keys.

        tool_calls: List[ToolCall] = Field(description="List of tool calls, empty array if you don't need to invoke a tool")
        content: str = Field(description="Response to the user if a tool doesn't need to be invoked")

        Here is the type for ToolCall (object with two keys):
            name: str = Field(description="Name of the function to run (NA if you don't need to invoke a tool)")
            args: dict = Field(description="Arguments for the function call (empty array if you don't need to invoke a tool or if no arguments are needed for the tool call)")

        Don't start your answers with "Here is the JSON response", just give the JSON.

        The tools you have access to are:

        {"".join(tool_descriptions)}

        Any message that starts with "Thought:" is you thinking to yourself. This isn't told to the user so you still need to communicate what you did with them.
        Don't repeat an action. If a thought tells you that you already took an action for a user, don't do it again.\n
        USER QUERY:\n
            """
    
    def generate(self, prompt):
        prompt =self.prompt.join(prompt)
        response =self.llm.generate(prompt,True)
        response_2 = self.tool_response(self,response)
        final_response = {
            "tool_calls" : response, 
            "tool_responses" : response_2
        }
        return final_response
    def tool_response(self, tool_call):
        tool_responses = {}
        for tool in tool_call:
            name = tool.name 
            args = tool.args
            tool_responses[name] = self.tools[name](**args)
        return tool_responses
