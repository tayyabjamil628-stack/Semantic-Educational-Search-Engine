# FILE: ingest_bulk.py
import os
import psycopg
from sentence_transformers import SentenceTransformer
from pathlib import Path

model = SentenceTransformer('all-MiniLM-L6-v2')

# Dynamically construct DSN to survive cloud deployment
DB_DSN = (
    f"dbname={os.getenv('DB_NAME', 'vectordb')} "
    f"user={os.getenv('DB_USER', 'admin')} "
    f"password={os.getenv('DB_PASSWORD', 'password123')} "
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')}"
)

# ... (Keep the semantic_chunking and ingest_directory functions exactly the same) ...

def semantic_chunking(text, max_length=1000):
    """
    Splits text by markdown paragraphs (\n\n) to avoid breaking code blocks.
    Groups smaller paragraphs together up to max_length characters to ensure dense vectors.
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        if len(current_chunk) + len(p) < max_length:
            current_chunk += p + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def ingest_directory(target_path):
    base_dir = Path(target_path)
    if not base_dir.exists():
        print(f"CRITICAL: Directory {target_path} not found.")
        return

    # Recursively find all markdown files in the English documentation
    md_files = list(base_dir.rglob("*.md"))
    print(f"Located {len(md_files)} markdown files. Commencing ingestion pipeline...")

    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            for file_path in md_files:
                try:
                    content = file_path.read_text(encoding='utf-8')
                    chunks = semantic_chunking(content)
                    
                    # Store the relative path as the source URL for frontend reference
                    source_url = f"fastapi/docs/{file_path.relative_to(base_dir)}"
                    title = file_path.name
                    
                    for index, chunk in enumerate(chunks):
                        if len(chunk) < 50:  # Drop useless fragments (e.g., stray markdown formatting)
                            continue
                            
                        embedding = model.encode(chunk).tolist()
                        
                        cur.execute(
                            """
                            INSERT INTO resource_chunks (source_url, title, chunk_index, content, embedding)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (source_url, title, index, chunk, str(embedding))
                        )
                    print(f"SUCCESS: Ingested {len(chunks)} chunks from {title}")
                except Exception as e:
                    print(f"FAILED on {file_path.name}: {e}")

if __name__ == "__main__":
    # Point directly to the English documentation folder you just cloned
    target_directory = "fastapi_docs/docs/en/docs"
    ingest_directory(target_directory)