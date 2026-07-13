# PAC Phase 3.2 — Criminal Network Intelligence (Neo4j) Implementation Plan

This implementation plan details the architecture, schemas, synchronization logic, and API endpoints required to build a Neo4j-powered criminal network analytics graph.

---

## User Review Required

> [!IMPORTANT]
> - **Neo4j Async Driver**: We will use the native Python `AsyncGraphDatabase.driver` to handle Neo4j sessions asynchronously. This integrates cleanly with FastAPI's event loop and avoids blocking network operations.
> - **Source of Truth**: PostgreSQL remains the source of truth. Neo4j is a read model optimized for graph analytics.
> - **Constraints & Indexes**: We will configure unique constraints on node IDs (`Crime.id`, `Criminal.id`, `Victim.id`, `Gang.name`, `PoliceStation.name`, `District.name`) at application startup to prevent duplicate node creation and speed up lookups.

---

## Open Questions

> [!NOTE]
> - **Co-Offender Association Logic**: When two criminals are linked to the same crime (co-offending), we will create a bidirectional `CRIMINAL_ASSOCIATED_WITH_CRIMINAL` relationship between them. Should we include the `crime_id` and `occurred_at` as properties on this relationship?
> - **Sync Scope**: Should updates to a crime (e.g. changing its status or updating its police station) trigger a delta-sync of the specific crime node and its local links in Neo4j, or should the sync service simply merge the nodes/relationships idempotently? (Idempotent MERGE is proposed as it is extremely robust and self-healing).

---

## Graph Model Specification

### Nodes & Labels
1. `(:Crime {id: String, fir_number: String, crime_type: String, severity: String, occurred_at: String})`
2. `(:Criminal {id: String, name: String, aliases: List, is_repeat_offender: Boolean})`
3. `(:Victim {id: String, name: String, gender: String, age: Integer})`
4. `(:Gang {name: String})`
5. `(:PoliceStation {name: String})`
6. `(:District {name: String})`

### Relationships
- `(Criminal)-[:CRIMINAL_COMMITTED_CRIME {role: String, is_arrested: Boolean}]->(Crime)`
- `(Criminal)-[:CRIMINAL_ASSOCIATED_WITH_CRIMINAL {crime_id: String}]->(Criminal)`
- `(Crime)-[:CRIME_OCCURRED_AT]->(District)`
- `(Crime)-[:UNDER_POLICE_STATION]->(PoliceStation)`
- `(Crime)-[:CRIME_TARGETED_VICTIM]->(Victim)`
- `(Criminal)-[:MEMBER_OF_GANG]->(Gang)`
- `(PoliceStation)-[:IN_DISTRICT]->(District)`
- `(Criminal)-[:IN_DISTRICT]->(District)`

---

## Proposed Changes

### Database & Configuration Layer

#### [NEW] [graph_db.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/graph_db.py)
Initializes the async Neo4j driver and exposes context managers to yield graph sessions. Ensures constraints are created on startup:
```cypher
CREATE CONSTRAINT crime_id_unique IF NOT EXISTS FOR (c:Crime) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT criminal_id_unique IF NOT EXISTS FOR (c:Criminal) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT victim_id_unique IF NOT EXISTS FOR (v:Victim) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT gang_name_unique IF NOT EXISTS FOR (g:Gang) REQUIRE g.name IS UNIQUE;
CREATE CONSTRAINT station_name_unique IF NOT EXISTS FOR (p:PoliceStation) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT district_name_unique IF NOT EXISTS FOR (d:District) REQUIRE d.name IS UNIQUE;
```

---

### Repository Layer

#### [NEW] [graph_repo.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/repositories/graph_repo.py)
Handles raw Cypher queries:
- **`sync_crime_node(...)`**: Idempotently merge a crime node and its associated links.
- **`sync_criminal_node(...)`**: Idempotently merge a criminal node and links.
- **`get_criminal_network(criminal_id, max_depth)`**: Fetch the criminal graph around an offender.
- **`get_shortest_path(criminal_id1, criminal_id2)`**: Runs Cypher shortestPath algorithm:
  ```cypher
  MATCH p = shortestPath((c1:Criminal {id: $id1})-[:CRIMINAL_ASSOCIATED_WITH_CRIMINAL|CRIMINAL_COMMITTED_CRIME*..5]-(c2:Criminal {id: $id2}))
  RETURN p;
  ```
- **`get_common_associates(criminal_id)`**: Finds co-offenders who share associates.
- **`get_gang_network(gang_name)`**: Fetches all gang members, their crimes, and their co-offenders.
- **`get_graph_statistics()`**: Fetches count of nodes by label and relationships by type.

---

### Service Layer

#### [NEW] [graph_service.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/services/graph_service.py)
Coordinates data retrieval from PostgreSQL and synchronization to Neo4j.
- **`sync_crime(crime_id)`**: Pulls the full crime ORM object (with relationships) from PostgreSQL and updates Neo4j.
- **`sync_criminal(criminal_id)`**: Pulls the criminal profile from PostgreSQL and updates Neo4j.
- **`rebuild_graph()`**: Scans PostgreSQL paginated batches of users, crimes, victims, criminals, and relationships, clears the Neo4j graph, and performs a complete rebuild.

---

### API Schemas

#### [NEW] [graph.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/schemas/graph.py)
Pydantic schemas:
- `NodeSchema` & `RelationshipSchema`: General JSON representations for front-end rendering.
- `GraphNetworkResponse`: Lists of nodes and links.
- `ShortestPathResponse`: Path details and distance.
- `GraphStatisticsResponse`: Counts of all nodes and relationships.

---

### API Routers

#### [NEW] [graph.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/api/v1/routers/graph.py)
Exposes endpoints:
- `POST /api/v1/graph/sync`
- `POST /api/v1/graph/rebuild`
- `GET /api/v1/graph/criminal/{criminal_id}`
- `GET /api/v1/graph/crime/{crime_id}`
- `GET /api/v1/graph/network/{criminal_id}`
- `GET /api/v1/graph/common-associates/{criminal_id}`
- `GET /api/v1/graph/gang/{gang_name}`
- `GET /api/v1/graph/shortest-path/{criminal1}/{criminal2}`
- `GET /api/v1/graph/statistics`

#### [MODIFY] [main.py](file:///c:/Users/Teja/OneDrive/Desktop/PAC/backend/app/main.py)
Register the `/api/v1/graph` router.

---

## Verification Plan

### Automated Tests
- Create a new test suite `backend/scripts/test_graph.py` to:
  - Mock Neo4j driver execution.
  - Test Cypher statement generation.
  - Test serialization of shortest path paths and network responses.

### Live Verification
- Perform a live full rebuild from the seeded database and assert matching node counts.
- Run shortest path queries between seeded co-offenders and verify the path output.
