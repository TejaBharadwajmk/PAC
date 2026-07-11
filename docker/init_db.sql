-- PAC Database Bootstrap
-- Enables all required PostgreSQL extensions before Alembic migrations run

-- Vector similarity search (all-MiniLM-L6-v2 → 384-dim)
CREATE EXTENSION IF NOT EXISTS vector;

-- Geospatial queries (crime hotspots, spatial clustering)
CREATE EXTENSION IF NOT EXISTS postgis;

-- UUID primary key generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
