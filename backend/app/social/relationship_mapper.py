import logging
from typing import List, Dict, Any, Optional

try:
    import networkx as nx
except ImportError:
    nx = None

logger = logging.getLogger("alas.social.mapper")

class RelationshipMapper:
    """
    ALAS Social Relationship Graph.
    Uses NetworkX to maintain a web of entities (users, family, friends, colleagues)
    and the relationships between them to provide social context.
    """
    def __init__(self):
        if nx is None:
            logger.error("NetworkX not installed. Relationship Mapper disabled.")
            self.graph = None
        else:
            self.graph = nx.DiGraph()
            logger.info("👥 Social Relationship Mapper initialized.")
            
    def add_person(self, person_id: str, attributes: Dict[str, Any] = None):
        """Add a person (node) to the social graph."""
        if self.graph is None: return
        attrs = attributes or {}
        self.graph.add_node(person_id, type="person", **attrs)
        logger.debug(f"Added person to social graph: {person_id}")
        
    def add_relationship(self, source: str, target: str, relationship_type: str, weight: float = 1.0):
        """Add a directed relationship (edge) between two people."""
        if self.graph is None: return
        self.graph.add_edge(source, target, relation=relationship_type, weight=weight)
        logger.debug(f"Mapped relationship: {source} -[{relationship_type}]-> {target}")
        
    def get_social_context(self, person_id: str, depth: int = 1) -> str:
        """Extract a conversational string explaining who this person is in relation to others."""
        if self.graph is None or person_id not in self.graph:
            return f"I don't have any social context mapped for {person_id}."
            
        context = []
        # Check outward relationships
        out_edges = self.graph.out_edges(person_id, data=True)
        for u, v, data in out_edges:
            relation = data.get('relation', 'connected to')
            context.append(f"{person_id} is the {relation} of {v}.")
            
        # Check inward relationships
        in_edges = self.graph.in_edges(person_id, data=True)
        for u, v, data in in_edges:
            relation = data.get('relation', 'connected to')
            context.append(f"{u} is the {relation} of {person_id}.")
            
        if not context:
            return f"{person_id} is known, but I have no specific relationships mapped."
            
        return " ".join(context)
