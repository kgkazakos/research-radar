"""Tests for research_radar.sources"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from research_radar.sources import (
    CustomSource,
    DocsSource,
    FileSource,
    GraphSource,
    SignalSource,
    SourceType,
    WebSource,
)

FIXTURE_TEXT = (
    Path(__file__).parent / "fixtures" / "sample_articles.txt"
).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# FileSource
# ---------------------------------------------------------------------------


def test_file_source_type():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write(FIXTURE_TEXT)
        path = f.name
    src = FileSource(path)
    assert src.source_type == SourceType.FILE
    chunks = src.fetch(domain="UX research")
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_file_source_non_empty_lines():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Line one.\n\n\nLine two.\n")
        path = f.name
    chunks = FileSource(path).fetch()
    assert "Line one." in chunks
    assert "Line two." in chunks
    assert "" not in chunks


# ---------------------------------------------------------------------------
# GraphSource — JSON mode
# ---------------------------------------------------------------------------


def test_graph_source_from_json_file():
    nodes = [
        {"text": "Thematic analysis is widely used in qualitative UX research."},
        {"content": "Dovetail released a major update to its analysis features."},
        {"body": "LLMs are being adopted for automated transcript coding."},
    ]
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(nodes, f)
        path = f.name

    src = GraphSource.from_json(path)
    assert src.source_type == SourceType.GRAPH
    chunks = src.fetch(domain="UX research")
    assert len(chunks) >= 1
    assert all(isinstance(c, str) for c in chunks)


def test_graph_source_json_nested_nodes_key():
    data = {
        "nodes": [
            {"text": "Participants showed trust erosion after AI recommendation failure."},
        ]
    }
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(data, f)
        path = f.name
    chunks = GraphSource.from_json(path).fetch()
    assert len(chunks) == 1
    assert "trust erosion" in chunks[0]


def test_graph_source_inline_nodes():
    nodes = [
        {"text": "Synthetic participants can approximate behavioral patterns."},
        {"summary": "CHI 2026 preprint on longitudinal trust studies."},
        {"title": "Short"},  # too short, should be skipped
    ]
    src = GraphSource(nodes=nodes)
    chunks = src.fetch()
    assert len(chunks) == 2


def test_graph_source_domain_filter():
    nodes = [
        {"text": "Dovetail released AI clustering for qualitative UX research teams."},
        {"text": "Unrelated note about quarterly planning and budget reviews."},
    ]
    src = GraphSource(nodes=nodes)
    chunks = src.fetch(domain="UX research")
    # At least the matching node should be in results
    assert any("Dovetail" in c for c in chunks)


def test_graph_source_empty_nodes():
    src = GraphSource(nodes=[])
    chunks = src.fetch(domain="anything")
    assert chunks == []


def test_graph_source_text_field_priority():
    node = {"title": "Short", "text": "This is a longer and more useful insight text."}
    src = GraphSource(nodes=[node])
    chunks = src.fetch()
    assert chunks[0] == "This is a longer and more useful insight text."


# ---------------------------------------------------------------------------
# DocsSource
# ---------------------------------------------------------------------------


def test_docs_source_reads_txt_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "notes.txt").write_text("Research note one.\nResearch note two.")
        (Path(tmpdir) / "report.md").write_text("# Report\nKey insight here.")
        src = DocsSource(tmpdir)
        chunks = src.fetch()
        joined = " ".join(chunks)
        assert "Research note one." in joined
        assert "Key insight here." in joined


def test_docs_source_type():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = DocsSource(tmpdir)
        assert src.source_type == SourceType.DOCS


def test_docs_source_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = DocsSource(tmpdir)
        assert src.fetch() == []


# ---------------------------------------------------------------------------
# CustomSource
# ---------------------------------------------------------------------------


def test_custom_source_calls_fn():
    called_with = []

    def my_fn(domain: str) -> list[str]:
        called_with.append(domain)
        return [f"Custom chunk for {domain}"]

    src = CustomSource(my_fn, label="My internal system")
    chunks = src.fetch(domain="payment UX")
    assert chunks == ["Custom chunk for payment UX"]
    assert called_with == ["payment UX"]


def test_custom_source_label():
    src = CustomSource(lambda d: [], label="Confluence export")
    assert src.label == "Confluence export"


def test_custom_source_type():
    src = CustomSource(lambda d: [])
    assert src.source_type == SourceType.CUSTOM


# ---------------------------------------------------------------------------
# SignalSource — abstract enforcement
# ---------------------------------------------------------------------------


def test_signal_source_is_abstract():
    with pytest.raises(TypeError):
        SignalSource()  # type: ignore


# ---------------------------------------------------------------------------
# WebSource (no network call — just check structure)
# ---------------------------------------------------------------------------


def test_web_source_type():
    src = WebSource(llm_backend="anthropic")
    assert src.source_type == SourceType.WEB


def test_web_source_import_error_without_deps():
    src = WebSource()
    with patch.dict("sys.modules", {"langchain_community": None, "langchain_community.tools": None}):
        with pytest.raises((ImportError, Exception)):
            src.fetch(domain="test")
