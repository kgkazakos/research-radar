"""
research-radar · CPR Orbital Tool 22
Rule-based signal scanner — no API keys required.

Scans text input (pasted articles, RSS dumps, notes) for research domain signals
using a curated keyword taxonomy per SignalCategory.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .models import STRENGTH_ORDER, RadarSignal, SignalCategory, SignalStrength

# ---------------------------------------------------------------------------
# Keyword taxonomy
# Each category has: primary keywords (strong signal), secondary (weak signal)
# ---------------------------------------------------------------------------

TAXONOMY: dict[SignalCategory, dict[str, list[str]]] = {
    SignalCategory.METHODOLOGY: {
        "primary": [
            "thematic analysis",
            "grounded theory",
            "diary study",
            "contextual inquiry",
            "card sorting",
            "tree testing",
            "moderated usability",
            "unmoderated usability",
            "longitudinal study",
            "ethnography",
            "co-design",
            "participatory design",
            "cognitive walkthrough",
            "heuristic evaluation",
            "jobs-to-be-done",
            "jtbd",
            "mental model",
            "affinity mapping",
            "experience sampling",
            "think aloud",
        ],
        "secondary": [
            "qualitative",
            "quantitative",
            "mixed methods",
            "interview",
            "survey",
            "usability test",
            "field study",
            "observation",
            "focus group",
            "prototype",
        ],
    },
    SignalCategory.TOOLING: {
        "primary": [
            "dovetail",
            "maze",
            "usertesting",
            "lookback",
            "dscout",
            "ethnio",
            "optimal workshop",
            "userlytics",
            "condens",
            "aurelius",
            "reframer",
            "tetra insights",
            "grain",
            "otter.ai",
            "notion",
            "airtable",
            "atlas.ti",
            "nvivo",
            "maxqda",
            "quirkos",
            "dedoose",
        ],
        "secondary": [
            "research tool",
            "research platform",
            "analysis software",
            "transcription",
            "repository",
            "insight management",
            "recruiting tool",
            "participant recruitment",
            "panel",
        ],
    },
    SignalCategory.AI_LLM: {
        "primary": [
            "large language model",
            "llm",
            "gpt-4",
            "claude",
            "gemini",
            "synthetic user",
            "synthetic participant",
            "ai-generated",
            "ai-assisted",
            "automated analysis",
            "automated coding",
            "computational",
            "generative ai",
            "prompt engineering",
            "retrieval augmented",
            "rag",
            "fine-tuning",
            "agent",
        ],
        "secondary": [
            "artificial intelligence",
            "machine learning",
            "natural language processing",
            "nlp",
            "sentiment analysis",
            "text mining",
            "automation",
            "ai",
        ],
    },
    SignalCategory.BEHAVIORAL: {
        "primary": [
            "say-do gap",
            "attitude-behavior gap",
            "trust erosion",
            "privacy concern",
            "decision fatigue",
            "cognitive load",
            "dark pattern",
            "friction",
            "drop-off",
            "abandonment",
            "workaround",
            "mental model shift",
            "behavioral change",
            "adoption barrier",
            "resistance",
            "habituation",
        ],
        "secondary": [
            "behavior",
            "behaviour",
            "user attitude",
            "preference shift",
            "expectation",
            "perception",
            "trust",
            "satisfaction",
            "frustration",
            "engagement",
        ],
    },
    SignalCategory.INDUSTRY: {
        "primary": [
            "research ops",
            "researchops",
            "democratization of research",
            "democratising research",
            "researcher burnout",
            "ux maturity",
            "research impact",
            "headcount",
            "layoff",
            "hiring freeze",
            "team structure",
            "embedded research",
            "centralized research",
            "research strategy",
            "research infrastructure",
            "roi of research",
        ],
        "secondary": [
            "industry trend",
            "market report",
            "salary survey",
            "benchmark",
            "hiring",
            "job market",
            "team",
            "organization",
            "leadership",
        ],
    },
    SignalCategory.ACADEMIC: {
        "primary": [
            "chi 2025",
            "chi 2026",
            "cscw",
            "dis 2025",
            "dis 2026",
            "acm",
            "ieee",
            "proceedings",
            "peer-reviewed",
            "preprint",
            "arxiv",
            "systematic review",
            "meta-analysis",
            "replication study",
            "longitudinal study",
        ],
        "secondary": [
            "research paper",
            "publication",
            "journal",
            "conference",
            "study",
            "findings",
            "evidence",
            "literature",
            "academic",
        ],
    },
}

# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------

_SENT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    return _SENT_RE.split(text.strip())


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


@dataclass
class ScanResult:
    category: SignalCategory
    sentence: str
    primary_hits: list[str] = field(default_factory=list)
    secondary_hits: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        return len(self.primary_hits) * 2.0 + len(self.secondary_hits) * 0.5

    @property
    def all_hits(self) -> list[str]:
        return self.primary_hits + self.secondary_hits


def scan_text(
    text: str,
    domain: str = "",
    categories: list[SignalCategory] | None = None,
) -> list[ScanResult]:
    """
    Scan raw text for research signals using keyword taxonomy.

    Args:
        text: Raw article text, RSS dump, or research notes.
        domain: Optional domain string (used to boost relevance scoring).
        categories: Limit scanning to specific categories (all by default).

    Returns:
        List of ScanResult objects, one per matched sentence.
    """
    active_cats = categories or list(SignalCategory)
    sentences = _split_sentences(text)
    results: list[ScanResult] = []

    domain_lower = domain.lower() if domain else ""

    for sent in sentences:
        sent_lower = sent.lower()
        if len(sent.split()) < 4:
            continue

        for cat in active_cats:
            taxonomy = TAXONOMY[cat]
            prim_hits = [kw for kw in taxonomy["primary"] if kw in sent_lower]
            sec_hits = [kw for kw in taxonomy["secondary"] if kw in sent_lower]

            # Boost if domain keyword appears in same sentence
            if domain_lower and domain_lower in sent_lower:
                prim_hits = prim_hits + (["[domain]"] if not prim_hits else [])

            if prim_hits or sec_hits:
                results.append(
                    ScanResult(
                        category=cat,
                        sentence=sent.strip(),
                        primary_hits=prim_hits,
                        secondary_hits=sec_hits,
                    )
                )

    return results


# ---------------------------------------------------------------------------
# Signal builder — clusters ScanResults into RadarSignals
# ---------------------------------------------------------------------------


def _strength_from_score(score: float) -> SignalStrength:
    if score >= 5.0:
        return SignalStrength.HIGH
    if score >= 2.0:
        return SignalStrength.MEDIUM
    return SignalStrength.LOW


def _make_summary(sentences: list[str], max_sentences: int = 3) -> str:
    seen: list[str] = []
    for s in sentences:
        s = s.strip()
        if s and s not in seen:
            seen.append(s)
        if len(seen) >= max_sentences:
            break
    return " ".join(seen)


def build_signals(
    results: list[ScanResult],
    domain: str = "",
    min_strength: SignalStrength = SignalStrength.LOW,
) -> list[RadarSignal]:
    """
    Cluster ScanResults into RadarSignals per category.

    Args:
        results: Raw scan results from scan_text().
        domain: Domain label for signal titles.
        min_strength: Filter out signals weaker than this.

    Returns:
        Sorted list of RadarSignal objects.
    """
    by_cat: dict[SignalCategory, list[ScanResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)

    signals: list[RadarSignal] = []
    min_order = STRENGTH_ORDER[min_strength]

    for cat, cat_results in by_cat.items():
        # Group into micro-clusters by primary keyword overlap
        clusters = _cluster_results(cat_results)

        for cluster in clusters:
            total_score = sum(r.score for r in cluster)
            all_keywords = list(
                {kw for r in cluster for kw in r.all_hits if kw != "[domain]"}
            )
            sentences = [r.sentence for r in cluster]

            strength = _strength_from_score(total_score)
            if STRENGTH_ORDER[strength] < min_order:
                continue

            # Title: best primary keyword + domain
            primary_terms = [kw for r in cluster for kw in r.primary_hits if kw != "[domain]"]
            key_term = primary_terms[0].title() if primary_terms else cat.value.replace("_", " ").title()
            title = f"{key_term} signal"
            if domain:
                title = f"{key_term} in {domain}"

            signals.append(
                RadarSignal(
                    category=cat,
                    title=title,
                    summary=_make_summary(sentences),
                    strength=strength,
                    keywords_matched=all_keywords[:8],
                    relevance_score=total_score,
                )
            )

    return sorted(signals, key=lambda s: (STRENGTH_ORDER[s.strength], s.relevance_score), reverse=True)


def _cluster_results(results: list[ScanResult]) -> list[list[ScanResult]]:
    """Simple greedy clustering by shared primary keywords."""
    if not results:
        return []

    clusters: list[list[ScanResult]] = []
    used = set()

    for i, r in enumerate(results):
        if i in used:
            continue
        cluster = [r]
        used.add(i)
        r_prim = set(r.primary_hits)

        for j, r2 in enumerate(results):
            if j in used:
                continue
            if r_prim & set(r2.primary_hits):  # shared primary keywords
                cluster.append(r2)
                used.add(j)

        clusters.append(cluster)

    return clusters
