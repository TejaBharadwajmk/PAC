# Architecture Decision Record — PAC Crime DNA Pipeline

**Project**: PAC — PoliceIT Analytics Core  
**Phase**: 2.1 — Crime DNA Generation & Hybrid Similarity  
**Authors**: PAC Architecture Team  
**Status**: ACCEPTED  
**Date**: 2026-07-11  

---

## Context

PAC is a government-grade AI investigation intelligence platform for Karnataka State Police. It must:

- Run **offline** — no external SaaS APIs allowed (government data sovereignty)
- Remain **cost-zero** at inference time — no per-query pricing
- Handle **1,500+ existing records** growing to **50,000+ over 3 years**
- Be **explainable** — investigators must understand *why* two crimes are similar
- Be **maintainable** by a small engineering team without dedicated ML ops

These constraints drive every architecture decision in this document.

---

## ADR-001 — pgvector over Dedicated Vector Databases

### Status: ACCEPTED

### Context

Similarity search requires storing and querying 384-dimensional dense vectors. The alternatives considered were:

| Option | Type | Cost | Self-Hosted | Requires Extra Service |
| :--- | :--- | :--- | :--- | :--- |
| **pgvector** | PostgreSQL extension | Free | Yes | No |
| Pinecone | Managed SaaS | Per-query pricing | No | Yes (external) |
| Weaviate | Open-source vector DB | Free | Yes | Yes (new container) |
| Qdrant | Open-source vector DB | Free | Yes | Yes (new container) |
| ChromaDB | Embedded vector DB | Free | Yes | Yes (new service) |
| Milvus | Open-source vector DB | Free | Yes | Yes (new container + etcd) |

### Decision

**Use pgvector** — a PostgreSQL extension that adds `vector(N)` column types and approximate nearest-neighbour (ANN) index operators (`<=>` cosine, `<#>` inner product, `<->` L2).

### Rationale

**1. Co-location with existing data**
PAC already stores crimes, criminals, victims, and MO features in PostgreSQL. pgvector keeps the vector index *in the same database*, enabling powerful hybrid SQL+vector queries in a single round trip:

```sql
-- Single query: pre-filter by district + ANN cosine search
SELECT c.*, 1 - (d.embedding <=> :qvec) AS similarity
FROM crimes c JOIN crime_dna d ON c.id = d.crime_id
WHERE c.district = 'Bengaluru Urban'
  AND c.crime_type = 'house_break_in'
ORDER BY d.embedding <=> :qvec
LIMIT 10;
```

With an external vector DB, this requires two round trips: query the vector DB for IDs, then query PostgreSQL for metadata. Cross-service joins are slower and harder to maintain.

**2. PostGIS + pgvector in one engine**
Phase 3 requires spatial clustering (geo hotspots). PostGIS provides `ST_DWithin`, `ST_Cluster`, and GIST spatial indexes. A single PostgreSQL instance hosts both PostGIS (spatial intelligence) and pgvector (semantic intelligence) — no data duplication, no synchronisation logic.

**3. Zero additional infrastructure**
Adding Weaviate, Qdrant, or Milvus would add a new container, new failure mode, new backup strategy, and new operational knowledge requirement. For a government deployment with limited DevOps capacity, fewer moving parts is a hard requirement.

**4. Government data sovereignty**
Pinecone is a US-based SaaS. Karnataka Police FIR data cannot legally transit through external servers. pgvector keeps all data within the government's own infrastructure.

**5. IVFFlat index performance at our scale**
For 50,000 vectors at 384 dimensions, the `IVFFlat` index with `lists=√N ≈ 224` delivers sub-10ms ANN queries. We are nowhere near the scale (>1M vectors) where pgvector's approximate search quality degrades enough to justify a specialised engine.

### Consequences

- ✅ Single database, single backup, single connection pool
- ✅ Joins across crime metadata and vectors in one SQL statement
- ✅ PostGIS and pgvector share the same query planner
- ✅ Zero licensing cost, zero data egress
- ⚠️ IVFFlat requires `SET ivfflat.probes = N` tuning at query time for recall vs speed tradeoff
- ⚠️ For >1M vectors, HNSW index (pgvector ≥ 0.5.0) should replace IVFFlat — handled by a future migration

---

## ADR-002 — Crime DNA as a Read-Model / Intelligence Hub

### Status: ACCEPTED

### Context

The naive design stores `embedding` directly in the `crimes` table or in a thin `crime_dna(crime_id, embedding)` table. A better pattern treats `crime_dna` as a **denormalised read-model** — a precomputed, flat intelligence record per crime that aggregates data from multiple source tables.

### Decision

`crime_dna` is a **wide, denormalised intelligence hub** that duplicates fields from `crimes` and `crime_mo` to enable zero-join similarity queries.

### Architecture: Read-Model Pattern

```
Write Side (normalised)         Read Side (denormalised)
──────────────────────         ──────────────────────────
crimes           ──────────────┐
  └── crime_type               │  crime_dna (intelligence hub)
  └── district                 │    ├── embedding (vector)
  └── latitude/longitude       │    ├── crime_type ← denormalized
  └── occurred_at              │    ├── district ← denormalized
                               │    ├── hour_of_day ← computed
crime_mo         ──────────────┤    ├── is_night ← computed
  └── crime_method             │    ├── crime_method ← denormalized
  └── target_type              │    ├── target_type ← denormalized
  └── gang_involved            │    ├── gang_involved ← denormalized
  └── planning_level           │    └── status (PENDING→COMPLETED)
  └── escape_method            │
                               └── Generated once at registration
```

### Rationale

**1. Zero-join similarity queries**
Similarity search is the most frequent read operation. With denormalised fields in `crime_dna`, the hybrid search query requires zero joins beyond `crime_dna` itself. This is critical for ANN performance — joins after a vector scan defeat the IVFFlat index optimisation.

**2. Precomputed time intelligence**
`hour_of_day`, `day_of_week`, `is_night`, `time_of_day_slot`, and `month` are derived from `occurred_at` at write time. Computing them at query time on every similarity comparison would add per-row Python overhead. Storing them precomputed makes feature scoring a simple dict lookup.

**3. Status lifecycle without touching the crimes table**
The `status` column (PENDING → PROCESSING → COMPLETED → FAILED) lives in `crime_dna`, not in `crimes`. This keeps the investigation status of a crime (registered/under_investigation/solved) separate from the intelligence processing status. Neither table pollutes the other.

**4. Upstream source of truth for all downstream modules**

```
crime_dna (intelligence hub)
  ├── Phase 2: Similarity Engine reads embedding + structured features
  ├── Phase 3 (Geo): reads latitude/longitude + district for DBSCAN clustering
  ├── Phase 3 (Neo4j): reads crime_type + district for graph property enrichment
  ├── Phase 4 (Behaviour Profile): aggregates crime_dna per criminal's linked crimes
  └── Phase 4 (Risk Score): reads planning_level + gang_involved + crime_type as ML features
```

No schema change is needed in Phases 3–4. All intelligence fields are pre-populated in Phase 2.1.

**5. Reindexing without touching source data**
If the embedding model is upgraded (e.g., to a 768-dim model in Phase 4), only `crime_dna` records need updating. The `crimes` and `crime_mo` tables are unchanged.

### Consequences

- ✅ All similarity queries are single-table scans (fastest possible)
- ✅ Status tracking is isolated from business logic
- ✅ All downstream phases reuse without schema migrations
- ⚠️ `crime_dna` fields must be kept in sync if source data is updated (handled by the DNA service re-index endpoint)
- ⚠️ Slightly more storage per crime (~2KB for 384-dim vector + metadata fields)

---

## ADR-003 — Sentence Transformers (all-MiniLM-L6-v2)

### Status: ACCEPTED

### Context

Generating semantic embeddings from crime MO narratives requires a pre-trained language model. Options evaluated:

| Model | Dims | Size | Inference (CPU) | Licence | Offline |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **all-MiniLM-L6-v2** | 384 | 90MB | ~15ms/text | Apache 2.0 | ✅ |
| all-mpnet-base-v2 | 768 | 420MB | ~50ms/text | Apache 2.0 | ✅ |
| text-embedding-ada-002 | 1536 | SaaS | ~200ms/text | Proprietary | ❌ |
| paraphrase-multilingual | 768 | 1.1GB | ~80ms/text | Apache 2.0 | ✅ |
| BERT-base-uncased | 768 | 440MB | ~60ms/text | Apache 2.0 | ✅ |

### Decision

**Use `all-MiniLM-L6-v2`** from the `sentence-transformers` library, fine-tuned on 1 billion sentence pairs for semantic similarity tasks.

### Rationale

**1. Optimised specifically for semantic similarity**
`all-MiniLM-L6-v2` was trained with contrastive learning on sentence pair datasets (NLI, STS-B, SNLI, etc.) to produce embeddings where *semantically similar sentences are close in vector space*. BERT-base-uncased was not fine-tuned for this task — its embeddings cluster poorly for similarity search.

**2. Size and inference speed**
At 90MB and ~15ms CPU inference per sentence, it loads in 3–5 seconds at startup and processes one crime's MO text nearly instantly. On a standard government-issue server (4 vCPU, 8GB RAM), the ML Engine can embed ~60 texts per second without GPU.

**3. English MO narratives**
Karnataka Police FIRs in CCTNS are entered in English (transliterated Kannada occasionally). English-only models outperform multilingual models on English text because they dedicate all model capacity to one language. `all-MiniLM-L6-v2` benchmarks highest on STS-B among models under 100MB.

**4. 384 dimensions — storage and index efficiency**
768-dim models require double the storage and double the memory bandwidth for ANN searches. At 50,000 crimes: `50,000 × 384 × 4 bytes = 76MB` for the vector data — fits comfortably in PostgreSQL's shared buffer pool.

**5. Apache 2.0 licence**
Commercial-use-permitted, no restrictions on government deployment.

**6. Offline, no API key**
The model is downloaded once via `sentence-transformers` and cached locally. Inference requires zero network connectivity — mandatory for a police intelligence system.

### Consequences

- ✅ Best-in-class quality for a <100MB offline model
- ✅ ~15ms inference — embedding does not block crime registration
- ✅ 384 dims fits IVFFlat index with minimal recall loss
- ✅ Fully air-gappable for sensitive deployments
- ⚠️ English-only — if Kannada-script MO text becomes common, migrate to `paraphrase-multilingual-MiniLM-L12-v2` (same architecture, multilingual)
- ⚠️ 384 dims may be insufficient for very long MO narratives (>256 tokens truncated) — mitigated by MO extraction producing concise, structured text

---

## ADR-004 — FastAPI BackgroundTasks over Celery

### Status: ACCEPTED (for Phase 2; re-evaluate at Phase 4)

### Context

DNA generation is a background operation — it must not block the HTTP response. Options:

| Option | Complexity | Infrastructure | Durability | Retry | Best For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BackgroundTasks** | Minimal | None | None (in-process) | Manual | Low-volume, simple tasks |
| Celery + Redis | High | Redis broker | Persistent queue | Built-in | High-volume, distributed |
| Celery + RabbitMQ | High | RabbitMQ broker | Persistent queue | Built-in | Enterprise scale |
| ARQ (async Redis Queue) | Medium | Redis | Persistent | Built-in | Mid-volume, async |
| asyncio.create_task | Minimal | None | None | Manual | Single process |

### Decision

**Use FastAPI's built-in `BackgroundTasks`** for Phase 2, with manual retry logic (up to 3 attempts with exponential backoff) and `status=FAILED` fallback for observability.

### Rationale

**1. Zero additional infrastructure**
Celery requires a message broker (Redis or RabbitMQ) and at least one worker process. PAC already uses Redis for caching, but adding Celery means adding:
- `celery.py` app configuration
- `celery_worker` Docker service
- Task serialisation/deserialisation code
- Celery Beat for periodic retries
- Flower or similar for monitoring

For Phase 2 with 1,500 records and ~5 new crimes per day, this complexity is unjustified.

**2. Durability is handled by `status=PENDING` in the database**
The key risk with in-process background tasks is task loss on server crash. PAC mitigates this architecturally: every crime creates a `crime_dna` record with `status=PENDING` *before* the background task runs. A startup sweep (`reindex_pending_dna()`) can re-process any PENDING or FAILED records that survived a crash.

```python
# On startup: sweep and requeue any abandoned PENDING/FAILED records
async def reindex_pending_dna():
    crimes = await dna_repo.get_pending_and_failed()
    for crime in crimes:
        background_tasks.add_task(dna_service.generate, crime.id)
```

**3. Complexity budget**
A Celery setup adds ~500 lines of configuration, a new Docker service, and operational overhead. BackgroundTasks adds ~20 lines. For Phase 2, the simpler option delivers identical user-visible behaviour.

**4. Phase 4 migration path is clean**
When PAC scales to 500+ crimes/day (Phase 4 production), migrating from BackgroundTasks to ARQ or Celery requires changing only `dna_service.generate` to a task decorator. The `crime_dna.status` state machine remains identical — no schema migration needed.

### When to migrate to Celery
- Daily crime volume exceeds ~200 new crimes/day
- ML Engine requires GPU scheduling across multiple workers
- Phase 4 introduces long-running risk score batch jobs

### Consequences

- ✅ Zero new infrastructure in Phase 2
- ✅ Status tracking via DB makes the system crash-safe
- ✅ Simple to test, debug, and monitor
- ⚠️ Tasks lost on server restart (mitigated by startup PENDING sweep)
- ⚠️ Not suitable for high-concurrency bulk reindexing — add Celery then

---

## ADR-005 — Hybrid Similarity (Rules + Embeddings) over Embeddings Alone

### Status: ACCEPTED

### Context

The simplest similarity approach: embed the query text, run ANN search, return top-K results by cosine distance. Why not do this?

### Decision

**Use a three-phase hybrid pipeline**: SQL pre-filter → pgvector ANN → Python feature overlap scorer with explainability output.

### Rationale

**1. The embedding captures semantics, not all investigative signals**

Consider two crimes:
- Crime A: "Two accused on motorcycle snatched gold chain near bus stand at 8pm"
- Crime B: "Two accused on motorcycle snatched gold chain near school gate at 9am"

Embedding similarity: ~0.97 (almost identical narrative).
But Crime B happened in the morning, Crime A at night. For an investigator checking *temporal patterns*, this distinction matters. The feature scorer adds: `time_of_day_slot mismatch → -0.15 penalty`.

**2. Domain experts expect structured explanations**

A police investigator cannot act on "92% similar". They need:

> "Similar because: same forced_entry method, same residential target, both nighttime operations. Semantically 91% match — narratives describe nearly identical breaking-and-entering pattern."

The feature overlap scorer generates this explanation as a list of `matched_features` with a human-readable `explanation` string. Embeddings alone cannot produce this.

**3. Rule-based pre-filtering dramatically reduces ANN search space**

Without pre-filtering, a search for "house break-in using crowbar" would return similar robbery and burglary records — all narratively close, but different crime categories. Pre-filtering by `crime_type` reduces the candidate pool by ~80-90%, improving both precision and ANN speed.

**4. Hybrid scoring is tunable per investigator feedback**

$$\text{hybrid\_score} = 0.70 \times \text{semantic} + 0.30 \times \text{feature}$$

The weights (α, β) are configurable constants. If investigators find semantic similarity too dominant (returning lexically similar but operationally different crimes), raise β. If they find feature matching too rigid, raise α. No model retraining required.

**5. Cold-start resilience**
For crimes where `mo_text` is short (<20 words) or vague ("suspect robbed victim"), the embedding has low information content. The feature scorer compensates using structured MO features extracted by the rule engine — `crime_method`, `target_type`, `gang_involved` are always populated regardless of narrative length.

### Score Formula

$$\text{hybrid\_score} = 0.70 \times S_{\text{semantic}} + 0.30 \times S_{\text{feature}}$$

$$S_{\text{feature}} = 0.30 \cdot m_{\text{method}} + 0.25 \cdot m_{\text{target}} + 0.20 \cdot m_{\text{time}} + 0.15 \cdot m_{\text{gang}} + 0.10 \cdot m_{\text{escape}}$$

Where $m_i = 1$ if feature $i$ matches, else $0$.

### Consequences

- ✅ Explainable results — investigators see *why* two crimes match
- ✅ Precision improvement over embedding-only (eliminates false positives)
- ✅ Resilient to short/vague MO narratives
- ✅ Tunable weights without model retraining
- ⚠️ Slight added latency in Phase 3 (Python scoring loop over 50 candidates ~2ms)
- ⚠️ Feature matching is only as good as MO extraction quality

---

## ADR-006 — Scaling Path to All Intelligence Modules

### Status: ACCEPTED

### Architecture: How Phase 2.1 Feeds All Future Phases

```
crime_dna (intelligence hub)
│   embedding        → Phase 2: Similarity Search
│   crime_type       → Phase 2: Pre-filter
│   crime_method     → Phase 2: Feature scoring
│   target_type      → Phase 2: Feature scoring
│   gang_involved    → Phase 2: Feature scoring + Phase 4: Behaviour Profile
│   planning_level   → Phase 2: Feature scoring + Phase 4: Risk Score ML
│   latitude         → Phase 3: Geo DBSCAN clustering (no schema change)
│   longitude        → Phase 3: Geo DBSCAN clustering (no schema change)
│   district         → Phase 3: Neo4j Location node property (no schema change)
│   hour_of_day      → Phase 4: Risk Score ML feature (no schema change)
│   is_night         → Phase 4: Risk Score ML feature (no schema change)
│   month            → Phase 4: Seasonal risk pattern (no schema change)
└── crime_id         → Phase 3: Neo4j Crime node reference (no schema change)
```

### Phase 3: Geo Intelligence

```python
# DBSCAN geo clustering — reads lat/lon from crime_dna, no joins
SELECT latitude, longitude, crime_type, hour_of_day
FROM crime_dna
WHERE status = 'completed'
  AND district = :district
  AND crime_type = :crime_type
```

PostGIS `ST_ClusterDBSCAN` receives these coordinates directly. No new table, no schema change.

### Phase 3: Neo4j Integration

The graph sync service reads `crime_dna` to enrich Neo4j Crime nodes:

```python
# Graph node enrichment
MERGE (c:Crime {id: $crime_id})
SET c.crime_type = $crime_type,
    c.district   = $district,
    c.gang       = $gang_involved,
    c.embedding_ready = ($status == 'completed')
```

`crime_dna.embedding` is NOT sent to Neo4j (too large). Only metadata fields. Neo4j handles relationship traversals; pgvector handles semantic search. Neither needs the other.

### Phase 4: Behaviour Profile Generation

A criminal's behaviour profile is aggregated from the `crime_dna` records of all crimes they're linked to:

```python
# Read all crime_dna records for criminal's linked crimes
SELECT cd.crime_method, cd.target_type, cd.hour_of_day, cd.gang_involved,
       cd.planning_level, cd.district
FROM crime_dna cd
JOIN crime_criminals cc ON cd.crime_id = cc.crime_id
WHERE cc.criminal_id = :criminal_id
  AND cd.status = 'completed'
```

The `BehaviourProfileService` aggregates these rows into a frequency distribution — most common `crime_method`, preferred `hour_of_day`, preferred `district` — without touching the `crimes` or `crime_mo` tables.

### Phase 4: Risk Score (XGBoost)

The risk scoring model uses `crime_dna` fields as features:

| Feature | Source in crime_dna | Notes |
| :--- | :--- | :--- |
| `crime_type` encoded | `crime_type` | Label encoded |
| `planning_level` | `planning_level` | Ordinal: opportunistic=0, planned=1, highly_planned=2 |
| `gang_involved` | `gang_involved` | Binary |
| `hour_of_day` | `hour_of_day` | Numeric 0–23 |
| `is_night` | `is_night` | Binary |
| `day_of_week` | `day_of_week` | Cyclic encoded |
| `month` | `month` | Cyclic encoded |
| `district` encoded | `district` | Label encoded |

All features are already precomputed in `crime_dna`. The XGBoost model reads them directly — no feature engineering queries needed at inference time.

### Summary: Zero Schema Changes for Phases 3–4

| Future Phase | Uses crime_dna fields | Needs schema change? |
| :--- | :--- | :--- |
| Geo DBSCAN | `latitude`, `longitude`, `crime_type` | ❌ No |
| Geo Hotspot Map | `latitude`, `longitude`, `hour_of_day` | ❌ No |
| Neo4j Sync | `crime_type`, `district`, `gang_involved` | ❌ No |
| Behaviour Profile | All structured MO fields | ❌ No |
| Risk Score (XGBoost) | All time + MO fields | ❌ No |
| AI Assistant (RAG) | `embedding`, `mo_text_embedded` | ❌ No |

---

## Decision Summary

| # | Decision | Chosen | Alternatives Rejected |
|:--|:--|:--|:--|
| ADR-001 | Vector store | **pgvector** | Pinecone, Weaviate, Qdrant, Milvus |
| ADR-002 | DNA design | **Read-model hub** | Thin embedding table, inline in crimes |
| ADR-003 | Embedding model | **all-MiniLM-L6-v2** | ada-002, mpnet-base, BERT-base |
| ADR-004 | Async processing | **BackgroundTasks** | Celery, ARQ, asyncio.create_task |
| ADR-005 | Similarity | **Hybrid (rules + vectors)** | Embeddings-only, rules-only |
| ADR-006 | Scalability | **crime_dna as hub** | Per-phase schema evolution |

---

*This ADR is a living document. Update when architectural constraints change or when Phase 3+ implementation reveals new trade-offs.*
