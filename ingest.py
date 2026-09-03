# FILE: ingest.py
import os
import psycopg
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

DB_PARAMS = {
    "dbname": "vectordb",
    "user": "admin",
    "password": "password123",
    "host": "localhost",
    "port": "5432"
}

def chunk_text(text, chunk_size=300):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def ingest_markdown(file_path, source_url):
    if not os.path.exists(file_path):
        print(f"CRITICAL: Target file {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    title = os.path.basename(file_path)
    chunks = chunk_text(content)
    
    # psycopg (v3) context managers automatically handle commits and connection closures
    with psycopg.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            for index, chunk in enumerate(chunks):
                embedding = model.encode(chunk).tolist()
                
                cur.execute(
                    """
                    INSERT INTO resource_chunks (source_url, title, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    # Stringifying the list allows Postgres to cast it directly to the VECTOR type
                    (source_url, title, index, chunk, str(embedding))
                )
                print(f"Inserted chunk {index+1}/{len(chunks)} for {title}")

if __name__ == "__main__":
    test_file = "sample.md"
    if not os.path.exists(test_file):
        with open(test_file, "w") as f:
            f.write("This is a highly technical test document explaining semantic search and vector embeddings. " * 50)
            
    ingest_markdown(test_file, "http://localhost/sample.md")