

def load_local_prompt(prompt_name: str) -> str:
    with open(f"./prompts/{prompt_name}.md", "r") as file:
        return file.read()