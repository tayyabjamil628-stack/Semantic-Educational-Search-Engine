import os
import psycopg
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("API Booted. Model loaded into memory.")
    yield
    print("Shutting down API.")

# Initialize the app ONCE
app = FastAPI(lifespan=lifespan, title="Semantic Search API")

# Attach middleware to the active instance
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

model = SentenceTransformer('all-MiniLM-L6-v2')

DB_DSN = (
    f"dbname={os.getenv('DB_NAME', 'vectordb')} "
    f"user={os.getenv('DB_USER', 'admin')} "
    f"password={os.getenv('DB_PASSWORD', 'password123')} "
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')}"
)

@app.get("/search")
async def search(q: str = Query(..., min_length=3, description="Search query")):
    try:
        query_vector = model.encode(q).tolist()
        
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as acur:
                await acur.execute(
                    """
                    SELECT title, content, 1 - (embedding <=> %s::vector) AS similarity 
                    FROM resource_chunks 
                    ORDER BY embedding <=> %s::vector 
                    LIMIT 3;
                    """,
                    (str(query_vector), str(query_vector))
                )
                records = await acur.fetchall()
        
        return {
            "query": q,
            "results": [
                {
                    "title": row[0],
                    "content": row[1].strip(),
                    "similarity": round(row[2], 4)
                }
                for row in records
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")