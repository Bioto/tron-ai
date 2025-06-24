from adalflow import OpenAIClient
from markitdown import MarkItDown
from tron_intelligence.utils.LLMClient import LLMClient
from tron_intelligence.processors import BaseProcessor


class FileProcessor(BaseProcessor):
    def process(self, file_path: str, client: LLMClient) -> str:
        md = MarkItDown(llm_client=client.api_client, llm_model=client.model)
        result = md.convert(file_path)

        return result.text_content


if __name__ == "__main__":
    from tron_intelligence.utils.LLMClient import LLMClientConfig

    llm_client = LLMClient(
        client=OpenAIClient(), config=LLMClientConfig(model_name="gpt-4o")
    )
    processor = FileProcessor()
    result = processor.process("tron_intelligence/processors/test.html", llm_client)
    print(result)
