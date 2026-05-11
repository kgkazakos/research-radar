"""
research-radar · CPR Orbital Tool 22
Pluggable signal source abstraction layer.

Sources produce text chunks that feed the rule-based scanner or LLM enrichment layer.
Teams can integrate their own internal pipelines by subclassing SignalSource or using
CustomSource with any callable that returns a list of strings.

Built-in sources:
    FileSource    — local text file (rule-based, no API key)
    WebSource     — live web search via DuckDuckGo (requires LLM backend)
    GraphSource   — internal knowledge graph via Neo4j bolt or JSON export
    DocsSource    — internal documents from a directory of .txt / .md files
    CustomSource  — any callable returning list[str]

Usage:
    from research_radar.sources import GraphSource, WebSource
    source = GraphSource.from_json("insights_export.json")
    chunks = source.fetch(domain="AI in UX research")
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Callable


class SourceType(str, Enum):
    FILE = "file"
    WEB = "web"
    GRAPH = "graph"
    DOCS = "docs"
    CUSTOM = "custom"


SOURCE_LABELS: dict[SourceType, str] = {
    SourceType.FILE: "Text file",
    SourceType.WEB: "Live web scan",
    SourceType.GRAPH: "Internal graph",
    SourceType.DOCS: "Internal docs",
    SourceType.CUSTOM: "Custom source",
}

SOURCE_ICONS: dict[SourceType, str] = {
    SourceType.FILE: "📄",
    SourceType.WEB: "🌐",
    SourceType.GRAPH: "🗄",
    SourceType.DOCS: "📁",
    SourceType.CUSTOM: "🔌",
}


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class SignalSource(ABC):
    """
    Abstract base for signal sources.

    Subclass this to plug in any internal system (Confluence, Dovetail,
    Notion, a Neo4j graph, a custom vector store, etc.).
    """

    source_type: SourceType = SourceType.CUSTOM

    @abstractmethod
    def fetch(self, domain: str = "") -> list[str]:
        """
        Return a list of text chunks for this domain.

        Args:
            domain: Research domain hint (used for filtering/querying).

        Returns:
            List of text strings — sentences, paragraphs, or node contents.
        """

    @property
    def label(self) -> str:
        return SOURCE_LABELS.get(self.source_type, "Custom source")

    @property
    def icon(self) -> str:
        return SOURCE_ICONS.get(self.source_type, "🔌")


# ---------------------------------------------------------------------------
# FileSource
# ---------------------------------------------------------------------------


class FileSource(SignalSource):
    """Scans a local text file — articles, RSS dumps, research notes."""

    source_type = SourceType.FILE

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def fetch(self, domain: str = "") -> list[str]:
        text = self.path.read_text(encoding="utf-8")
        return [line.strip() for line in text.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# WebSource
# ---------------------------------------------------------------------------


class WebSource(SignalSource):
    """
    Live web search via DuckDuckGo.

    Requires: pip install "research-radar[openai|anthropic|gemini]"
    No search API key required — only the LLM key.
    """

    source_type = SourceType.WEB

    def __init__(self, llm_backend: str = "anthropic"):
        self.llm_backend = llm_backend

    def fetch(self, domain: str = "") -> list[str]:
        """
        Runs DuckDuckGo searches for the domain and returns raw result text.
        Intended to be consumed by enrich_report() in llm.py.
        """
        try:
            from langchain_community.tools import DuckDuckGoSearchRun  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "WebSource requires langchain-community and duckduckgo-search.\n"
                f"Install: pip install 'research-radar[{self.llm_backend}]'"
            ) from exc

        search = DuckDuckGoSearchRun()
        query = f"{domain} research trends"
        try:
            result = search.run(query)
            return [s.strip() for s in result.split(".") if len(s.strip()) > 20]
        except Exception:
            return []


# ---------------------------------------------------------------------------
# GraphSource
# ---------------------------------------------------------------------------


class GraphSource(SignalSource):
    """
    Internal knowledge graph source.

    Supports two backends:
    - Neo4j bolt connection (requires neo4j driver: pip install "research-radar[graph]")
    - JSON export (no extra deps, works rule-based)

    JSON export format — list of node objects with any of these text fields:
        [
          {"text": "...", "tags": ["methodology"], "source": "Q3 research"},
          {"content": "...", "category": "tooling"},
          {"body": "...", "title": "Insight about LLM adoption"},
          ...
        ]

    Neo4j Cypher queries return nodes whose text property is used.
    Domain filtering is passed as a parameter to the Cypher query.
    """

    source_type = SourceType.GRAPH

    # Fields to extract text from (in priority order)
    TEXT_FIELDS = ("text", "content", "body", "summary", "description", "title")

    def __init__(
        self,
        *,
        nodes: list[dict] | None = None,
        neo4j_uri: str | None = None,
        neo4j_auth: tuple[str, str] | None = None,
        cypher_query: str | None = None,
    ):
        """
        Args:
            nodes: Pre-loaded list of graph node dicts (JSON export mode).
            neo4j_uri: Bolt URI, e.g. "bolt://localhost:7687".
            neo4j_auth: (username, password) tuple.
            cypher_query: Cypher query returning nodes with a text field.
                          Use $domain parameter for domain filtering.
                          Default: "MATCH (n:Insight) RETURN n"
        """
        self._nodes = nodes or []
        self._neo4j_uri = neo4j_uri
        self._neo4j_auth = neo4j_auth
        self._cypher_query = cypher_query or (
            "MATCH (n:Insight) WHERE toLower(n.text) CONTAINS toLower($domain) "
            "OR $domain = '' RETURN n LIMIT 500"
        )

    @classmethod
    def from_json(cls, path: str | Path, encoding: str = "utf-8") -> "GraphSource":
        """Load from a JSON export file."""
        data = json.loads(Path(path).read_text(encoding=encoding))
        nodes = data if isinstance(data, list) else data.get("nodes", [])
        return cls(nodes=nodes)

    @classmethod
    def from_neo4j(
        cls,
        uri: str,
        username: str,
        password: str,
        cypher_query: str | None = None,
    ) -> "GraphSource":
        """Connect to a live Neo4j instance."""
        return cls(
            neo4j_uri=uri,
            neo4j_auth=(username, password),
            cypher_query=cypher_query,
        )

    def _extract_text(self, node: dict) -> str | None:
        """Extract text content from a node dict, trying known field names."""
        # Handle Neo4j node objects
        if hasattr(node, "items"):
            node = dict(node)
        if "n" in node and isinstance(node["n"], dict):
            node = node["n"]

        for field in self.TEXT_FIELDS:
            value = node.get(field)
            if value and isinstance(value, str) and len(value.strip()) > 10:
                return value.strip()
        return None

    def _fetch_from_neo4j(self, domain: str) -> list[str]:
        try:
            from neo4j import GraphDatabase  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "Neo4j source requires the neo4j driver.\n"
                "Install: pip install 'research-radar[graph]'"
            ) from exc

        driver = GraphDatabase.driver(self._neo4j_uri, auth=self._neo4j_auth)
        chunks: list[str] = []
        try:
            with driver.session() as session:
                result = session.run(self._cypher_query, domain=domain)
                for record in result:
                    for value in record.values():
                        text = self._extract_text(dict(value) if hasattr(value, "items") else {"text": str(value)})
                        if text:
                            chunks.append(text)
        finally:
            driver.close()
        return chunks

    def fetch(self, domain: str = "") -> list[str]:
        if self._neo4j_uri:
            return self._fetch_from_neo4j(domain)

        # JSON export mode — filter by domain if provided
        domain_lower = domain.lower()
        chunks: list[str] = []
        for node in self._nodes:
            text = self._extract_text(node)
            if text is None:
                continue
            if not domain_lower or domain_lower in text.lower():
                chunks.append(text)
            elif not chunks:
                chunks.append(text)  # fallback: include all if nothing matches
        return chunks


# ---------------------------------------------------------------------------
# DocsSource
# ---------------------------------------------------------------------------


class DocsSource(SignalSource):
    """
    Internal documents source — reads .txt and .md files from a directory.

    Useful for Confluence / Notion / SharePoint exports saved locally,
    or any structured folder of research notes.
    """

    source_type = SourceType.DOCS

    def __init__(self, directory: str | Path, glob: str = "**/*.{txt,md}"):
        self.directory = Path(directory)
        self.glob = glob

    def fetch(self, domain: str = "") -> list[str]:
        chunks: list[str] = []
        patterns = ["**/*.txt", "**/*.md"]
        for pattern in patterns:
            for fp in self.directory.glob(pattern):
                try:
                    text = fp.read_text(encoding="utf-8", errors="ignore")
                    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                    chunks.extend(lines)
                except Exception:
                    continue
        return chunks


# ---------------------------------------------------------------------------
# CustomSource
# ---------------------------------------------------------------------------


class CustomSource(SignalSource):
    """
    Plug in any callable that returns a list of text strings.

    Example:
        def my_confluence_fetcher(domain: str) -> list[str]:
            return confluence_api.search(domain)

        source = CustomSource(my_confluence_fetcher, label="Confluence")
    """

    source_type = SourceType.CUSTOM

    def __init__(self, fn: Callable[[str], list[str]], label: str = "Custom"):
        self._fn = fn
        self._label = label

    @property
    def label(self) -> str:
        return self._label

    def fetch(self, domain: str = "") -> list[str]:
        return self._fn(domain)
