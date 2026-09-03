# FILE: Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for psycopg and compiling native extensions
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install fastapi[all]==0.110.0

COPY . .

# Expose the API port
EXPOSE 8000

# Run Uvicorn bound to all network interfaces
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]