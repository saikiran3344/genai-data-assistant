from ingestion.loader import load_file

def run_ingestion(file_path: str):
    print(f"\n starting ingestion: {file_path}")
    docs = load_file(file_path)
    print("docs type:", type(docs))
    print("docs value:", docs)
    print(f"\n ingestion completed: {len(docs)} chunks ready")
    return docs