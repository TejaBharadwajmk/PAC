"""
PAC — ML Engine Service (Phase 2)

Production Sentence Transformer embedding service.
Loads all-MiniLM-L6-v2 once at startup, serves 384-dim embeddings.

Design:
  - Model loaded once into module-level singleton (thread-safe, no GIL issues for inference)
  - /embed  → batch text embedding (used by backend background tasks)
  - /health → liveness + model readiness check
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

import os

logger = logging.getLogger(__name__)

# ── Model Singleton ────────────────────────────────────────────
# Loaded once at startup. SentenceTransformer inference is thread-safe.
_model = None
_model_load_time: Optional[float] = None
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))


def _load_model():
    """Load Sentence Transformer model into process memory and run startup validation."""
    global _model, _model_load_time
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading model: {MODEL_NAME} ...")
        t0 = time.time()
        _model = SentenceTransformer(MODEL_NAME)
        _model_load_time = time.time() - t0
        
        # Run startup validation: generate test embedding
        test_vector = _model.encode(["validation test"], show_progress_bar=False)
        actual_dim = len(test_vector[0])
        
        # Verify dimension matches config
        if actual_dim != EMBEDDING_DIM:
            error_msg = (
                f"CRITICAL CONFIGURATION ERROR: Expected embedding dimension {EMBEDDING_DIM}, "
                f"but model '{MODEL_NAME}' returned dimension {actual_dim}."
            )
            logger.critical(error_msg)
            raise ValueError(error_msg)
            
        device = getattr(_model, "device", "cpu")
        
        logger.info("=========================================")
        logger.info("PAC ML Engine Startup Configuration:")
        logger.info(f"  Embedding Model  : {MODEL_NAME}")
        logger.info(f"  Expected Dim     : {EMBEDDING_DIM}")
        logger.info(f"  Actual Dim       : {actual_dim}")
        logger.info(f"  Device           : {device}")
        logger.info(f"  Cache Status     : Cached (Local Build)")
        logger.info(f"  Validation Result: PASS")
        logger.info("=========================================")
        
        # Ensure stdout visibility in Docker logs
        print("=========================================")
        print("PAC ML Engine Startup Configuration:")
        print(f"  Embedding Model  : {MODEL_NAME}")
        print(f"  Expected Dim     : {EMBEDDING_DIM}")
        print(f"  Actual Dim       : {actual_dim}")
        print(f"  Device           : {device}")
        print(f"  Cache Status     : Cached (Local Build)")
        print(f"  Validation Result: PASS")
        print("=========================================")
        
    except Exception as e:
        logger.critical(f"Failed to load/validate model {MODEL_NAME}: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, release on shutdown."""
    _load_model()
    yield
    global _model
    _model = None
    logger.info("Model released.")


# ── FastAPI App ────────────────────────────────────────────────
app = FastAPI(
    title="PAC ML Engine",
    version="2.0.0",
    description=(
        "Crime DNA embedding service using Sentence Transformers.\n\n"
        f"**Model**: `{MODEL_NAME}`  \n"
        f"**Output**: `{EMBEDDING_DIM}`-dimensional dense vectors  \n"
        "**Use**: Cosine similarity search via pgvector"
    ),
    docs_url="/docs",
    lifespan=lifespan,
)


# ── Schemas ────────────────────────────────────────────────────

class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, description="List of MO text strings to embed")
    crime_ids: List[str] = Field(default_factory=list, description="Optional: corresponding crime UUIDs for logging")
    normalize: bool = Field(default=True, description="L2-normalize embeddings (recommended for cosine similarity)")


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dim: int
    count: int
    elapsed_ms: float


class HealthResponse(BaseModel):
    status: str
    model: str
    dimension: int
    device: str
    ready: bool


# ── Endpoints ──────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Meta"])
async def health():
    """Liveness + model readiness check."""
    return HealthResponse(
        status="healthy" if _model is not None else "degraded",
        model=MODEL_NAME,
        dimension=EMBEDDING_DIM,
        device=str(getattr(_model, "device", "cpu")),
        ready=_model is not None,
    )


@app.post("/embed", response_model=EmbedResponse, tags=["Embedding"])
async def embed_texts(request: EmbedRequest):
    """
    Generate 384-dim dense embeddings for a batch of MO text strings.

    - Runs synchronously in the async handler (SentenceTransformer uses torch,
      which releases the GIL during inference — safe for async context).
    - Embeddings are L2-normalised by default (required for cosine similarity via pgvector).
    """
    if _model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Service is starting up.",
        )

    if not request.texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="texts list cannot be empty",
        )

    if len(request.texts) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum batch size is 500 texts per request",
        )

    t0 = time.time()
    try:
        embeddings = _model.encode(
            request.texts,
            normalize_embeddings=request.normalize,
            show_progress_bar=False,
            batch_size=32,
            convert_to_numpy=True,
        )
        elapsed_ms = (time.time() - t0) * 1000

        logger.info(
            f"Embedded {len(request.texts)} texts in {elapsed_ms:.1f}ms "
            f"| crime_ids={request.crime_ids[:3]}{'...' if len(request.crime_ids) > 3 else ''}"
        )

        return EmbedResponse(
            embeddings=[e.tolist() for e in embeddings],
            model=MODEL_NAME,
            dim=EMBEDDING_DIM,
            count=len(embeddings),
            elapsed_ms=round(elapsed_ms, 2),
        )

    except Exception as exc:
        logger.error(f"Embedding failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding error: {str(exc)}",
        )


@app.get("/model/info", tags=["Meta"])
async def model_info():
    """Return technical details about the loaded model."""
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {
        "model_name": MODEL_NAME,
        "embedding_dim": EMBEDDING_DIM,
        "max_seq_length": getattr(_model, "max_seq_length", 256),
        "tokenizer": str(type(_model.tokenizer).__name__) if hasattr(_model, "tokenizer") else "unknown",
        "model_load_time_s": _model_load_time,
    }
