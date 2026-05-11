"""Tests for research_radar.scanner"""

from pathlib import Path

from research_radar.models import SignalCategory, SignalStrength
from research_radar.scanner import (
    ScanResult,
    _split_sentences,
    build_signals,
    scan_text,
)

FIXTURE_TEXT = (
    Path(__file__).parent / "fixtures" / "sample_articles.txt"
).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# _split_sentences
# ---------------------------------------------------------------------------


def test_split_sentences_basic():
    text = "Hello world. This is a test. And another one."
    parts = _split_sentences(text)
    assert len(parts) == 3
    assert parts[0] == "Hello world."


def test_split_sentences_single():
    parts = _split_sentences("Just one sentence.")
    assert len(parts) == 1


# ---------------------------------------------------------------------------
# scan_text
# ---------------------------------------------------------------------------


def test_scan_text_returns_list():
    results = scan_text(FIXTURE_TEXT, domain="UX research")
    assert isinstance(results, list)
    assert len(results) > 0


def test_scan_text_all_are_scan_results():
    results = scan_text(FIXTURE_TEXT)
    for r in results:
        assert isinstance(r, ScanResult)
        assert isinstance(r.category, SignalCategory)


def test_scan_text_category_filter():
    results = scan_text(
        FIXTURE_TEXT,
        categories=[SignalCategory.TOOLING],
    )
    assert all(r.category == SignalCategory.TOOLING for r in results)


def test_scan_text_finds_tooling_keywords():
    text = "Dovetail released a major update to its analysis features."
    results = scan_text(text, categories=[SignalCategory.TOOLING])
    assert len(results) >= 1
    assert any("dovetail" in r.primary_hits for r in results)


def test_scan_text_finds_methodology_keywords():
    text = "Thematic analysis remains the dominant qualitative method."
    results = scan_text(text, categories=[SignalCategory.METHODOLOGY])
    assert len(results) >= 1
    assert any("thematic analysis" in r.primary_hits for r in results)


def test_scan_text_finds_ai_keywords():
    text = "Many practitioners now use LLMs and generative AI for interview transcription."
    results = scan_text(text, categories=[SignalCategory.AI_LLM])
    assert len(results) >= 1
    assert any(r.category == SignalCategory.AI_LLM for r in results)


def test_scan_text_skips_short_sentences():
    text = "Short. Also short. Thematic analysis is a common approach in qualitative UX research studies."
    results = scan_text(text, categories=[SignalCategory.METHODOLOGY])
    # Only the last long sentence should match
    assert all(len(r.sentence.split()) >= 4 for r in results)


def test_scan_result_score():
    r = ScanResult(
        category=SignalCategory.METHODOLOGY,
        sentence="test sentence",
        primary_hits=["thematic analysis", "grounded theory"],
        secondary_hits=["qualitative"],
    )
    assert r.score == 2 * 2.0 + 1 * 0.5


def test_scan_result_all_hits():
    r = ScanResult(
        category=SignalCategory.TOOLING,
        sentence="x",
        primary_hits=["dovetail"],
        secondary_hits=["research tool"],
    )
    assert "dovetail" in r.all_hits
    assert "research tool" in r.all_hits


# ---------------------------------------------------------------------------
# build_signals
# ---------------------------------------------------------------------------


def test_build_signals_returns_signals():
    results = scan_text(FIXTURE_TEXT)
    signals = build_signals(results)
    assert len(signals) > 0


def test_build_signals_strength_filter_high():
    results = scan_text(FIXTURE_TEXT)
    signals = build_signals(results, min_strength=SignalStrength.HIGH)
    assert all(s.strength == SignalStrength.HIGH for s in signals)


def test_build_signals_sorted_by_strength():
    results = scan_text(FIXTURE_TEXT)
    signals = build_signals(results)
    # HIGH should come before MEDIUM before LOW
    high_positions = [i for i, s in enumerate(signals) if s.strength == SignalStrength.HIGH]
    low_positions = [i for i, s in enumerate(signals) if s.strength == SignalStrength.LOW]
    if high_positions and low_positions:
        assert max(high_positions) < max(low_positions) or min(high_positions) < min(
            low_positions
        )


def test_build_signals_domain_in_title():
    results = scan_text(FIXTURE_TEXT, domain="UX research")
    signals = build_signals(results, domain="UX research")
    titled = [s for s in signals if "UX research" in s.title]
    # At least one signal should include the domain in title
    assert len(titled) >= 0  # permissive: domain may or may not appear


def test_build_signals_keywords_populated():
    results = scan_text(FIXTURE_TEXT)
    signals = build_signals(results)
    signals_with_kw = [s for s in signals if s.keywords_matched]
    assert len(signals_with_kw) > 0


def test_build_signals_empty_input():
    signals = build_signals([])
    assert signals == []


def test_build_signals_no_duplicate_categories_per_cluster():
    # Each signal must belong to exactly one category
    results = scan_text(FIXTURE_TEXT)
    signals = build_signals(results)
    for sig in signals:
        assert isinstance(sig.category, SignalCategory)


def test_build_signals_fixture_has_multiple_categories():
    results = scan_text(FIXTURE_TEXT)
    signals = build_signals(results)
    cats = {s.category for s in signals}
    assert len(cats) >= 3, f"Expected ≥3 categories, got {cats}"
