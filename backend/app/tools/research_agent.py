"""
ALAS Research Agent — Autonomous multi-step research pipeline.

Pipeline:
  1. search_web(query) → top N results
  2. read_webpage(url) for best results → extract content
  3. LLM synthesize → structured research report
  4. Save to file system + skill memory
  5. Return summary to user

Designed to be called as a single tool by the LLM, or executed
as a background task via the task queue.
"""

import logging
import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("alas.tools.research")


def research_topic(
    topic: str,
    depth: str = "standard",
    save_to_file: bool = True,
    output_dir: str = "~/alas_research",
) -> str:
    """
    Conduct autonomous research on a topic.
    
    Pipeline:
      1. Web search for the topic
      2. Read top articles
      3. Synthesize a structured report
      4. Save to file and skill memory
    
    Args:
        topic: The research topic or question.
        depth: "quick" (3 sources), "standard" (5 sources), or "deep" (8 sources).
        save_to_file: Whether to save the report as a markdown file.
        output_dir: Directory to save the report in.
    
    Returns:
        Research report summary.
    """
    from backend.app.llm.tools import search_web, read_webpage

    depth_map = {"quick": 3, "standard": 5, "deep": 8}
    num_sources = depth_map.get(depth, 5)

    logger.info(f"🔬 Research Agent: Starting research on '{topic}' (depth={depth}, sources={num_sources})")

    # === Step 1: Search the web ===
    logger.info("🔬 Step 1/4: Searching the web...")
    search_results_raw = search_web(topic)

    if "failed" in search_results_raw.lower() or "no web results" in search_results_raw.lower():
        return f"❌ Research failed: Could not find web results for '{topic}'.\n\nRaw: {search_results_raw}"

    # Parse search results into structured data
    sources = _parse_search_results(search_results_raw, max_results=num_sources)

    if not sources:
        return f"❌ Research failed: No usable search results for '{topic}'."

    logger.info(f"🔬 Found {len(sources)} sources")

    # === Step 2: Read top articles ===
    logger.info("🔬 Step 2/4: Reading articles...")
    article_contents = []
    for i, source in enumerate(sources):
        url = source.get("url", "")
        if not url:
            continue
        logger.info(f"   Reading [{i+1}/{len(sources)}]: {url[:80]}...")
        content = read_webpage(url)
        if content and "failed" not in content.lower():
            article_contents.append({
                "title": source.get("title", "Untitled"),
                "url": url,
                "content": content[:3000],  # Truncate per article
            })

    if not article_contents:
        # Fall back to search snippets only
        logger.warning("🔬 Could not read any articles, using search snippets only")
        article_contents = [
            {"title": s.get("title", ""), "url": s.get("url", ""), "content": s.get("snippet", "")}
            for s in sources
        ]

    logger.info(f"🔬 Successfully read {len(article_contents)} articles")

    # === Step 3: Synthesize report ===
    logger.info("🔬 Step 3/4: Synthesizing research report...")
    report = _synthesize_report(topic, article_contents)

    # === Step 4: Save ===
    saved_path = None
    if save_to_file:
        logger.info("🔬 Step 4/4: Saving report...")
        saved_path = _save_report(topic, report, output_dir)

    # Save to skill memory
    _save_to_skill_memory(topic, report, article_contents)

    # === Build final summary ===
    summary_parts = [
        f"# 🔬 Research Complete: {topic}\n",
        f"**Sources consulted:** {len(article_contents)}",
        f"**Depth:** {depth}",
    ]
    if saved_path:
        summary_parts.append(f"**Report saved to:** `{saved_path}`")

    summary_parts.extend([
        "",
        "---",
        "",
        report,
    ])

    result = "\n".join(summary_parts)
    logger.info(f"🔬 Research complete! Report: {len(report)} chars, {len(article_contents)} sources")
    return result


def _parse_search_results(raw: str, max_results: int = 5) -> list[dict]:
    """Parse the raw search_web output into structured source data."""
    sources = []
    current = {}

    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("Title:"):
            if current:
                sources.append(current)
            current = {"title": line[6:].strip()}
        elif line.startswith("URL:"):
            current["url"] = line[4:].strip()
        elif line.startswith("Snippet:"):
            current["snippet"] = line[8:].strip()

    if current:
        sources.append(current)

    return sources[:max_results]


def _synthesize_report(topic: str, articles: list[dict]) -> str:
    """
    Synthesize a structured research report from collected articles.
    Uses the LLM if available, otherwise does a structured compilation.
    """
    try:
        import ollama
        from backend.app.config import get_settings

        settings = get_settings()
        client = ollama.Client(host=settings.ollama_host)

        # Build context from articles
        context_parts = []
        for i, art in enumerate(articles, 1):
            context_parts.append(
                f"[Source {i}] {art['title']}\n"
                f"URL: {art['url']}\n"
                f"Content: {art['content'][:2000]}\n"
            )
        context = "\n---\n".join(context_parts)

        prompt = f"""You are a research analyst. Based on the following sources, write a comprehensive research report on: "{topic}"

Structure your report as:
1. **Overview** — What is this topic about? (2-3 sentences)
2. **Key Findings** — The most important facts and insights (bullet points)
3. **Detailed Analysis** — Deeper exploration of the topic (2-3 paragraphs)
4. **Practical Applications** — How this knowledge can be used
5. **Sources** — List the sources with URLs

Sources:
{context}

Write a thorough, well-organized report. Be factual and cite sources."""

        response = client.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.message.content

    except Exception as e:
        logger.warning(f"LLM synthesis failed, using structured compilation: {e}")
        return _compile_report_fallback(topic, articles)


def _compile_report_fallback(topic: str, articles: list[dict]) -> str:
    """Fallback report compilation when LLM is unavailable."""
    parts = [
        f"## Research Report: {topic}\n",
        f"*Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        "### Sources & Key Information\n",
    ]

    for i, art in enumerate(articles, 1):
        parts.append(f"**{i}. {art['title']}**")
        parts.append(f"   URL: {art['url']}")
        # Extract first 500 chars as summary
        content = art.get("content", "")[:500]
        if content:
            parts.append(f"   Summary: {content}")
        parts.append("")

    return "\n".join(parts)


def _save_report(topic: str, report: str, output_dir: str) -> Optional[str]:
    """Save the research report to a markdown file."""
    try:
        # Expand ~ and resolve path
        out_path = Path(output_dir).expanduser().resolve()
        out_path.mkdir(parents=True, exist_ok=True)

        # Generate safe filename
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_"
            for c in topic
        ).strip().replace(" ", "_")[:60]

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{safe_name}_{timestamp}.md"
        filepath = out_path / filename

        # Write report
        full_content = (
            f"# 🔬 Research Report: {topic}\n\n"
            f"*Generated by ALAS Research Agent on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            f"---\n\n"
            f"{report}\n"
        )

        filepath.write_text(full_content, encoding="utf-8")
        logger.info(f"🔬 Report saved to: {filepath}")
        return str(filepath)

    except Exception as e:
        logger.error(f"Failed to save research report: {e}")
        return None


def _save_to_skill_memory(topic: str, report: str, articles: list[dict]) -> None:
    """Save research findings to ALAS skill memory."""
    try:
        from backend.app.memory.skills import get_skill_memory

        # Extract key facts from the report
        lines = report.split("\n")
        key_facts = [
            line.strip("- *•").strip()
            for line in lines
            if line.strip().startswith(("-", "•", "*")) and len(line.strip()) > 10
        ][:10]  # Max 10 facts

        if not key_facts:
            key_facts = [report[:500]]

        # Add source URLs as facts
        source_urls = [f"Source: {art['url']}" for art in articles if art.get("url")]
        key_facts.extend(source_urls[:5])

        get_skill_memory().add_skill(
            name=f"Research: {topic}",
            steps=key_facts,
            description=report[:500],
        )
        logger.info(f"🔬 Research saved to skill memory: {topic}")

    except Exception as e:
        logger.warning(f"Failed to save research to skill memory: {e}")
