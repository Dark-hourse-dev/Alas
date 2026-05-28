import asyncio
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger("alas.swarm.blackboard")

class Blackboard:
    """
    Agent Communication Bus.
    Acts as a centralized shared memory and pub/sub event bus for sub-agents.
    """
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        logger.info("🐝 Swarm Blackboard initialized.")

    async def publish(self, topic: str, data: Any, publisher: str = "system"):
        """Publish an event/data to a specific topic."""
        callbacks_to_run = []
        
        async with self._lock:
            # Update shared state
            if topic not in self.state:
                self.state[topic] = []
            self.state[topic].append({"source": publisher, "data": data})
            
            # Keep history bounded
            if len(self.state[topic]) > 50:
                self.state[topic].pop(0)
                
            # Copy subscribers to notify outside the lock
            if topic in self.subscribers:
                callbacks_to_run = list(self.subscribers[topic])

        # Notify subscribers without holding the lock
        for callback in callbacks_to_run:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(topic, data, publisher)
                else:
                    callback(topic, data, publisher)
            except Exception as e:
                logger.error(f"Error in subscriber callback for topic {topic}: {e}")
                
        logger.debug(f"[{publisher}] published to [{topic}]")

    def subscribe(self, topic: str, callback: Callable):
        """Subscribe an agent to a specific topic."""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        if callback not in self.subscribers[topic]:
            self.subscribers[topic].append(callback)
            
    def read_state(self, topic: str) -> List[Dict[str, Any]]:
        """Read the recent history of a topic from the blackboard."""
        return self.state.get(topic, [])
