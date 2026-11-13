"""
research-radar · CPR Orbital Tool 22
LLM enrichment layer — opt-in via --llm-backend flag.

Uses LangChain + DuckDuckGo (no search API key required) to scan the live web
for domain-specific signals, then synthesises them with the chosen LLM.

Requires one of:
    pip install "research-radar[openai]"
    pip install "research-radar[anthropic]"
    pip install "research-radar[gemini]"

Environment variables:
    OPENAI_API_KEY      for openai backend
    ANTHROPIC_API_KEY   for anthropic backend
    GOOGLE_API_KEY      for gemini backend
"""

from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .models import (
    CATEGORY_LABELS,
    RadarSignal,
    SignalCategory,
    SignalStrength,
    TrendReport,
)

# ---------------------------------------------------------------------------
# Search queries per category
# ---------------------------------------------------------------------------

_CATEGORY_QUERIES: dict[SignalCategory, str] = {
    SignalCategory.METHODOLOGY: "UX research methodology trends {domain} {year}",
    SignalCategory.TOOLING: "user research tools product research new {domain} {year}",
    SignalCategory.AI_LLM: "AI LLM generative AI UX research product research {domain} {year}",
    SignalCategory.BEHAVIORAL: "user behavior shifts attitudes preferences {domain} research {year}",
    SignalCategory.INDUSTRY: "UX research industry trends hiring team structure {domain} {year}",
    SignalCategory.ACADEMIC: "HCI research papers CHI CSCW {domain} {year}",
}

_SIGNAL_PROMPT = """\
You are a senior product researcher scanning the web for domain-specific research signals.

Domain: {domain}
Category: {category_label}
Search results (web snippets):
---
{search_results}
---

Extract 1-3 distinct research signals from these snippets that are relevant to the domain "{domain}" and the category "{category_label}".

For each signal output a JSON object with keys:
  title      - short descriptive title (max 10 words)
  summary    - 2-3 sentence summary of the signal and why it matters for researchers
  strength   - "high", "medium", or "low" (based on evidence strength and recency)
  sources    - list of source names or URLs mentioned in the snippets (max 3)

Respond ONLY with a JSON array of objects. No preamble, no markdown fences.
If no relevant signal is found, return an empty array [].
"""

_NARRATIVE_PROMPT = """\
You are a senior product researcher writing a weekly trend digest.

Domain: {domain}
Signals detected (JSON):
{signals_json}

Write a weekly radar digest for researchers working in "{domain}".
- 3-5 sentences, narrative style, as if briefing a research team
- Highlight the 2-3 most important signals and what they mean for practitioners
- Acknowledge uncertainty where evidence is thin
- Do NOT use bullet points — prose only
- End with one open question for the team to consider

Respond with ONLY the narrative text. No headers, no markdown.
"""


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------


def _get_llm(backend: str):  # type: ignore[return]
    """Return a LangChain chat model for the given backend string."""
    backend = backend.lower()

    if backend == "openai":
        from langchain_openai import ChatOpenAI  # type: ignore

        return ChatOpenAI(model="gpt-5.5", temperature=0.3)

    if backend == "anthropic":
        from langchain_anthropic import ChatAnthropic  # type: ignore

        return ChatAnthropic(model="claude-sonnet-4-6", temperature=0.3)  # type: ignore[call-arg]

    if backend == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore

        return ChatGoogleGenerativeAI(model="gemini-4-argon", temperature=0.3)

    raise ValueError(f"Unknown LLM backend: {backend!r}. Choose openai, anthropic, or gemini.")


def _get_search():
    """Return a DuckDuckGo search tool."""
    from langchain_community.tools import DuckDuckGoSearchRun  # type: ignore

    return DuckDuckGoSearchRun()


# ---------------------------------------------------------------------------
# Main enrichment function
# ---------------------------------------------------------------------------


def enrich_report(
    domain: str,
    backend: str,
    categories: list[SignalCategory] | None = None,
    source_content: dict[SignalCategory, str] | None = None,
) -> TrendReport:
    """
    Synthesise research signals with LLM from web search or pre-fetched source content.

    Args:
        domain: Research domain to monitor (e.g. "AI in UX research").
        backend: LLM backend — "openai", "anthropic", or "gemini".
        categories: Limit to specific categories (all by default).
        source_content: Pre-fetched text per category (from GraphSource, DocsSource, etc.).
                        When provided for a category, skips web search for that category.

    Returns:
        TrendReport with LLM-enriched signals and narrative.
    """
    import json

    llm = _get_llm(backend)
    active_cats = categories or list(SignalCategory)
    year = str(datetime.datetime.now().year)
    source_content = source_content or {}

    signals: list[RadarSignal] = []

    for cat in active_cats:
        # Use pre-fetched source content if provided, otherwise fall back to web search
        if cat in source_content and source_content[cat].strip():
            search_results = source_content[cat]
        else:
            search = _get_search()
            query_template = _CATEGORY_QUERIES[cat]
            query = query_template.format(domain=domain, year=year)
            try:
                search_results = search.run(query)
            except Exception:
                search_results = ""

        if not search_results.strip():
            continue

        prompt = _SIGNAL_PROMPT.format(
            domain=domain,
            category_label=CATEGORY_LABELS[cat],
            search_results=search_results[:2000],
        )

        try:
            response = llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            raw = raw.strip().strip("```json").strip("```").strip()
            items = json.loads(raw)
        except Exception:
            items = []

        for item in items:
            if not isinstance(item, dict):
                continue
            strength_raw = item.get("strength", "low")
            try:
                strength = SignalStrength(strength_raw)
            except ValueError:
                strength = SignalStrength.LOW

            signals.append(
                RadarSignal(
                    category=cat,
                    title=item.get("title", "Unnamed signal"),
                    summary=item.get("summary", ""),
                    strength=strength,
                    sources=item.get("sources", [])[:3],
                    llm_enriched=True,
                )
            )

    # Generate narrative digest
    narrative = None
    if signals:
        signals_summary = [
            {"category": s.category.value, "title": s.title, "strength": s.strength.value}
            for s in signals[:10]
        ]
        narr_prompt = _NARRATIVE_PROMPT.format(
            domain=domain,
            signals_json=json.dumps(signals_summary, indent=2),
        )
        try:
            narr_resp = llm.invoke(narr_prompt)
            narrative = (
                narr_resp.content if hasattr(narr_resp, "content") else str(narr_resp)
            ).strip()
        except Exception:
            narrative = None

    return TrendReport(
        domain=domain,
        signals=signals,
        narrative=narrative,
        llm_enriched=True,
    )
