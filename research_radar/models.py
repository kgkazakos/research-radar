"""
research-radar · CPR Orbital Tool 22
Core data models for radar signals and trend reports.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SignalCategory(str, Enum):
    METHODOLOGY = "methodology"
    TOOLING = "tooling"
    AI_LLM = "ai_llm"
    BEHAVIORAL = "behavioral"
    INDUSTRY = "industry"
    ACADEMIC = "academic"


CATEGORY_LABELS: dict[SignalCategory, str] = {
    SignalCategory.METHODOLOGY: "Methodology",
    SignalCategory.TOOLING: "Tooling",
    SignalCategory.AI_LLM: "AI / LLM",
    SignalCategory.BEHAVIORAL: "Behavioral Shifts",
    SignalCategory.INDUSTRY: "Industry Signals",
    SignalCategory.ACADEMIC: "Academic",
}

CATEGORY_COLORS: dict[SignalCategory, str] = {
    SignalCategory.METHODOLOGY: "#7F77DD",
    SignalCategory.TOOLING: "#1D9E75",
    SignalCategory.AI_LLM: "#185FA5",
    SignalCategory.BEHAVIORAL: "#D85A30",
    SignalCategory.INDUSTRY: "#BA7517",
    SignalCategory.ACADEMIC: "#854F0B",
}

CATEGORY_EMOJI: dict[SignalCategory, str] = {
    SignalCategory.METHODOLOGY: "🔬",
    SignalCategory.TOOLING: "🛠",
    SignalCategory.AI_LLM: "🤖",
    SignalCategory.BEHAVIORAL: "🧠",
    SignalCategory.INDUSTRY: "📊",
    SignalCategory.ACADEMIC: "📚",
}


class SignalStrength(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


STRENGTH_ORDER = {SignalStrength.HIGH: 3, SignalStrength.MEDIUM: 2, SignalStrength.LOW: 1}


@dataclass
class RadarSignal:
    category: SignalCategory
    title: str
    summary: str
    strength: SignalStrength
    sources: list[str] = field(default_factory=list)
    keywords_matched: list[str] = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    llm_enriched: bool = False
    relevance_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "title": self.title,
            "summary": self.summary,
            "strength": self.strength.value,
            "sources": self.sources,
            "keywords_matched": self.keywords_matched,
            "detected_at": self.detected_at,
            "llm_enriched": self.llm_enriched,
            "relevance_score": self.relevance_score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RadarSignal":
        return cls(
            category=SignalCategory(d["category"]),
            title=d["title"],
            summary=d["summary"],
            strength=SignalStrength(d["strength"]),
            sources=d.get("sources", []),
            keywords_matched=d.get("keywords_matched", []),
            detected_at=d.get("detected_at", datetime.datetime.now().isoformat()),
            llm_enriched=d.get("llm_enriched", False),
            relevance_score=d.get("relevance_score", 0.0),
        )


@dataclass
class TrendReport:
    domain: str
    generated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    signals: list[RadarSignal] = field(default_factory=list)
    narrative: Optional[str] = None
    llm_enriched: bool = False

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def high_signals(self) -> list[RadarSignal]:
        return [s for s in self.signals if s.strength == SignalStrength.HIGH]

    @property
    def by_category(self) -> dict[SignalCategory, list[RadarSignal]]:
        result: dict[SignalCategory, list[RadarSignal]] = {}
        for cat in SignalCategory:
            sigs = [s for s in self.signals if s.category == cat]
            if sigs:
                result[cat] = sorted(sigs, key=lambda s: STRENGTH_ORDER[s.strength], reverse=True)
        return result

    @property
    def top_categories(self) -> list[SignalCategory]:
        counts = {cat: len(sigs) for cat, sigs in self.by_category.items()}
        return sorted(counts, key=lambda c: counts[c], reverse=True)[:3]

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "generated_at": self.generated_at,
            "llm_enriched": self.llm_enriched,
            "narrative": self.narrative,
            "signal_count": self.signal_count,
            "top_categories": [c.value for c in self.top_categories],
            "signals": [s.to_dict() for s in self.signals],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TrendReport":
        report = cls(
            domain=d["domain"],
            generated_at=d.get("generated_at", datetime.datetime.now().isoformat()),
            narrative=d.get("narrative"),
            llm_enriched=d.get("llm_enriched", False),
        )
        report.signals = [RadarSignal.from_dict(s) for s in d.get("signals", [])]
        return report
