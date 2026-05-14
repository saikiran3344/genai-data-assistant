import os
from ingestion.pdf_loader import load_pdf
from ingestion.csv_loader import load_csv

supported_types = [".pdf",".csv",".xlsx"]

def load_file(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"file not found: {file_path}")
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in supported_types:
        raise ValueError(
            f"UNSUPPORTED file type: {ext}."
            f"SUPPORTED file type:{supported_types}"
        )
    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext in [".csv", ".xlsx"]:
        return load_csv(file_path)
    else:
        raise ValueError(f"unhandled file type: {ext}")
