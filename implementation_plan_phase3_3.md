# Implementation Plan — PAC Phase 3.3: Criminal Behaviour Intelligence (Approved Version)

This document details the approved design and implementation roadmap for **Criminal Behaviour Intelligence (Phase 3.3)**.

---

## User Review Required

> [!NOTE]
> All behavioral calculations are fully offline, deterministic, and explainable. No LLMs or third-party APIs are utilized. The `detailed_metrics` field in the database uses a flexible JSONB format to prevent the need for future database schema migrations when extending scoring rules.

---

## Open Questions

None. The architectural decisions are finalized.

---

## Proposed Changes

### Database Layer

#### [MODIFY] [behaviour.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/models/behaviour.py)
Align `BehaviourProfile` model with the flexible read-model schema:
- **Columns to retain / map**:
  - `id` (UUID, PK)
  - `criminal_id` (UUID, FK, unique)
  - `risk_score` (Float)
  - `risk_level` (String)
  - `operating_radius_km` (Float)
  - `behaviour_consistency_score` (Float)
  - `serial_offender_probability` (Float)
  - `behaviour_confidence_score` (Float)
  - `profile_summary` (Text)
  - `generated_at` -> Map or rename to `last_generated_at` / `generated_at` (DateTime)
- **New Columns to add**:
  - `profile_version` (String, default="1.0")
  - `generated_from_crimes` (JSONB, default=list) — List of Crime IDs used to compile the profile.
  - `detailed_metrics` (JSONB, default=dict) — Houses all intermediate calculations, frequency distributions, trend progressions, network features, and explanation strings.

#### [NEW] [Alembic migration](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/alembic/versions/)
Create a migration to add `profile_version`, `generated_from_crimes`, and `detailed_metrics` to `behaviour_profiles`.

---

### Core Business Logic

#### [NEW] [behavior_engine.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/behavior_engine.py)
The core calculations module:
1. **CrimeDNA Aggregator**: Processes linked `Crime` & `CrimeDNA` rows.
2. **Frequency Analysis**: Computes total crimes, avg interval in days, and recurrence rate.
3. **Time Analysis**: Preferred hour of day, slots (morning, afternoon, evening, night), weekday vs. weekend bias, and seasonality.
4. **Geographic Analysis**: Preferred district, police station, operating radius (maximum distance between crime locations using coordinates), and participation in active hotspots.
5. **MO Analysis**: Aggregates planning levels, weapon usages, tools, escape patterns, and modus operandi tags.
6. **Network Enrichment**: Reads Neo4j metrics (co-offenders count, strongest associate, gang info).
7. **Scores Calculation**:
   - `violence_score`: Normalized metric based on weapon usage, crime severity, and violent offence types.
   - `gang_affiliation_score`: Ratio of offenses committed with known gang names or co-offenders.
   - `behaviour_consistency_score`: Entropy/consistency across time, location, and MO.
   - `escalation_trend`: Trend status (`Emerging`, `Stable`, `Declining`) based on chronological severity changes.
   - `serial_offender_probability`: Deterministic probability based on repeat history, consistency, and MO similarity.
   - `risk_score`: Combined metric mapping to `LOW` [0.0 - 0.35], `MEDIUM` [0.35 - 0.7], or `HIGH` [0.7 - 1.0].
8. **Explainability Block**: Populates the `detailed_metrics` JSON with `value`, `confidence`, `explanation`, and `supporting_evidence` for every major score.
9. **Summary Generator**: Dynamically formats a human-readable text profile.

#### [NEW] [behavior_repo.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/repositories/behavior_repo.py)
SQLAlchemy repository for `BehaviourProfile` table handling updates, reads, stats aggregation, and querying criminals by risk level, serial patterns, and repeat offenses.

#### [NEW] [behavior_service.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/behavior_service.py)
Coordinating service:
- Fetches all required information for a given `criminal_id`.
- Checks Neo4j database using `GraphService` or direct driver queries to get network analytics.
- Runs `BehaviorEngine` scoring.
- Saves or updates `BehaviourProfile` in PostgreSQL.

---

### Automatic Trigger Hooks

#### [MODIFY] [crime_service.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/crime_service.py)
Triggers automatic regeneration in a background task when a crime registration associates or dissociates a criminal.

#### [MODIFY] [dna_service.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/dna_service.py)
Triggers profile regeneration when `CrimeDNA` generation or updates finish.

#### [MODIFY] [graph_service.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/graph_service.py)
Triggers regeneration when Neo4j synchronization finishes (ensures network properties remain fresh).

---

### API Router & Schemas

#### [NEW] [behavior.py (schemas)](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/schemas/behavior.py)
Implement `BehaviourProfileResponse` conforming directly to the extensible structure:
```json
{
  "summary": "...",
  "scores": {},
  "patterns": {},
  "network": {},
  "geo": {},
  "evidence": [],
  "recommendations": [],
  "detailed_metrics": {
    "profile_summary": "...",
    "score_breakdown": {},
    "patterns": {},
    "timeline": {},
    "network_metrics": {},
    "geo_metrics": {},
    "confidence": {},
    "recommendations": {},
    "evidence": [
      "Committed 9 chain snatching crimes.",
      "87% occurred between 7 PM and 10 PM.",
      "Operating radius limited to 3.2 km.",
      "Associated with Gang X in 6 incidents."
    ]
  }
}
```

#### [NEW] [behavior.py (router)](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/api/v1/routers/behavior.py)
Endpoints:
- `GET /api/v1/behavior/criminal/{criminal_id}`
- `GET /api/v1/behavior/high-risk`
- `GET /api/v1/behavior/repeat-offenders`
- `GET /api/v1/behavior/serial-patterns`
- `GET /api/v1/behavior/statistics`
- `POST /api/v1/behavior/rebuild`

---

## Verification Plan

### Automated & Manual Tests
- Create `backend/scripts/test_behavior.py` covering:
  - Behavior engine calculations.
  - CRUD operations.
  - Endpoints and statistics.
- Create `backend/scripts/verify_behavior_e2e.py` for E2E validation:
  - Creating a synthetic pipeline (Crime -> DNA -> Neo4j -> Behaviour).
  - Asserting correct scores and explanations.
  - Wiping and rebuilding all behavior profiles.
