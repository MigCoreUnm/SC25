from lanlCodeGeneration import generate_code
from lanlTestingSuite import run_unit_tests_and_analysis
from lanlQBreakdown import breakdown_system
import time


def full_system(question:str, collection:str ="",model="",temp=.1):
    start_time =time.time()
    prompts, file = breakdown_system(question, model, temp)
    code = generate_code(question, prompts,files=file)
    return code, code, 0, 0
    try:        
        code2, regens = run_unit_tests_and_analysis(code, question, model, temp)
    except Exception as e:
        code2 = e
        regens = None

    end_time = time.time()
    elapsed_time = end_time - start_time  

    return code, code2, regens, elapsed_time

    
