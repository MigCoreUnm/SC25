import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json

#/lustre/vescratch1/miguelcord/llms/llama321b/checkpoints
class LLM():
    def __init__(self,path, max_new_tokens = 4096, temperature = .5, top_p=0.9):
        self.tokenizer = AutoTokenizer.from_pretrained(path, use_fast=False)
        self.model = AutoModelForCausalLM.from_pretrained(path)
        self.maxNT = max_new_tokens
        self.temp = temperature
        self.topP = top_p
        self.device = None
        self.setupLLM()


    def setupLLM(self):
        # sets the model to evaulation mode and either gpu or cpu 
        self.model.eval()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model.to(device)
    
    def generate(self,prompt,json_f=False):
        # Tokenize input
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(inputs.input_ids, max_new_tokens=100, temperature=0.7, top_p=0.9)

        # Decode response
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        if json_f:
            response = json.loads(response)
        return response
    
path = "/lustre/vescratch1/miguelcord/llms/llama321b/checkpoints"
