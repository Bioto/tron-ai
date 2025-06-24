from tron_intelligence.processors import BaseProcessor


from sentence_transformers import SentenceTransformer

transformer = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=".cache/sentence_transformers")

class SimpleEmbeddingsProcessor(BaseProcessor):
    def process(self, text: str, *args, **kwargs) -> str:
        return transformer.encode(text)


if __name__ == "__main__":
    processor = SimpleEmbeddingsProcessor()
    print(processor.process("Hello, world!"))
