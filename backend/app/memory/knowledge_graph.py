"""
ALAS Semantic Knowledge Graph (L2) — NetworkX-backed persistent graph.

Stores entities (people, concepts, skills, goals, events) and their
relationships extracted from conversations. Provides graph queries
for context enrichment during LLM inference.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import networkx as nx

from backend.app.config import get_settings

logger = logging.getLogger("alas.memory.knowledge_graph")


class KnowledgeGraph:
    """
    Layer 2 — Semantic Knowledge Graph.

    Maintains a persistent directed graph of entities and
    relationships extracted from user conversations. Supports
    graph queries, path finding, and context enrichment.
    """

    # Supported entity types
    ENTITY_TYPES = {"person", "concept", "skill", "goal", "event", "topic", "place", "preference"}

    # Supported relationship types
    RELATION_TYPES = {
        "knows_about", "interested_in", "related_to", "mentioned_by",
        "caused_by", "precedes", "part_of", "works_on", "prefers",
        "learned_from", "associated_with", "opposes",
    }

    def __init__(self):
        settings = get_settings()
        self._graph = nx.DiGraph()
        self._persist_path = Path(settings.chroma_persist_dir).parent / "knowledge_graph.json"
        self._load()

    def _load(self):
        """Load the graph from disk if it exists."""
        if self._persist_path.exists():
            try:
                with open(self._persist_path, "r") as f:
                    data = json.load(f)
                self._graph = nx.node_link_graph(data, directed=True)
                logger.info(f"Knowledge graph loaded: {self._graph.number_of_nodes()} nodes, {self._graph.number_of_edges()} edges")
            except Exception as e:
                logger.warning(f"Failed to load knowledge graph: {e}. Starting fresh.")
                self._graph = nx.DiGraph()
        else:
            logger.info("No existing knowledge graph found. Starting fresh.")

    def _save(self):
        """Persist the graph to disk."""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = nx.node_link_data(self._graph)
            with open(self._persist_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save knowledge graph: {e}")

    def add_entity(
        self,
        name: str,
        entity_type: str = "concept",
        properties: Optional[dict] = None,
        source: str = "conversation",
    ) -> str:
        """
        Add or update an entity node in the graph.

        Args:
            name: Entity name (used as node ID after normalization).
            entity_type: One of ENTITY_TYPES.
            properties: Additional properties dict.
            source: How this entity was learned.

        Returns:
            The normalized node ID.
        """
        node_id = self._normalize(name)
        now = datetime.now(timezone.utc).isoformat()

        if self._graph.has_node(node_id):
            # Update existing — increment mention count
            node = self._graph.nodes[node_id]
            node["mention_count"] = node.get("mention_count", 1) + 1
            node["last_seen"] = now
            if properties:
                node.setdefault("properties", {}).update(properties)
        else:
            # Create new
            self._graph.add_node(
                node_id,
                label=name,
                type=entity_type if entity_type in self.ENTITY_TYPES else "concept",
                created_at=now,
                last_seen=now,
                mention_count=1,
                source=source,
                properties=properties or {},
            )

        self._save()
        return node_id

    def add_relationship(
        self,
        source_name: str,
        target_name: str,
        relation: str = "related_to",
        weight: float = 1.0,
        context: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Add or strengthen a relationship between two entities.

        Args:
            source_name: Source entity name.
            target_name: Target entity name.
            relation: Relationship type.
            weight: Relationship strength (0-1).
            context: Conversation context where this was learned.

        Returns:
            Tuple of (source_id, target_id).
        """
        src_id = self._normalize(source_name)
        tgt_id = self._normalize(target_name)
        now = datetime.now(timezone.utc).isoformat()

        # Ensure both nodes exist
        if not self._graph.has_node(src_id):
            self.add_entity(source_name)
        if not self._graph.has_node(tgt_id):
            self.add_entity(target_name)

        if self._graph.has_edge(src_id, tgt_id):
            # Strengthen existing relationship
            edge = self._graph.edges[src_id, tgt_id]
            edge["weight"] = min(1.0, edge.get("weight", 0.5) + 0.1)
            edge["reinforced_count"] = edge.get("reinforced_count", 1) + 1
            edge["last_reinforced"] = now
        else:
            # Create new relationship
            rel = relation if relation in self.RELATION_TYPES else "related_to"
            self._graph.add_edge(
                src_id,
                tgt_id,
                relation=rel,
                weight=weight,
                created_at=now,
                last_reinforced=now,
                reinforced_count=1,
                context=context or "",
            )

        self._save()
        return src_id, tgt_id

    def query_entity(self, name: str) -> Optional[dict]:
        """Get full information about an entity and its connections."""
        node_id = self._normalize(name)
        if not self._graph.has_node(node_id):
            return None

        node_data = dict(self._graph.nodes[node_id])

        # Get relationships
        outgoing = []
        for _, target, data in self._graph.out_edges(node_id, data=True):
            target_label = self._graph.nodes[target].get("label", target)
            outgoing.append({
                "target": target_label,
                "relation": data.get("relation", "related_to"),
                "weight": data.get("weight", 0.5),
            })

        incoming = []
        for source, _, data in self._graph.in_edges(node_id, data=True):
            source_label = self._graph.nodes[source].get("label", source)
            incoming.append({
                "source": source_label,
                "relation": data.get("relation", "related_to"),
                "weight": data.get("weight", 0.5),
            })

        return {
            "id": node_id,
            **node_data,
            "outgoing_relations": outgoing,
            "incoming_relations": incoming,
        }

    def query_related(self, name: str, max_depth: int = 2, limit: int = 20) -> list[dict]:
        """
        Find entities related to the given entity within N hops.

        Args:
            name: Starting entity name.
            max_depth: Maximum graph traversal depth.
            limit: Maximum results.

        Returns:
            List of related entities with path info.
        """
        node_id = self._normalize(name)
        if not self._graph.has_node(node_id):
            return []

        related = []
        visited = {node_id}

        # BFS traversal
        queue = [(node_id, 0)]
        while queue and len(related) < limit:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for neighbor in list(self._graph.successors(current)) + list(self._graph.predecessors(current)):
                if neighbor not in visited:
                    visited.add(neighbor)
                    node_data = dict(self._graph.nodes[neighbor])
                    edge_data = self._graph.edges.get((current, neighbor), self._graph.edges.get((neighbor, current), {}))
                    related.append({
                        "id": neighbor,
                        "label": node_data.get("label", neighbor),
                        "type": node_data.get("type", "concept"),
                        "relation": edge_data.get("relation", "related_to"),
                        "depth": depth + 1,
                        "mention_count": node_data.get("mention_count", 0),
                    })
                    queue.append((neighbor, depth + 1))

        # Sort by mention count (most referenced first)
        related.sort(key=lambda x: x.get("mention_count", 0), reverse=True)
        return related[:limit]

    def search(self, query: str, entity_type: Optional[str] = None, limit: int = 10) -> list[dict]:
        """
        Search entities by name substring match.

        Args:
            query: Search string.
            entity_type: Filter by entity type.
            limit: Maximum results.

        Returns:
            List of matching entities.
        """
        query_lower = query.lower()
        results = []

        for node_id, data in self._graph.nodes(data=True):
            label = data.get("label", node_id).lower()
            if query_lower in label or query_lower in node_id:
                if entity_type and data.get("type") != entity_type:
                    continue
                results.append({
                    "id": node_id,
                    "label": data.get("label", node_id),
                    "type": data.get("type", "concept"),
                    "mention_count": data.get("mention_count", 0),
                })

        results.sort(key=lambda x: x.get("mention_count", 0), reverse=True)
        return results[:limit]

    def get_context_for_query(self, query: str, limit: int = 5) -> str:
        """
        Generate a context string from the knowledge graph for LLM prompt.

        Searches for relevant entities and formats their relationships
        into a readable context block.
        """
        matches = self.search(query, limit=limit)
        if not matches:
            return ""

        parts = ["--- Knowledge Graph Context ---"]
        for match in matches:
            entity = self.query_entity(match["label"])
            if not entity:
                continue

            line = f"• {entity['label']} ({entity.get('type', 'concept')})"
            relations = entity.get("outgoing_relations", [])
            if relations:
                rel_strs = [f"{r['relation']} → {r['target']}" for r in relations[:5]]
                line += f" [{', '.join(rel_strs)}]"
            parts.append(line)

        return "\n".join(parts) if len(parts) > 1 else ""

    def get_stats(self) -> dict:
        """Get graph statistics."""
        type_counts = {}
        for _, data in self._graph.nodes(data=True):
            t = data.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_entities": self._graph.number_of_nodes(),
            "total_relationships": self._graph.number_of_edges(),
            "entity_types": type_counts,
        }

    def get_all_entities(self, limit: int = 100) -> list[dict]:
        """Get all entities for visualization."""
        entities = []
        for node_id, data in self._graph.nodes(data=True):
            entities.append({
                "id": node_id,
                "label": data.get("label", node_id),
                "type": data.get("type", "concept"),
                "mention_count": data.get("mention_count", 0),
            })
        entities.sort(key=lambda x: x.get("mention_count", 0), reverse=True)
        return entities[:limit]

    def get_all_edges(self) -> list[dict]:
        """Get all relationships for visualization."""
        edges = []
        for src, tgt, data in self._graph.edges(data=True):
            edges.append({
                "source": src,
                "target": tgt,
                "relation": data.get("relation", "related_to"),
                "weight": data.get("weight", 0.5),
            })
        return edges

    def clear(self):
        """Clear the entire knowledge graph."""
        self._graph.clear()
        self._save()

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize entity name to a consistent node ID."""
        return name.strip().lower().replace(" ", "_")
