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
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download the model at build time so the container starts instantly.
# The model is cached to /app/models_cache which is mounted as a Docker volume.
# On rebuild, Docker layer cache skips this step if requirements.txt unchanged.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-MiniLM-L6-v2'); \
    print('Model pre-downloaded successfully')"

EXPOSE 5001

# Healthcheck using curl against the /health endpoint
HEALTHCHECK --interval=20s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:5001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5001"]
