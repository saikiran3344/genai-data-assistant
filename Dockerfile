# ─────────────────────────────────────────────────────────────
# GenAI Data Assistant – API + UI image
# Runs FastAPI (port 8000) and Streamlit (port 8501) together.
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps (for psycopg, pdf parsing, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application source
COPY . .

# Make sure uploads dir exists at runtime
RUN mkdir -p /app/data/uploads

EXPOSE 8000 8501

# Default: launch FastAPI (UI runs as a separate compose service)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
