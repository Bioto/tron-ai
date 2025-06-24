from typing import Callable
from functools import wraps


def with_args(*bind_args, **bind_kwargs):
    """
    Decorator that allows binding additional arguments to a function.
    
    Args:
        *bind_args: Positional arguments to bind to the function
        **bind_kwargs: Keyword arguments to bind to the function
    
    Returns:
        A decorator that wraps the function with pre-bound arguments
    
    Example:
        @with_args(user_query="example query", some_param=True)
        def my_function(state, user_query, some_param):
            return f"State: {state}, Query: {user_query}, Param: {some_param}"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Merge bound kwargs with runtime kwargs (runtime takes precedence)
            merged_kwargs = {**bind_kwargs, **kwargs}
            return await func(*bind_args, *args, **merged_kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Merge bound kwargs with runtime kwargs (runtime takes precedence)
            merged_kwargs = {**bind_kwargs, **kwargs}
            return func(*bind_args, *args, **merged_kwargs)
        
        # Return async wrapper if the original function is async, otherwise sync
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
