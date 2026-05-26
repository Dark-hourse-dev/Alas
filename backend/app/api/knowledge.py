"""
ALAS Knowledge Graph API — Endpoints for knowledge graph inspection and management.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.memory.knowledge_graph import KnowledgeGraph
from backend.app.memory.consolidation import ConsolidationEngine

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_graph: Optional[KnowledgeGraph] = None
_consolidation: Optional[ConsolidationEngine] = None


def get_graph() -> KnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph()
    return _graph


def get_consolidation() -> ConsolidationEngine:
    global _consolidation
    if _consolidation is None:
        _consolidation = ConsolidationEngine()
    return _consolidation


class EntityRequest(BaseModel):
    name: str
    entity_type: str = "concept"
    properties: Optional[dict] = None


class RelationshipRequest(BaseModel):
    source: str
    target: str
    relation: str = "related_to"


@router.get("/stats")
async def graph_stats():
    """Get knowledge graph statistics."""
    return get_graph().get_stats()


@router.get("/entities")
async def list_entities(limit: int = 50, entity_type: Optional[str] = None):
    """List all entities, optionally filtered by type."""
    graph = get_graph()
    entities = graph.get_all_entities(limit=limit)
    if entity_type:
        entities = [e for e in entities if e.get("type") == entity_type]
    return {"entities": entities}


@router.get("/entity/{name}")
async def get_entity(name: str):
    """Get detailed info about an entity and its connections."""
    result = get_graph().query_entity(name)
    if result is None:
        return {"error": f"Entity '{name}' not found"}
    return result


@router.post("/entity")
async def add_entity(request: EntityRequest):
    """Manually add an entity to the knowledge graph."""
    node_id = get_graph().add_entity(
        name=request.name,
        entity_type=request.entity_type,
        properties=request.properties,
        source="manual",
    )
    return {"status": "added", "node_id": node_id}


@router.post("/relationship")
async def add_relationship(request: RelationshipRequest):
    """Manually add a relationship between entities."""
    src_id, tgt_id = get_graph().add_relationship(
        source_name=request.source,
        target_name=request.target,
        relation=request.relation,
    )
    return {"status": "added", "source": src_id, "target": tgt_id}


@router.get("/related/{name}")
async def get_related(name: str, depth: int = 2, limit: int = 20):
    """Find entities related to the given entity."""
    related = get_graph().query_related(name, max_depth=depth, limit=limit)
    return {"entity": name, "related": related}


@router.get("/search")
async def search_knowledge(q: str, entity_type: Optional[str] = None, limit: int = 10):
    """Search entities by name."""
    results = get_graph().search(q, entity_type=entity_type, limit=limit)
    return {"query": q, "results": results}


@router.get("/graph")
async def get_full_graph():
    """Get full graph data for visualization (nodes + edges)."""
    graph = get_graph()
    return {
        "nodes": graph.get_all_entities(limit=200),
        "edges": graph.get_all_edges(),
        "stats": graph.get_stats(),
    }


@router.post("/consolidate")
async def trigger_consolidation(session_id: Optional[str] = None):
    """Trigger memory consolidation — extracts knowledge from episodic memories."""
    engine = get_consolidation()
    result = await engine.consolidate(session_id=session_id)
    return result


@router.post("/reflect")
async def generate_reflection(session_id: Optional[str] = None):
    """Generate a self-reflection on recent interactions."""
    engine = get_consolidation()
    reflection = await engine.generate_reflection(session_id=session_id)
    return {"reflection": reflection}


@router.delete("/")
async def clear_graph():
    """Clear the entire knowledge graph. Irreversible."""
    get_graph().clear()
    return {"status": "cleared"}
