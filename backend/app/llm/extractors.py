"""
ALAS Entity Extractor — LLM-powered entity and relationship extraction.

Uses the LLM to extract structured entities and relationships from
conversation text, feeding the semantic knowledge graph (L2).
"""

import json
import logging
from typing import Optional

import ollama

from backend.app.config import get_settings

logger = logging.getLogger("alas.llm.extractors")

EXTRACTION_PROMPT = """You are an entity and relationship extractor. Analyze the conversation below and extract:

1. **Entities**: People, concepts, skills, goals, events, topics, places, preferences mentioned
2. **Relationships**: How entities relate to each other

Output ONLY valid JSON in this exact format (no markdown, no explanation):
{{
  "entities": [
    {{"name": "entity name", "type": "person|concept|skill|goal|event|topic|place|preference"}}
  ],
  "relationships": [
    {{"source": "entity1", "target": "entity2", "relation": "knows_about|interested_in|related_to|works_on|prefers|learned_from|part_of"}}
  ]
}}

Rules:
- Extract only clearly stated facts, not assumptions
- Normalize names (e.g., "AI" not "artificial intelligence" unless both are used)
- Use the user's name if mentioned
- Keep entity names short (1-3 words)
- Maximum 10 entities and 10 relationships per extraction
- If nothing meaningful can be extracted, return {{"entities": [], "relationships": []}}

Conversation:
---
{conversation}
---

Extract entities and relationships as JSON:"""


async def extract_entities(conversation_text: str) -> dict:
    """
    Extract entities and relationships from conversation text using LLM.

    Args:
        conversation_text: The conversation to analyze.

    Returns:
        Dictionary with 'entities' and 'relationships' lists.
    """
    settings = get_settings()

    try:
        client = ollama.AsyncClient(host=settings.ollama_host)
        response = await client.chat(
            model=settings.ollama_model,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(conversation=conversation_text[:2000]),
            }],
            options={"temperature": 0.1},  # Low temp for structured output
        )

        # Always use attribute access for newer ollama library
        raw = response.message.content.strip()

        # Try to parse JSON from response
        result = _parse_extraction_response(raw)
        logger.info(f"Extracted {len(result.get('entities', []))} entities, {len(result.get('relationships', []))} relationships")
        return result

    except Exception as e:
        import traceback
        logger.error(f"Entity extraction failed: {e}\n{traceback.format_exc()}")
        return {"entities": [], "relationships": []}


def _parse_extraction_response(raw: str) -> dict:
    """Parse the LLM extraction response, handling common formatting issues."""
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    if "```" in raw:
        for block in raw.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                continue

    # Try finding JSON object in the text
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not parse extraction response: {raw[:200]}")
    return {"entities": [], "relationships": []}


def extract_user_facts(user_message: str, assistant_message: str) -> str:
    """
    Format a user-assistant exchange for entity extraction.

    Args:
        user_message: What the user said.
        assistant_message: What the assistant responded.

    Returns:
        Formatted conversation string.
    """
    return f"User: {user_message}\nAssistant: {assistant_message}"
