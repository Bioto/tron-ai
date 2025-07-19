def __getattr__(name):
    if name == "LLMClient":
        from .LLMClient import LLMClient
        return LLMClient
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["LLMClient"]