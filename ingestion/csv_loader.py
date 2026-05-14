import pandas as pd
import os
from langchain_core.documents import Document


def load_csv(file_path: str):
    file_path = os.path.normpath(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path, engine="openpyxl")
    else:
        # Try encodings in order until one works
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        df = None
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"[CSV] Read file using encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            raise ValueError(
                f"Could not read {file_path} with any known encoding. "
                f"Try saving the file as UTF-8 CSV."
            )

    # Fill empty cells
    df.fillna("N/A", inplace=True)

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
    