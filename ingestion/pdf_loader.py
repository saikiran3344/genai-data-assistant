from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_pdf(file_path: str) -> list:
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50,
        separators = ["\n\n", "\n", ".", " "]
    )
    chunks = splitter.split_documents(documents)
    print(f"[pdf] loaded {len(documents)} pages -> {len(chunks)} chunks")
    return chunks
