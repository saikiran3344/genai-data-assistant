import os
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings

load_dotenv()

_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading Ollama Embedding Model...")
        _model = OllamaEmbeddings(
            model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            base_url = os.getenv("OLLAMA_BASE_URL", "https://localhost:11434"),
        )
        print("Embedding model loaded.")
    return _model

def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    return model.embed_documents(texts)

def embed_query(text: str) -> list[float]:
    model = get_model()
    return model.embed_query(text)

def get_embedding_dimension() -> int:
    vec = embed_query("test")
    return len(vec)

if __name__=="__main__":
    dim = get_embedding_dimension()
    print(f"Embedding dimensions: {dim}")

    test = "Struggling to get a Job."
    vector = embed_query(test)
    print(f"vector length: {len(vector)}")
    print(f"First 5 values:{[round(v,4) for v in vector[:5]]}")
    print("Embeddings are working correctly")