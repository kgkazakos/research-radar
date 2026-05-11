"""
research-radar · CPR Orbital Tool 22
Click CLI entry point.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .models import SignalCategory, SignalStrength, TrendReport
from .reporter import read_json, render_markdown, write_json
from .scanner import build_signals, scan_text

console = Console()


def _str_to_cats(cats_str: str | None) -> list[SignalCategory] | None:
    if not cats_str:
        return None
    mapping = {c.value: c for c in SignalCategory}
    result = []
    for token in cats_str.split(","):
        token = token.strip()
        if token in mapping:
            result.append(mapping[token])
        else:
            raise click.BadParameter(
                f"Unknown category {token!r}. Valid: {', '.join(mapping)}"
            )
    return result or None


@click.group()
@click.version_option()
def cli() -> None:
    """research-radar — domain-specific signal monitor for product researchers.

    Plugs into any research pipeline: text files, live web, internal graphs, or docs.

    \b
    Examples:
      research-radar scan --domain "AI in UX research" --input articles.txt
      research-radar scan --domain "payment UX" --llm-backend anthropic
      research-radar scan --domain "enterprise UX" --source-type graph --graph-json insights.json --llm-backend openai
      research-radar scan --domain "mobile UX" --source-type docs --docs-dir ./notes/ --llm-backend gemini
      research-radar report radar.json --format markdown
    """


@cli.command()
@click.option("--domain", "-d", required=True, help="Research domain to monitor.")
@click.option(
    "--source-type",
    type=click.Choice(["file", "web", "graph", "docs"]),
    default="file",
    show_default=True,
    help="Signal source: text file, live web, internal graph, or docs directory.",
)
@click.option(
    "--input", "-i", "input_file",
    type=click.Path(exists=True, path_type=Path),
    help="[file] Text file to scan.",
)
@click.option(
    "--graph-json",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="[graph] JSON export of your knowledge graph.",
)
@click.option("--graph-uri", default=None, help="[graph] Neo4j bolt URI.")
@click.option("--graph-user", default="neo4j", show_default=True, help="[graph] Neo4j username.")
@click.option("--graph-password", default=None, help="[graph] Neo4j password (or NEO4J_PASSWORD env var).")
@click.option("--graph-query", default=None, help="[graph] Custom Cypher query with $domain parameter.")
@click.option(
    "--docs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="[docs] Directory of .txt/.md files to scan.",
)
@click.option(
    "--llm-backend",
    type=click.Choice(["openai", "anthropic", "gemini"]),
    default=None,
    help="LLM backend for enrichment (required for web/graph/docs sources).",
)
@click.option(
    "--categories", "-c",
    default=None,
    help="Comma-separated: methodology,tooling,ai_llm,behavioral,industry,academic",
)
@click.option(
    "--min-strength",
    type=click.Choice(["low", "medium", "high"]),
    default="low",
    show_default=True,
)
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None, help="Save to .json or .md")
@click.option(
    "--format", "-f", "output_format",
    type=click.Choice(["json", "markdown", "plain"]),
    default="plain",
    show_default=True,
)
def scan(
    domain: str,
    source_type: str,
    input_file: Path | None,
    graph_json: Path | None,
    graph_uri: str | None,
    graph_user: str,
    graph_password: str | None,
    graph_query: str | None,
    docs_dir: Path | None,
    llm_backend: str | None,
    categories: str | None,
    min_strength: str,
    output: Path | None,
    output_format: str,
) -> None:
    """Scan for research signals from any source.

    \b
    Source types:
      file   — rule-based scan on a local text file (zero API calls)
      web    — live web search + LLM synthesis
      graph  — internal knowledge graph (Neo4j bolt or JSON export) + LLM synthesis
      docs   — directory of internal .txt/.md files + LLM synthesis
    """
    import os

    cats = _str_to_cats(categories)
    min_str = SignalStrength(min_strength)

    if source_type == "file":
        if not input_file:
            raise click.UsageError("--input is required for --source-type file.")
        text = input_file.read_text(encoding="utf-8")
        results = scan_text(text, domain=domain, categories=cats)
        signals = build_signals(results, domain=domain, min_strength=min_str)
        report = TrendReport(domain=domain, signals=signals, llm_enriched=False)

    else:
        if not llm_backend:
            raise click.UsageError(f"--llm-backend is required for --source-type {source_type}.")

        task_label = {
            "web": f"Scanning live web for [{domain}] via {llm_backend}…",
            "graph": f"Reading internal graph, synthesising with {llm_backend}…",
            "docs": f"Reading internal docs, synthesising with {llm_backend}…",
        }.get(source_type, "Scanning…")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(task_label, total=None)
            try:
                from .llm import enrich_report
                from .sources import DocsSource, GraphSource

                source_content: dict[SignalCategory, str] | None = None

                if source_type == "graph":
                    if not graph_json and not graph_uri:
                        raise click.UsageError(
                            "Provide --graph-json or --graph-uri for --source-type graph."
                        )
                    if graph_json:
                        src = GraphSource.from_json(graph_json)
                    else:
                        pwd = graph_password or os.environ.get("NEO4J_PASSWORD", "")
                        src = GraphSource.from_neo4j(graph_uri, graph_user, pwd, cypher_query=graph_query)  # type: ignore[arg-type]
                    chunks = src.fetch(domain=domain)
                    combined = " ".join(chunks)
                    source_content = {cat: combined for cat in (cats or list(SignalCategory))}

                elif source_type == "docs":
                    if not docs_dir:
                        raise click.UsageError("--docs-dir is required for --source-type docs.")
                    src_docs = DocsSource(docs_dir)
                    chunks = src_docs.fetch(domain=domain)
                    combined = " ".join(chunks)
                    source_content = {cat: combined for cat in (cats or list(SignalCategory))}

                report = enrich_report(
                    domain=domain,
                    backend=llm_backend,
                    categories=cats,
                    source_content=source_content,
                )

            except ImportError as exc:
                console.print(
                    f"[red]LLM deps missing:[/] {exc}\n"
                    f"Install: pip install 'research-radar[{llm_backend}]'"
                )
                sys.exit(1)

    _display_report(report, output_format, console)

    if output:
        _write_report(report, output)
        console.print(f"\n[dim]Report saved → {output}[/dim]")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format", "-f", "output_format",
    type=click.Choice(["json", "markdown", "plain"]),
    default="markdown",
    show_default=True,
)
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
def report(input_file: Path, output_format: str, output: Path | None) -> None:
    """Render a saved radar report (JSON) as markdown or plain text."""
    with open(input_file, encoding="utf-8") as fp:
        rpt = read_json(fp)
    _display_report(rpt, output_format, console)
    if output:
        _write_report(rpt, output)
        console.print(f"\n[dim]Saved → {output}[/dim]")


def _display_report(report: TrendReport, fmt: str, con: Console) -> None:
    if fmt == "json":
        con.print_json(json.dumps(report.to_dict(), indent=2))
    elif fmt == "markdown":
        con.print(Markdown(render_markdown(report)))
    else:
        con.print(Panel(
            f"[bold]{report.domain}[/bold]  ·  [dim]{report.signal_count} signals[/dim]",
            title="[green]Research Radar[/green]",
            expand=False,
        ))
        if report.narrative:
            con.print(Panel(report.narrative, title="Weekly Digest", style="dim"))
        table = Table(show_header=True, header_style="bold")
        table.add_column("Category", style="dim", width=18)
        table.add_column("Signal", width=32)
        table.add_column("Strength", width=10)
        table.add_column("Summary", width=50)
        strength_style = {
            SignalStrength.HIGH: "red",
            SignalStrength.MEDIUM: "yellow",
            SignalStrength.LOW: "white dim",
        }
        for cat, signals in report.by_category.items():
            for sig in signals:
                table.add_row(
                    cat.value, sig.title,
                    f"[{strength_style[sig.strength]}]{sig.strength.value.upper()}[/]",
                    sig.summary[:100] + ("…" if len(sig.summary) > 100 else ""),
                )
        con.print(table)


def _write_report(report: TrendReport, path: Path) -> None:
    if path.suffix == ".json":
        with open(path, "w", encoding="utf-8") as fp:
            write_json(report, fp)
    else:
        path.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    cli()
