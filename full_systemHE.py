from d_systems.codeGenerationSystemRolling  import generate_code
from d_systems.testingSuiteSystem import run_unit_tests_and_analysis
from d_systems.questionBreakdownSystem import breakdown_system
import time


def full_system(question:str, collection:str ="",model="Meta-Llama-3.3-70B-Instruct",temp=.1):
    start_time =time.time()
    prompts = breakdown_system(question, model, temp)
    code = generate_code(question, prompts, model, temp)

    try:
        code2, regens = run_unit_tests_and_analysis(code, question, model, temp)
    except Exception as e:
        code2 = "error running analysis"
        regens = None

    end_time = time.time()
    elapsed_time = end_time - start_time  

    return code, code2, regens, elapsed_time

    
