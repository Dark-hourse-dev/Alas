import logging
import asyncio
import json
import networkx as nx
from typing import List, Dict, Any

from backend.app.memory.retrieval import MemoryRetriever
from backend.app.config import get_settings
import ollama

logger = logging.getLogger("alas.memory.synthesis")


class KnowledgeSynthesizer:
    """
    Background worker that analyzes the L2 Semantic Knowledge Graph
    to discover hidden insights and connections ("Aha!" moments).
    """
    
    def __init__(self):
        self.retriever = MemoryRetriever()
        
    async def synthesize(self) -> Dict[str, Any]:
        """
        Run the synthesis process over the current Knowledge Graph.
        Returns a dict describing any new insights discovered.
        """
        logger.info("🧠 Starting Deep Knowledge Synthesis...")
        
        # 1. Load the Knowledge Graph
        kg_data = self.retriever.get_knowledge_graph()
        
        if not kg_data or not kg_data.get("nodes"):
            logger.info("Knowledge Graph is empty or unavailable.")
            return {"status": "skipped", "reason": "empty_graph"}
            
        nodes = kg_data["nodes"]
        links = kg_data["links"]
        
        # Build NetworkX graph
        G = nx.Graph()
        for node in nodes:
            G.add_node(node["id"], group=node.get("group", 1))
        for link in links:
            G.add_edge(link["source"], link["target"])
            
        # 2. Find disjoint or loosely connected components
        # We look for nodes that have high centrality but are not connected to each other
        if len(G.nodes) < 5:
            logger.info("Knowledge Graph too small for meaningful synthesis.")
            return {"status": "skipped", "reason": "graph_too_small"}
            
        # Get nodes with highest degree centrality
        centrality = nx.degree_centrality(G)
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        top_concepts = [n[0] for n in sorted_nodes[:5]]
        
        # 3. Use LLM to find non-obvious connections
        prompt = f"""
        Here are the most central concepts in my user's memory:
        {json.dumps(top_concepts)}
        
        Analyze these concepts. Can you find a non-obvious, deep, or causal relationship between them?
        What is a profound insight or "Aha!" moment that connects these seemingly disparate ideas?
        
        Keep your response under 3 sentences. Be profound and analytical.
        """
        
        try:
            settings = get_settings()
            client = ollama.AsyncClient(host=settings.ollama_host)
            
            messages = [
                {"role": "system", "content": "You are a master of lateral thinking and pattern recognition. Find deep connections."},
                {"role": "user", "content": prompt}
            ]
            
            res = await client.chat(
                model=settings.ollama_model,
                messages=messages,
                options={"temperature": 0.8}
            )
            insight = res.message.content
            
            # 4. Save the insight back into the graph
            # We create an "Insight" node that links these top concepts
            insight_id = f"Insight: {insight[:30]}..."
            self.retriever._execute_query(
                "INSERT OR IGNORE INTO knowledge_graph (source, target, relationship) VALUES (?, ?, ?)",
                (insight_id, top_concepts[0], "connects_to")
            )
            self.retriever._execute_query(
                "INSERT OR IGNORE INTO knowledge_graph (source, target, relationship) VALUES (?, ?, ?)",
                (insight_id, top_concepts[1], "connects_to")
            )
            
            logger.info(f"💡 Discovered Insight: {insight}")
            
            return {
                "status": "success",
                "insight": insight,
                "connected_concepts": top_concepts[:2]
            }
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {"status": "error", "reason": str(e)}

async def run_synthesis_task():
    """Wrapper to run as a background task."""
    synthesizer = KnowledgeSynthesizer()
    return await synthesizer.synthesize()
