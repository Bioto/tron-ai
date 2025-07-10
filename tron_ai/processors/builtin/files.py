from markitdown import MarkItDown
from tron_ai.utils.llm.LLMClient import LLMClient, get_llm_client
from tron_ai.processors import BaseProcessor


class FileProcessor(BaseProcessor):
    def process(self, file_path: str, client: LLMClient) -> str:
        md = MarkItDown(llm_client=client.api_client, llm_model=client.model)
        result = md.convert(file_path)

        return result.text_content


if __name__ == "__main__":
    llm_client = get_llm_client()
    processor = FileProcessor()
    result = processor.process("tron_ai/processors/test.html", llm_client)
    print(result)
