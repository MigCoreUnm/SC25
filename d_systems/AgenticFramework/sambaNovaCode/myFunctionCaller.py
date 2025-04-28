import openai
import cmath
import json

# Initialize the client with SN Cloud base URL and your API key
client = openai.OpenAI(
    base_url="https://api.sambanova.ai/v1", 
    api_key= API_KEY
)

def solve_quadratic(a, b, c, root_type="real"):
    """
    Solve a quadratic equation of the form ax^2 + bx + c = 0.
    """
    discriminant = b**2 - 4*a*c
    
    if root_type == "real":
        if discriminant < 0:
            return []  # No real roots
        else:
            root1 = (-b + discriminant**0.5) / (2 * a)
            root2 = (-b - discriminant**0.5) / (2 * a)
            return [root1, root2]
    else:
        root1 = (-b + cmath.sqrt(discriminant)) / (2 * a)
        root2 = (-b - cmath.sqrt(discriminant)) / (2 * a)
        return [
            {"real": root1.real, "imag": root1.imag},
            {"real": root2.real, "imag": root2.imag}
        ]


# Define user input and function schema
user_prompt = "Find all the roots of a quadratic equation given coefficients a = 3, b = -11, and c = -4."
messages = [

        {
            "role": "user",
            "content": user_prompt,
        }
    ]

tools = [
    {
        "type": "function",
        "function": {
            "name": "run_py",
            "description": "runs python code will take in the code and the dependecies",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "Coefficient of the squared term"},
                    "b": {"type": "integer", "description": "Coefficient of the linear term"},
                    "c": {"type": "integer", "description": "Constant term"},
                    "root_type": {"type": "string", "description": "Type of roots: 'real' or 'all'"}
                },
                "required": ["a", "b", "c"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="Meta-Llama-3.1-70B-Instruct",
    messages=messages,
    tools=tools,
    tool_choice="required"
)

print(response)