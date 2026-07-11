# PAC — PoliceIT Analytics Core

> **AI-Powered Investigation Intelligence Platform for Karnataka State Police**

PAC acts as an intelligence layer above existing PoliceIT/CCTNS systems. It transforms static crime records into actionable behavioural intelligence — connecting crimes through behavioural similarity instead of keyword matching.

---

## Project Structure

```
PAC/
├── backend/                    # FastAPI — Core Intelligence API
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── config.py           # pydantic-settings
│   │   ├── database.py         # Async SQLAlchemy engine
│   │   ├── dependencies.py     # DI: DB session, JWT auth, RBAC
│   │   ├── core/               # Security, exceptions, logging
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic v2 request/response
│   │   ├── repositories/       # Data access layer
│   │   ├── services/           # Business logic + AI orchestration
│   │   └── api/v1/routers/     # FastAPI routers
│   ├── alembic/                # DB migrations
│   └── scripts/                # seed_data.py, create_admin.py
│
├── mlengine/                   # Sentence Transformers ML service
│   └── app/main.py             # Embedding API (Phase 2)
│
├── frontend/                   # React + TailwindCSS (Phase 5)
├── docs/                       # Architecture & API docs
├── docker/
│   ├── Dockerfile.postgres     # PostGIS + pgvector combo image
│   └── init_db.sql             # Extension bootstrap
└── docker-compose.yml          # All 6 services
```

---

## Quick Start

### 1. Clone & Configure

```bash
cp backend/.env.example backend/.env
cp mlengine/.env.example mlengine/.env
# Edit backend/.env — set a strong SECRET_KEY
```

### 2. Launch Services

```bash
docker-compose up -d postgres neo4j redis
# Wait for postgres to be healthy (~30s)
docker-compose up -d backend mlengine
```

### 3. Run Migrations

```bash
docker exec pac_backend alembic upgrade head
```

### 4. Seed Karnataka Crime Dataset

```bash
docker exec pac_backend python scripts/seed_data.py
```

This inserts **1,500 realistic Karnataka crime records** across 10 districts with:
- 5 criminal gang networks (30 total criminals)
- Behavioural MO pattern clusters (same behaviour, different words)
- Geographic clustering for hotspot detection
- 3-year history (2022–2024)

### 5. Access API

| Endpoint | URL |
|---|---|
| **Swagger Docs** | http://localhost:8000/api/docs |
| **ReDoc** | http://localhost:8000/api/redoc |
| **Health Check** | http://localhost:8000/health |
| **Neo4j Browser** | http://localhost:7474 |

**Admin credentials** (after seeding):
- Badge: `ADMIN001`
- Password: `Admin@2024`

---

## Services

| Service | Image | Port | Purpose |
|---|---|---|---|
| `postgres` | PostGIS 16 + pgvector | 5432 | Primary DB + spatial + vectors |
| `neo4j` | neo4j:5-community | 7474/7687 | Criminal network graphs |
| `redis` | redis:7 | 6379 | Cache + task queue |
| `backend` | FastAPI (Python 3.11) | 8000 | Core intelligence API |
| `mlengine` | Python 3.11 | 5001 | Sentence Transformer embeddings |
| `frontend` | React + Nginx | 3000 | Investigation dashboard |

---

## Intelligence Architecture

```
Crime Registered (FIR)
       ↓
Rule-Based MO Extraction   → structured features (fast, free)
       ↓
Sentence Transformer       → 384-dim vector (all-MiniLM-L6-v2)
       ↓
pgvector storage           → Crime DNA stored permanently
       ↓
Officer searches           → cosine similarity in milliseconds
```

**Core principle**: Intelligence is generated once, stored permanently, retrieved instantly.

---

## API Modules (Phase 1)

| Module | Endpoint | Description |
|---|---|---|
| **Auth** | `/api/v1/auth/*` | Login, token refresh, user registration |
| **Crimes** | `/api/v1/crimes/*` | FIR registration with auto MO extraction |
| **Criminals** | `/api/v1/criminals/*` | Accused/suspect profiles and crime history |

### Coming in Phase 2–4

| Module | Endpoint | Intelligence |
|---|---|---|
| **Similarity** | `/api/v1/similarity/*` | Find behaviourally similar crimes |
| **Behaviour** | `/api/v1/behaviour/*` | Criminal behaviour profiles |
| **Network** | `/api/v1/network/*` | Criminal network graph (Neo4j) |
| **Geo** | `/api/v1/geo/*` | Crime hotspots (PostGIS + DBSCAN) |
| **Risk** | `/api/v1/risk/*` | Area risk scoring (XGBoost) |
| **Assistant** | `/api/v1/assistant/*` | NL query → investigation support (Ollama) |

---

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + Alembic
- **Database**: PostgreSQL 16 + pgvector (384-dim) + PostGIS
- **Graph**: Neo4j 5 Community
- **ML**: Sentence Transformers (all-MiniLM-L6-v2), scikit-learn, XGBoost
- **AI Assistant**: Ollama (Mistral) — local, no external APIs
- **Frontend**: React + TailwindCSS + Leaflet + React Flow
- **Infra**: Docker Compose

---

## Developer Notes

### Running migrations locally

```bash
cd backend
# Point to local postgres
DATABASE_URL_SYNC=postgresql+psycopg2://pac_user:pac_password@localhost:5432/pac_db \
  alembic upgrade head
```

### Creating new migration

```bash
docker exec pac_backend alembic revision --autogenerate -m "description"
```

### Resetting database

```bash
docker-compose down -v   # destroys all volumes
docker-compose up -d     # fresh start
docker exec pac_backend alembic upgrade head
docker exec pac_backend python scripts/seed_data.py
```

---

*PAC is designed for Karnataka State Police hackathon demonstration. All crime data is synthetic.*
