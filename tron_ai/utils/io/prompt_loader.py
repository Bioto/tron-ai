import os

def load_local_prompt(prompt_name: str) -> str:
    with open(os.path.join(os.path.dirname(__file__), "..", "..", "prompts", f"{prompt_name}.md"), "r") as file:
        return file.read()