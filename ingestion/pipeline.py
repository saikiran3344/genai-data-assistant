from ingestion.loader import load_file
from vectorstore.store import setup_table, ingest_documents, get_chunk_count, clear_documents


def run_ingestion(file_path: str, force_refresh: bool = False):
    print(f"\n starting ingestion: {file_path}")
    setup_table()
    if force_refresh:
        clear_documents(source=file_path)

    docs = load_file(file_path)
    print(f"Parsed {len(docs)} chunks from file")
    
    ingest_documents(docs)
    total = get_chunk_count()
    print(f"Pipeline completed. Total chunks in DB: {total}")
    return docs