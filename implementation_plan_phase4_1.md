# Implementation Plan — PAC Phase 4.1: AI Investigation Assistant (Final Architecture)

This document defines the implementation roadmap for the PAC AI Investigation Assistant. This phase orchestrates all existing intelligence modules into a conversational investigation assistant that produces evidence-backed, explainable answers for investigators.

---

## User Review Required

> [!IMPORTANT]
> - The assistant **never hallucinate**. Retrieval always comes before generation.
> - Every response cites PAC data sources. Unsupported conclusions are rejected by the validator.
> - Intent detection is deterministic first (keyword/rule matching); LLM fallback only if required.
> - No business logic is duplicated. The assistant only orchestrates existing PAC modules.

> [!NOTE]
> **LLM Provider**: The plan uses Google Gemini (`gemini-1.5-flash`) as the default provider via `google-generativeai`. The provider layer is designed behind a `BaseLLM` interface so that Ollama, OpenAI, or a mock can replace it without changing the assistant logic.

---

## Open Questions

None. Architecture and supported intents are clearly defined.

---

## Architecture Pipeline

```
User Question
     ↓
Intent Classifier (deterministic rules → LLM fallback)
     ↓
Retriever Orchestrator (selects and calls PAC modules)
     ↓
Context Builder (structures results into JSON context)
     ↓
Prompt Builder (injects context into grounded system prompt)
     ↓
LLM Provider (Gemini / OpenAI / Ollama / Mock)
     ↓
Response Validator (checks citations, evidence, grounding)
     ↓
Final Structured Response
```

---

## Proposed Changes

### Core Engine Components

---

#### [NEW] [assistant_engine.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/assistant_engine.py)

Coordinates the full pipeline: intent → retrieval → context → prompt → LLM → validation → response.

**Supported Intents:**

| Intent | Example Query |
|--------|--------------|
| `similarity_search` | "Show crimes similar to FIR 2026-451" |
| `criminal_profile` | "Explain this criminal's behaviour" |
| `criminal_network` | "Show strongest associates" |
| `hotspot_analysis` | "Which hotspots are growing?" |
| `district_analysis` | "Crime trends in Mysuru last month" |
| `gang_analysis` | "Which gangs are active in Whitefield?" |
| `risk_prediction` | "Why is this criminal High Risk?" |
| `investigation_summary` | "Generate investigation briefing for FIR 2026-451" |
| `patrol_recommendation` | "What patrols do we need in Koramangala?" |
| `compare_entities` | "Compare Criminal A and Criminal B" |
| `unknown` | Graceful fallback |

---

#### [NEW] [retriever_service.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/retriever_service.py)

**Responsibilities:**
- Based on the detected intent, selects and calls the appropriate PAC modules.
- Gathers data from:
  - `CrimeDNA` / `SimilarityService` for similar cases
  - `GeoService` for hotspot data
  - `BehaviorService` for criminal behaviour profiles
  - `PredictionService` for risk forecasts and district indexes
  - `GraphService` / Neo4j for criminal networks, gangs, associates
- Combines all retrieved data into one clean context dict.

---

#### [NEW] [context_builder.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/context_builder.py)

Converts raw retrieved data into a structured context ready for prompt injection:
```json
{
  "crime_summary": {},
  "similar_cases": [],
  "behavior": {},
  "network": {},
  "geo": {},
  "prediction": {},
  "evidence": []
}
```
Never passes raw ORM rows to the LLM. All data is sanitised and structured first.

---

#### [NEW] [prompt_builder.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/prompt_builder.py)

Constructs the system and user prompts:
- Instructs the model to **never invent facts**.
- Instructs the model to use **only the supplied PAC context**.
- Explicitly asks for **reasoning explanation** and **evidence citations**.
- Instructs the model to flag **uncertainty** where data is incomplete.
- Uses concise, **investigator-friendly language** rather than generic chat language.

---

#### [NEW] [llm_provider.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/llm_provider.py)

Interface-based LLM layer:

```
BaseLLM (abstract)
  ├── GeminiProvider     # Default: google-generativeai (gemini-1.5-flash)
  ├── OpenAIProvider     # Optional
  ├── OllamaProvider     # Offline/local option
  └── MockProvider       # For unit tests
```

The `generate()` method signature is identical across all providers, allowing future replacement with no API changes.

---

#### [NEW] [response_validator.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/response_validator.py)

Validates every LLM response before it reaches the investigator:
- Checks that every claim is supported by the retrieved context.
- Ensures no unsupported entities (names, case numbers, locations) are introduced.
- Verifies confidence score presence.
- If validation fails → returns `"Insufficient evidence available."`

---

### Conversation Memory

**In-session memory via `ConversationSession`** (stored in-process dict, keyed by session ID):
- Tracks entity context: last referenced criminal, crime, district, gang.
- Resolves pronouns and references: `"his associates"` → last mentioned criminal.
- No persistent session storage required (session lives for the HTTP connection lifetime).

---

### API Layer

#### [NEW] [assistant.py (router)](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/api/v1/routers/assistant.py)

Endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/assistant/chat` | General investigation query with conversation memory |
| `POST` | `/api/v1/assistant/investigation-summary` | Structured briefing for a crime/FIR |
| `POST` | `/api/v1/assistant/patrol-briefing` | Patrol recommendations for a district |
| `POST` | `/api/v1/assistant/crime-summary` | Analytical summary for a specific crime |
| `POST` | `/api/v1/assistant/criminal-summary` | Full profile brief for a specific criminal |
| `GET` | `/api/v1/assistant/health` | LLM provider health check |

#### [NEW] [assistant.py (schemas)](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/schemas/assistant.py)

**Response format for every endpoint:**
```json
{
  "answer": "...",
  "confidence": 0.91,
  "sources": ["Crime DNA", "Behavior Intelligence", "Neo4j", "Geo Intelligence"],
  "evidence": ["...", "...", "..."],
  "recommendations": ["...", "...", "..."],
  "follow_up_questions": ["...", "...", "..."]
}
```

Register the router in [main.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/main.py).

---

### Environment Configuration

Add the following to the `.env` and `Settings` model:
- `GEMINI_API_KEY` — Gemini API key for production use.
- `LLM_PROVIDER` — Controls which provider is loaded (`gemini` | `openai` | `ollama` | `mock`). Default: `gemini`.
- `LLM_MODEL_NAME` — e.g., `gemini-1.5-flash`.

---

### Dependencies

Add to `requirements.txt`:
- `google-generativeai` — Gemini Python SDK.

---

## Verification Plan

### Automated Tests
- Create `backend/scripts/test_assistant.py`:
  - Intent detection accuracy for 11 intent categories.
  - Context builder output structure validation.
  - Prompt builder grounding instruction verification.
  - Response validator rejection of hallucinated content.
  - API endpoint response schema validation (using `MockProvider`).

### End-to-End Tests
- Create `backend/scripts/verify_assistant_e2e.py`:
  - Full pipeline: `User Query → Intent → Retrieval → Context → Prompt → LLM (Mock) → Validation → Final Answer`.
  - Multi-turn conversation: entity reference resolution across follow-up questions.
  - Benchmark: retrieval latency, context construction, LLM latency, total response time.
  - Docker compatibility verified inside `pac_backend` container.
