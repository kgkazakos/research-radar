"""Tests for research_radar.models and research_radar.reporter"""

import io
import json
from pathlib import Path

from research_radar.models import (
    CATEGORY_COLORS,
    CATEGORY_EMOJI,
    CATEGORY_LABELS,
    RadarSignal,
    SignalCategory,
    SignalStrength,
    TrendReport,
)
from research_radar.reporter import read_json, render_markdown, render_plain, write_json
from research_radar.scanner import build_signals, scan_text

FIXTURE_TEXT = (
    Path(__file__).parent / "fixtures" / "sample_articles.txt"
).read_text(encoding="utf-8")


def _make_signal(
    cat: SignalCategory = SignalCategory.METHODOLOGY,
    strength: SignalStrength = SignalStrength.HIGH,
) -> RadarSignal:
    return RadarSignal(
        category=cat,
        title="Test signal",
        summary="This is a test summary for the signal.",
        strength=strength,
        keywords_matched=["thematic analysis"],
        sources=["example.com"],
    )


def _make_report() -> TrendReport:
    report = TrendReport(domain="AI in UX research")
    report.signals = [
        _make_signal(SignalCategory.METHODOLOGY, SignalStrength.HIGH),
        _make_signal(SignalCategory.TOOLING, SignalStrength.MEDIUM),
        _make_signal(SignalCategory.AI_LLM, SignalStrength.LOW),
    ]
    report.narrative = "This is a test narrative for the weekly digest."
    return report


# ---------------------------------------------------------------------------
# RadarSignal
# ---------------------------------------------------------------------------


def test_radar_signal_to_dict():
    sig = _make_signal()
    d = sig.to_dict()
    assert d["category"] == "methodology"
    assert d["strength"] == "high"
    assert d["title"] == "Test signal"
    assert d["llm_enriched"] is False


def test_radar_signal_roundtrip():
    sig = _make_signal()
    restored = RadarSignal.from_dict(sig.to_dict())
    assert restored.category == sig.category
    assert restored.strength == sig.strength
    assert restored.title == sig.title
    assert restored.keywords_matched == sig.keywords_matched


def test_radar_signal_llm_enriched_flag():
    sig = _make_signal()
    sig.llm_enriched = True
    d = sig.to_dict()
    restored = RadarSignal.from_dict(d)
    assert restored.llm_enriched is True


# ---------------------------------------------------------------------------
# TrendReport
# ---------------------------------------------------------------------------


def test_trend_report_signal_count():
    report = _make_report()
    assert report.signal_count == 3


def test_trend_report_high_signals():
    report = _make_report()
    assert len(report.high_signals) == 1
    assert report.high_signals[0].strength == SignalStrength.HIGH


def test_trend_report_by_category():
    report = _make_report()
    cats = report.by_category
    assert SignalCategory.METHODOLOGY in cats
    assert SignalCategory.TOOLING in cats


def test_trend_report_top_categories():
    report = _make_report()
    top = report.top_categories
    assert len(top) <= 3
    assert all(isinstance(c, SignalCategory) for c in top)


def test_trend_report_roundtrip():
    report = _make_report()
    d = report.to_dict()
    restored = TrendReport.from_dict(d)
    assert restored.domain == report.domain
    assert restored.signal_count == report.signal_count
    assert restored.narrative == report.narrative


def test_trend_report_empty():
    report = TrendReport(domain="empty domain")
    assert report.signal_count == 0
    assert report.high_signals == []
    assert report.by_category == {}


# ---------------------------------------------------------------------------
# Metadata completeness
# ---------------------------------------------------------------------------


def test_all_categories_have_labels():
    for cat in SignalCategory:
        assert cat in CATEGORY_LABELS
        assert CATEGORY_LABELS[cat]


def test_all_categories_have_colors():
    for cat in SignalCategory:
        assert cat in CATEGORY_COLORS
        assert CATEGORY_COLORS[cat].startswith("#")


def test_all_categories_have_emoji():
    for cat in SignalCategory:
        assert cat in CATEGORY_EMOJI


# ---------------------------------------------------------------------------
# Reporter — render_markdown
# ---------------------------------------------------------------------------


def test_render_markdown_contains_domain():
    report = _make_report()
    md = render_markdown(report)
    assert "AI in UX research" in md


def test_render_markdown_contains_signal_count():
    report = _make_report()
    md = render_markdown(report)
    assert "3" in md


def test_render_markdown_contains_narrative():
    report = _make_report()
    md = render_markdown(report)
    assert report.narrative in md


def test_render_markdown_contains_signal_titles():
    report = _make_report()
    md = render_markdown(report)
    assert "Test signal" in md


def test_render_markdown_strength_badges():
    report = _make_report()
    md = render_markdown(report)
    assert "HIGH" in md
    assert "MEDIUM" in md
    assert "LOW" in md


# ---------------------------------------------------------------------------
# Reporter — render_plain
# ---------------------------------------------------------------------------


def test_render_plain_contains_domain():
    report = _make_report()
    txt = render_plain(report)
    assert "AI IN UX RESEARCH" in txt


def test_render_plain_contains_categories():
    report = _make_report()
    txt = render_plain(report)
    assert "METHODOLOGY" in txt or "methodology" in txt.lower()


# ---------------------------------------------------------------------------
# Reporter — JSON round-trip
# ---------------------------------------------------------------------------


def test_write_read_json_roundtrip():
    report = _make_report()
    buf = io.StringIO()
    write_json(report, buf)
    buf.seek(0)
    restored = read_json(buf)
    assert restored.domain == report.domain
    assert restored.signal_count == report.signal_count
    assert restored.signals[0].title == report.signals[0].title


def test_write_json_valid_json():
    report = _make_report()
    buf = io.StringIO()
    write_json(report, buf)
    buf.seek(0)
    data = json.load(buf)
    assert "domain" in data
    assert "signals" in data


# ---------------------------------------------------------------------------
# Integration: fixture text → report → markdown
# ---------------------------------------------------------------------------


def test_integration_fixture_to_markdown():
    results = scan_text(FIXTURE_TEXT, domain="UX research")
    signals = build_signals(results, domain="UX research")
    report = TrendReport(domain="UX research", signals=signals)
    md = render_markdown(report)
    assert "UX research" in md
    assert len(md) > 100
