from functools import wraps
def execution(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    definition = func.__doc__
    name = func.__name__
    custom_data = f""" The name of the functions is {name}. The definition of the function is as follows : {definition}\n"""
    setattr(func, 'custom_data', custom_data)
    return wrapper
        
    
        