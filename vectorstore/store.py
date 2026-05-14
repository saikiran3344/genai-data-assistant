import os
import psycopg2
import hashlib
from dotenv import load_dotenv
from langchain_core.documents import Document
from embeddings.embedder import embed_query, embed_texts, get_embedding_dimension

load_dotenv

EMBEDDING_DIM = get_embedding_dimension()

def get_connection():
    return psycopg2.connect(
        host = os.getenv("DB_HOST", "localhost"),
        port = os.getenv("DB_PORT", 5432),
        dbname = os.getenv("DB_NAME", "genai_db"),
        user = os.getenv("DB_USER", "postgres"),
        password = os.getenv("DB_PASSWORD", "")
    )


def setup_table():
    """
    Creates vector table and index if they don't exist
    safe to call multiple times--it will not overwrite existing data.
    """
    conn = get_connection()
    cur = conn.cursor()
#CREATE EXTENSION IF NOT EXISTS.
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
#CREATES CHUNK TABLE
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id        SERIAL PRIMARY KEY,
            content   TEXT NOT NULL,
            source    TEXT,
            chunk_type TEXT,
            row_index  INTEGER,
            page       INTEGER,
            chunk_hash TEXT UNIQUE,
            embedding  vector({EMBEDDING_DIM}),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                      );
                 """)
    
    #IVFFLAT index for fast cosine similarity search
    cur.execute("""
        CREATE  INDEX IF NOT EXISTS idx_chunks_embedding
                ON documents_chunks
                USING ivfflat(embedding vector_cosine_ops)
                WITH (lists = 50);
            """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database table and index are ready")

#create unique hash key to check for duplicates.
def generate_chunk_hash(content: str, source: str = "") -> str:
    raw = f"{source}:{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def get_existing_hashes() -> set[str]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT chunk_hash FROM document_chunks WHERE chunk_hash IS NOT NULL")
    rows = cur.fetchall()
    hashes = {row[0] for row in rows}

    cur.close()
    conn.close()
    return hashes

def ingest_documents(documents: list[Document]):
    if not documents:
        print("No documents to ingest")
        return
    
    existing_hashes = get_existing_hashes()

    new_documents =[]
    new_hashes = []

    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        chunk_hash = generate_chunk_hash(doc.page_content, source)
        if chunk_hash not in existing_hashes:
            new_documents.append(doc)
            new_hashes.append(chunk_hash)
        else:
            print("No new documents to ingest. Database is already upto date...")
        
    print(f"Generating embeddings for {len(new_documents)} chunks...")
    texts = [doc.page_content for doc in new_documents]
    embeddings = embed_texts(texts)

    conn = get_connection()
    cur = conn.cursor()

    inserted = 0
    for doc, embedding, chunk_hash in zip(new_documents, embeddings, new_hashes):
        cur.execute("""
             INSERT INTO document_chunks
                     (content, source, chunk_type, row_index, page, chunk_hash, embedding, updated_at)
                VALUES(%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (chunk_hash) DO NOTHING         
        """, (
            doc.page_content,
            doc.metadata.get("source", "unknown"),
            doc.metadata.get("type", "unknown"),
            doc.metadata.get("row", None),
            doc.metadata.get("page", None),
            chunk_hash,
            embedding
        ))
            
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"successfully stored {inserted} chunks in pgvector")

def similarity_search(query: str, k: int = 5) -> list[Document]:
    query_vector = embed_query(query)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
                content, source, chunk_type, row_index, page,
                1 - (embedding <=> %s::vector) AS similarity
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
    """, (query_vector, query_vector, k))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = []
    for row in rows:
        content, source, chunk_type, row_index, page, similarity = row
        results.append(Document(
            page_content = content,
            metadata = {
                "source": source,
                "type": chunk_type,
                "row": row_index,
                "page": page,
                "similarity_score": round(float(similarity), 4)
            }
        ))
    return results

def clear_documents(source: str = None):
    """
    Delete chunks by source file or all chunks in the DB(if no source is given)
    useful when re-uploading the same file
    """
    conn = get_connection()
    cur = conn.cursor()
    if source:
        cur.execute("DELETE FROM document_chunks WHERE source = %s", (source,))
        print(f"cleared chunks for : {source}")
    else:
        cur.execute("DELETE FROM document_chunks")
        print(f"Cleared all data from the database.")
    conn.commit()
    conn.close()
    cur.close()


def get_chunk_count() -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM document_chunks")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count

if __name__=="__main__":
    print(f"Setting up Database....")
    setup_table()
    count = get_chunk_count()
    print(f"Current chunks in database are: {count}")
    print(f"Vector Database is working perfectly....")

