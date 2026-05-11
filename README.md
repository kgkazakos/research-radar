# 📡 research-radar

> **CPR Orbital Series · Tool 22 of 40**  
> Automated domain-specific signal monitor delivering weekly research trend digests for product researchers.

[![CI](https://github.com/kgkazakos/research-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/kgkazakos/research-radar/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The problem

Research teams struggle to stay current with what's shifting in their domain — new methods, new tools, emerging behavioural patterns, relevant academic output. That kind of monitoring doesn't happen systematically; it happens in slack channels, Twitter lists, and the occasional newsletter. It's fragmented, uneven, and rarely tied to what your team is actually researching.

`research-radar` gives you a structured weekly digest of domain signals, either from text corpora you feed it (no API key needed) or from live web scanning via LangChain + DuckDuckGo (LLM opt-in).

---

## Features

- **Six signal categories** — Methodology, Tooling, AI/LLM, Behavioral Shifts, Industry Signals, Academic  
- **Rule-based core** — works on any text input (articles, RSS dumps, notes) with zero API calls  
- **Live web scan** — optional LLM enrichment via LangChain + DuckDuckGo (no search API key required, just your LLM key)  
- **Three LLM backends** — OpenAI, Anthropic, Gemini; swap with `--llm-backend`  
- **Signal strength scoring** — HIGH / MEDIUM / LOW based on keyword density and evidence breadth  
- **Narrative digest** — LLM-generated weekly briefing for your research team  
- **Streamlit dashboard** — visual radar UI for team walkthroughs and screenshot-ready outputs  
- **Multiple output formats** — JSON, Markdown, plain text  

---

## Installation

```bash
# Rule-based core (no API keys needed)
pip install research-radar

# With live web scan via OpenAI
pip install "research-radar[openai]"

# With live web scan via Anthropic
pip install "research-radar[anthropic]"

# With live web scan via Gemini
pip install "research-radar[gemini]"

# Streamlit dashboard
pip install "research-radar[streamlit]"

# Everything
pip install "research-radar[all]"
```

---

## CLI usage

### Rule-based scan (zero API calls)

```bash
# Scan a text file (articles, RSS dump, pasted notes)
research-radar scan --domain "AI in UX research" --input articles.txt

# Save report as JSON
research-radar scan --domain "payment UX" --input corpus.txt --output report.json

# Filter to specific categories
research-radar scan \
  --domain "enterprise B2B" \
  --input notes.txt \
  --categories "methodology,ai_llm,behavioral" \
  --min-strength medium \
  --format markdown
```

### Live web scan with LLM

```bash
# Scan live web, synthesise with OpenAI
export OPENAI_API_KEY=sk-...
research-radar scan --domain "AI in UX research" --llm-backend openai

# Use Anthropic
export ANTHROPIC_API_KEY=...
research-radar scan --domain "payment UX" --llm-backend anthropic --format markdown

# Use Gemini + save to file
export GOOGLE_API_KEY=...
research-radar scan \
  --domain "enterprise SaaS onboarding" \
  --llm-backend gemini \
  --output weekly.json
```

### Render a saved report

```bash
research-radar report weekly.json --format markdown
research-radar report weekly.json --format plain
research-radar report weekly.json --output weekly.md
```

---

## Streamlit dashboard

```bash
pip install "research-radar[streamlit]"
streamlit run research_radar/app.py
```

The dashboard provides:
- Domain input + scan mode selector (text file or live web)
- LLM backend selector + category filters
- Signal strength summary statistics
- Colour-coded signal cards per category
- Narrative digest panel
- JSON + Markdown download buttons

---

## Signal categories

| Category | What it tracks |
|----------|---------------|
| 🔬 Methodology | New/emerging research methods, frameworks, approaches |
| 🛠 Tooling | Research tools, platforms, software updates |
| 🤖 AI / LLM | AI-assisted research, synthetic data, LLM applications |
| 🧠 Behavioral Shifts | User attitude changes, trust patterns, mental model shifts |
| 📊 Industry Signals | Hiring, team structures, research ops, maturity trends |
| 📚 Academic | Papers, CHI/CSCW proceedings, preprints, publications |

---

## Python API

```python
from research_radar.scanner import scan_text, build_signals
from research_radar.models import TrendReport, SignalStrength
from research_radar.reporter import render_markdown

# Rule-based scan
text = open("articles.txt").read()
results = scan_text(text, domain="AI in UX research")
signals = build_signals(results, domain="AI in UX research", min_strength=SignalStrength.LOW)

report = TrendReport(domain="AI in UX research", signals=signals)
print(render_markdown(report))

# LLM-powered live scan
from research_radar.llm import enrich_report
report = enrich_report(domain="payment UX", backend="anthropic")
```

---

## Output example (plain text)

```
RESEARCH RADAR — AI IN UX RESEARCH
============================================================
Signals: 8  |  Generated: 2026-06-27

[ METHODOLOGY ]
  ● Thematic Analysis in AI in UX research
    Teams pairing thematic analysis with LLM pre-coding...

[ TOOLING ]
  ◐ Dovetail in AI in UX research
    Dovetail released automated theme clustering in GA...

[ AI / LLM ]
  ● LLM in AI in UX research
    Synthetic participants generated by LLMs approximate...
```

---

## Part of the CPR Ecosystem

`research-radar` is Tool 22 in the [CPR Orbital Series](https://github.com/kgkazakos) — 40 open-source Python tools for AI-native product research infrastructure, shipping every Friday.

**Related tools:**
- [bias-audit](https://github.com/kgkazakos/bias-audit) (Tool 14) — detect interviewer bias across transcript corpora
- [say-do-lite](https://github.com/kgkazakos/say-do-lite) (Tool 13) — lightweight Say-Do Gap detection
- [research-rubric](https://github.com/kgkazakos/research-rubric) (Tool 6) — evaluate research quality across dimensions
- [evidence-chain](https://github.com/kgkazakos/evidence-chain) (Tool 23) — track claim-to-evidence provenance chains *(coming soon)*

---

## Development

```bash
git clone https://github.com/kgkazakos/research-radar
cd research-radar
pip install -e ".[all]"
pytest tests/ -v
ruff check research_radar/ tests/
```

---

## License

MIT © [Kostas Kazakos](https://github.com/kgkazakos)
