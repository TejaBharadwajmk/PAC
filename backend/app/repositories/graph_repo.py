"""
PAC — Neo4j Graph Database Repository
"""

import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from neo4j import AsyncSession

logger = logging.getLogger(__name__)


class GraphRepository:
    """Encapsulates all raw Cypher queries for Neo4j Criminal Network Intelligence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def clear_graph(self) -> None:
        """Deletes all nodes and relationships in the graph."""
        logger.warning("Wiping Neo4j Graph Database...")
        await self.session.run("MATCH (n) DETACH DELETE n")

    async def sync_crime_nodes_batch(self, batch: List[Dict[str, Any]]) -> None:
        """
        Idempotently merges a batch of Crime, PoliceStation, District, and Victim nodes,
        and sets up their containment/location relationships.
        """
        if not batch:
            return

        query = """
        UNWIND $batch AS row
        MERGE (c:Crime {id: row.id})
        SET c.fir_number = row.fir_number,
            c.crime_type = row.crime_type,
            c.severity = row.severity,
            c.occurred_at = row.occurred_at,
            c.dna_status = row.dna_status,
            c.similarity_ready = row.similarity_ready,
            c.district = row.district,
            c.police_station = row.police_station

        MERGE (d:District {name: row.district})
        MERGE (c)-[:CRIME_OCCURRED_AT]->(d)

        MERGE (p:PoliceStation {name: row.police_station})
        MERGE (c)-[:UNDER_POLICE_STATION]->(p)
        MERGE (p)-[:IN_DISTRICT]->(d)

        FOREACH (v_row IN row.victims |
            MERGE (v:Victim {id: v_row.id})
            SET v.name = v_row.name,
                v.gender = v_row.gender,
                v.age = v_row.age
            MERGE (c)-[:CRIME_TARGETED_VICTIM]->(v)
        )
        """
        await self.session.run(query, {"batch": batch})

    async def sync_criminal_nodes_batch(self, batch: List[Dict[str, Any]]) -> None:
        """
        Idempotently merges a batch of Criminal and Gang nodes, and sets up
        the gang member and district relationships.
        """
        if not batch:
            return

        query = """
        UNWIND $batch AS row
        MERGE (cr:Criminal {id: row.id})
        SET cr.name = row.name,
            cr.is_repeat_offender = row.is_repeat_offender,
            cr.risk_score = row.risk_score,
            cr.primary_crime_type = row.primary_crime_type,
            cr.known_aliases = row.known_aliases

        FOREACH (dist IN CASE WHEN row.district IS NOT NULL AND row.district <> '' THEN [row.district] ELSE [] END |
            MERGE (d:District {name: dist})
            MERGE (cr)-[:IN_DISTRICT]->(d)
        )

        FOREACH (g_name IN CASE WHEN row.gang_name IS NOT NULL AND row.gang_name <> '' THEN [row.gang_name] ELSE [] END |
            MERGE (g:Gang {name: g_name})
            MERGE (cr)-[:MEMBER_OF_GANG]->(g)
        )
        """
        await self.session.run(query, {"batch": batch})

    async def sync_crime_criminals_batch(self, batch: List[Dict[str, Any]]) -> None:
        """
        Idempotently links Criminals to Crimes they committed, and dynamically
        calculates co-offending relationships (associates) with strength/timeline tracking.
        """
        if not batch:
            return

        # 1. Merge committed links
        commit_query = """
        UNWIND $batch AS row
        MATCH (cr:Criminal {id: row.criminal_id})
        MATCH (c:Crime {id: row.crime_id})
        MERGE (cr)-[rel:CRIMINAL_COMMITTED_CRIME]->(c)
        SET rel.role = row.role,
            rel.is_arrested = row.is_arrested
        """
        await self.session.run(commit_query, {"batch": batch})

        # 2. Extract crime IDs to compute co-offences
        crime_ids = list({row["crime_id"] for row in batch})
        
        # 3. Dynamic co-offending linkage and calculation of strengths
        cooffence_query = """
        MATCH (c1:Criminal)-[r1:CRIMINAL_COMMITTED_CRIME]->(crime:Crime)<-[r2:CRIMINAL_COMMITTED_CRIME]->(c2:Criminal)
        WHERE crime.id IN $crime_ids AND c1.id < c2.id
        
        MERGE (c1)-[assoc:CRIMINAL_ASSOCIATED_WITH_CRIMINAL]-(c2)
        
        WITH c1, c2, assoc, crime
        ORDER BY crime.occurred_at ASC
        
        WITH c1, c2, assoc, collect(crime) AS shared_crimes
        WITH c1, c2, assoc, shared_crimes, shared_crimes[0] AS first_crime, shared_crimes[size(shared_crimes)-1] AS last_crime
        
        SET assoc.times_seen_together = size(shared_crimes),
            assoc.association_strength = toFloat(size(shared_crimes)),
            assoc.first_seen = first_crime.occurred_at,
            assoc.last_seen = last_crime.occurred_at,
            assoc.crime_id = last_crime.id,
            assoc.occurred_at = last_crime.occurred_at
        """
        await self.session.run(cooffence_query, {"crime_ids": crime_ids})

    async def update_gang_summaries(self) -> None:
        """Updates member count, active districts, and crime types across all Gang nodes."""
        query = """
        MATCH (g:Gang)<-[:MEMBER_OF_GANG]-(c:Criminal)
        OPTIONAL MATCH (c)-[:CRIMINAL_COMMITTED_CRIME]->(cr:Crime)
        WITH g, count(DISTINCT c) AS m_count, collect(DISTINCT cr.district) AS districts, collect(DISTINCT cr.crime_type) AS crime_types
        SET g.member_count = m_count,
            g.active_districts = [d IN districts WHERE d IS NOT NULL],
            g.known_crime_types = [t IN crime_types WHERE t IS NOT NULL]
        """
        await self.session.run(query)

    async def get_node_by_label_and_id(self, label: str, id_value: str) -> Optional[Dict[str, Any]]:
        """Fetches properties of a single node in Neo4j."""
        query = f"MATCH (n:{label} {{id: $id_value}}) RETURN n"
        result = await self.session.run(query, {"id_value": id_value})
        record = await result.single()
        if not record:
            return None
        node = record["n"]
        return {
            "id": node["id"],
            "label": list(node.labels)[0] if node.labels else label,
            "properties": dict(node)
        }

    async def get_criminal_network(self, criminal_id: str, max_depth: int = 2) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Traverses nodes connected to a starting criminal up to max_depth.
        Returns serialized (nodes, relationships) matching GraphNetworkResponse schema.
        """
        query = f"""
        MATCH (c:Criminal {{id: $criminal_id}})
        MATCH path = (c)-[*..{max_depth}]-(target)
        RETURN path
        """
        result = await self.session.run(query, {"criminal_id": criminal_id})
        
        nodes_map = {}
        relationships_list = []
        relationships_seen = set()

        async for record in result:
            path = record["path"]
            for node in path.nodes:
                n_id = node.get("id") or node.get("name")
                if n_id and n_id not in nodes_map:
                    nodes_map[n_id] = {
                        "id": str(n_id),
                        "label": list(node.labels)[0] if node.labels else "Unknown",
                        "properties": dict(node)
                    }
            for rel in path.relationships:
                start_node = rel.nodes[0]
                end_node = rel.nodes[1]
                s_id = str(start_node.get("id") or start_node.get("name"))
                t_id = str(end_node.get("id") or end_node.get("name"))
                
                # Create a stable identifier for relationship to prevent duplicates
                rel_key = f"{s_id}-{t_id}-{rel.type}-{dict(rel)}"
                if rel_key not in relationships_seen:
                    relationships_seen.add(rel_key)
                    relationships_list.append({
                        "source": s_id,
                        "target": t_id,
                        "type": rel.type,
                        "properties": dict(rel)
                    })

        # Ensure starting node is included even if it has no links
        if criminal_id not in nodes_map:
            start_node = await self.get_node_by_label_and_id("Criminal", criminal_id)
            if start_node:
                nodes_map[criminal_id] = start_node

        return list(nodes_map.values()), relationships_list

    async def get_shortest_path(self, criminal_id1: str, criminal_id2: str) -> Optional[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]]:
        """
        Finds the shortest co-offending path between two criminals in the graph.
        Returns (nodes, relationships, distance) or None if no path exists.
        """
        query = """
        MATCH (c1:Criminal {id: $id1})
        MATCH (c2:Criminal {id: $id2})
        MATCH path = shortestPath((c1)-[:CRIMINAL_ASSOCIATED_WITH_CRIMINAL|CRIMINAL_COMMITTED_CRIME*..5]-(c2))
        RETURN path
        """
        result = await self.session.run(query, {"id1": criminal_id1, "id2": criminal_id2})
        record = await result.single()
        if not record or not record["path"]:
            return None

        path = record["path"]
        nodes_list = []
        relationships_list = []
        
        for node in path.nodes:
            n_id = str(node.get("id") or node.get("name"))
            nodes_list.append({
                "id": n_id,
                "label": list(node.labels)[0] if node.labels else "Unknown",
                "properties": dict(node)
            })
            
        for rel in path.relationships:
            start_node = rel.nodes[0]
            end_node = rel.nodes[1]
            s_id = str(start_node.get("id") or start_node.get("name"))
            t_id = str(end_node.get("id") or end_node.get("name"))
            relationships_list.append({
                "source": s_id,
                "target": t_id,
                "type": rel.type,
                "properties": dict(rel)
            })

        return nodes_list, relationships_list, len(relationships_list)

    async def get_common_associates(self, criminal_id: str) -> List[Dict[str, Any]]:
        """
        Finds criminals sharing co-offending associates with the given criminal.
        Returns a sorted list of potential co-offenders and their shared associate counts.
        """
        query = """
        MATCH (c:Criminal {id: $criminal_id})-[:CRIMINAL_ASSOCIATED_WITH_CRIMINAL]-(assoc:Criminal)-[:CRIMINAL_ASSOCIATED_WITH_CRIMINAL]-(other:Criminal)
        WHERE other.id <> $criminal_id AND NOT (c)-[:CRIMINAL_ASSOCIATED_WITH_CRIMINAL]-(other)
        RETURN other, collect(assoc.name) AS shared_associates, count(assoc) AS shared_count
        ORDER BY shared_count DESC
        LIMIT 10
        """
        result = await self.session.run(query, {"criminal_id": criminal_id})
        
        associates = []
        async for row in result:
            other_node = row["other"]
            associates.append({
                "criminal_id": other_node["id"],
                "name": other_node["name"],
                "shared_associates": row["shared_associates"],
                "shared_count": row["shared_count"],
                "risk_score": other_node.get("risk_score", 0.0),
                "primary_crime_type": other_node.get("primary_crime_type", "unknown")
            })
        return associates

    async def get_gang_network(self, gang_name: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Traverses the network of all members belonging to a gang, their crimes,
        and co-offenders up to 2 hops.
        """
        query = """
        MATCH (g:Gang {name: $gang_name})
        MATCH path = (g)<-[:MEMBER_OF_GANG]-(c:Criminal)-[*..2]-(target)
        RETURN path
        """
        result = await self.session.run(query, {"gang_name": gang_name})
        
        nodes_map = {}
        relationships_list = []
        relationships_seen = set()

        async for record in result:
            path = record["path"]
            for node in path.nodes:
                n_id = node.get("id") or node.get("name")
                if n_id and n_id not in nodes_map:
                    nodes_map[n_id] = {
                        "id": str(n_id),
                        "label": list(node.labels)[0] if node.labels else "Unknown",
                        "properties": dict(node)
                    }
            for rel in path.relationships:
                start_node = rel.nodes[0]
                end_node = rel.nodes[1]
                s_id = str(start_node.get("id") or start_node.get("name"))
                t_id = str(end_node.get("id") or end_node.get("name"))
                
                rel_key = f"{s_id}-{t_id}-{rel.type}-{dict(rel)}"
                if rel_key not in relationships_seen:
                    relationships_seen.add(rel_key)
                    relationships_list.append({
                        "source": s_id,
                        "target": t_id,
                        "type": rel.type,
                        "properties": dict(rel)
                    })

        # Ensure the Gang node is in the map even if it has no members
        if gang_name not in nodes_map:
            nodes_map[gang_name] = {
                "id": gang_name,
                "label": "Gang",
                "properties": {"name": gang_name}
            }

        return list(nodes_map.values()), relationships_list

    async def get_gang_members(self, gang_name: str) -> List[Dict[str, Any]]:
        """Fetch a flat list of criminal members of a gang for AI assistant retrieval."""
        query = """
        MATCH (g:Gang {name: $gang_name})<-[:MEMBER_OF_GANG]-(c:Criminal)
        RETURN c.id AS id, c.name AS name, c.risk_score AS risk_score,
               c.primary_crime_type AS primary_crime_type,
               c.is_repeat_offender AS is_repeat_offender
        ORDER BY c.risk_score DESC
        LIMIT 20
        """
        result = await self.session.run(query, {"gang_name": gang_name})
        members = []
        async for row in result:
            members.append({
                "criminal_id": row["id"],
                "name": row["name"],
                "risk_score": row["risk_score"],
                "primary_crime_type": row["primary_crime_type"],
                "is_repeat_offender": row["is_repeat_offender"],
            })
        return members

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Returns node count summary by label and relationship count summary by type."""
        # 1. Node statistics
        nodes_query = "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS node_count"
        nodes_res = await self.session.run(nodes_query)
        
        node_counts = {}
        async for row in nodes_res:
            label = row["label"] or "Unlabeled"
            node_counts[label] = row["node_count"]

        # 2. Relationship statistics
        rels_query = "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS rel_count"
        rels_res = await self.session.run(rels_query)
        
        relationship_counts = {}
        async for row in rels_res:
            rel_type = row["rel_type"]
            relationship_counts[rel_type] = row["rel_count"]

        return {
            "node_counts": node_counts,
            "relationship_counts": relationship_counts
        }
