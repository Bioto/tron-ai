from pathlib import Path


def load_prompt_content(prompt_name: str) -> str:
    """Load a prompt from the prompts directory."""
    prompt_path = Path(__file__).parent / "res" / f"{prompt_name}.md"

    with open(prompt_path, "r") as file:
        return file.read()
