import pandas as pd
from langchain_core.documents import Document

def load_csv(file_path: str, nrows: int = 100):
    if file_path.endswith("xlsx"):
        df = pd.read_excel(file_path, engine = 'openpyxl', nrows = 100)
    else:
        df = pd.read_csv(file_path, nrows = 100)
    
    df.fillna("N/A")

    documents = []
    for i, row in df.iterrows():
        content = ",".join([
            f"{col}: {val}"
            for col, val in row.items()
        ])
        documents.append(Document(
            page_content = content,
            metadata = {
                "source": file_path,
                "type": "csv",
                "row":i
            }
        ))
    print(f"[csv] loaded {len(documents)} rows as documents")
    return documents
    