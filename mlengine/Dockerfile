FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # Cache Sentence Transformer models inside the container volume
    SENTENCE_TRANSFORMERS_HOME=/app/models_cache \
    # Disable HuggingFace progress bars in logs
    TRANSFORMERS_VERBOSITY=error \
    HF_HUB_DISABLE_PROGRESS_BARS=1

# System deps: gcc for building extensions, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install all Python deps (includes sentence-transformers + torch)
# We pre-install the CPU version of PyTorch to avoid massive CUDA downloads (saving ~2.5 GB)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download models at build time so the container starts instantly.
# The models are cached to /app/models_cache which is stored inside the image.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-MiniLM-L6-v2'); \
    SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); \
    print('Models pre-downloaded successfully')"

EXPOSE 5001

# Healthcheck using curl against the /health endpoint
HEALTHCHECK --interval=20s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:5001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5001"]
