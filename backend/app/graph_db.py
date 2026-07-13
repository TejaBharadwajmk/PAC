"""
PAC Backend — Neo4j Database Connection & Session Factory
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from neo4j import AsyncGraphDatabase, AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

# Global driver singleton
_driver = None


def get_neo4j_driver():
    """Retrieve or initialize the thread-safe async Neo4j driver singleton."""
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
        )
    return _driver


async def close_neo4j() -> None:
    """Closes the active Neo4j driver connection pool."""
    global _driver
    if _driver is not None:
        await _driver.close()
        logger.info("Neo4j connection pool closed successfully.")
        _driver = None


@asynccontextmanager
async def get_graph_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a Neo4j database session."""
    driver = get_neo4j_driver()
    async with driver.session() as session:
        yield session


async def get_neo4j_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a Neo4j database session."""
    driver = get_neo4j_driver()
    async with driver.session() as session:
        yield session


async def init_neo4j() -> None:
    """Checks Neo4j database connection and initializes constraints on startup."""
    logger.info("Initializing Neo4j Graph Database...")
    driver = get_neo4j_driver()
    try:
        await driver.verify_connectivity()
        logger.info("Successfully connected to Neo4j cluster.")

        # Set up schema constraints
        async with driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT crime_id_unique IF NOT EXISTS FOR (c:Crime) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT criminal_id_unique IF NOT EXISTS FOR (c:Criminal) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT victim_id_unique IF NOT EXISTS FOR (v:Victim) REQUIRE v.id IS UNIQUE",
                "CREATE CONSTRAINT gang_name_unique IF NOT EXISTS FOR (g:Gang) REQUIRE g.name IS UNIQUE",
                "CREATE CONSTRAINT station_name_unique IF NOT EXISTS FOR (p:PoliceStation) REQUIRE p.name IS UNIQUE",
                "CREATE CONSTRAINT district_name_unique IF NOT EXISTS FOR (d:District) REQUIRE d.name IS UNIQUE",
            ]
            for stmt in constraints:
                await session.run(stmt)
            logger.info("Neo4j database unique ID constraints initialized.")
    except Exception as exc:
        logger.critical(f"Neo4j database initialization failed: {exc}")
        # Note: Do not raise/crash here to allow backend startup even if Neo4j is offline (e.g. offline migrations)
