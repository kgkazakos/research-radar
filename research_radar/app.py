"""
research-radar · CPR Orbital Tool 22
Streamlit UI — visual radar dashboard for domain-specific research signals.

Run with:
    streamlit run research_radar/app.py
"""

from __future__ import annotations

import json

import streamlit as st

from .models import (
    CATEGORY_COLORS,
    CATEGORY_EMOJI,
    CATEGORY_LABELS,
    SignalCategory,
    SignalStrength,
    TrendReport,
)
from .reporter import render_markdown

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Research Radar · CPR",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
<style>
/* ---- Global ---- */
[data-testid="stAppViewContainer"] {
    background: #0f1117;
    color: #e8e8e8;
}
[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #30363d;
}
[data-testid="stSidebar"] * {
    color: #c9d1d9 !important;
}

/* ---- Header strip ---- */
.radar-header {
    background: linear-gradient(135deg, #1a1f2e 0%, #0f1117 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.radar-header h1 {
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    margin: 0;
    letter-spacing: -0.3px;
}
.radar-header p {
    font-size: 13px;
    color: #8b949e;
    margin: 4px 0 0;
}
.radar-icon {
    font-size: 36px;
    line-height: 1;
}

/* ---- Stat cards ---- */
.stat-row {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}
.stat-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px 18px;
    min-width: 110px;
    flex: 1;
}
.stat-card .label {
    font-size: 11px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.stat-card .value {
    font-size: 26px;
    font-weight: 700;
    color: #e6edf3;
}
.stat-card .sub {
    font-size: 11px;
    color: #8b949e;
    margin-top: 2px;
}

/* ---- Signal cards ---- */
.signal-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    border-left-width: 3px;
    position: relative;
}
.signal-title {
    font-size: 13px;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 5px;
    line-height: 1.3;
}
.signal-summary {
    font-size: 12px;
    color: #8b949e;
    line-height: 1.5;
    margin-bottom: 8px;
}
.signal-meta {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
}
.badge {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 99px;
    font-weight: 600;
    letter-spacing: 0.3px;
}
.badge-high   { background: #3d1515; color: #f85149; border: 1px solid #f851491a; }
.badge-medium { background: #2d1f00; color: #d29922; border: 1px solid #d299221a; }
.badge-low    { background: #1c2128; color: #8b949e; border: 1px solid #30363d; }
.kw-chip {
    font-size: 10px;
    background: #1c2128;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 1px 6px;
    color: #8b949e;
    font-family: monospace;
}

/* ---- Narrative box ---- */
.narrative-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 20px;
}
.narrative-box h3 {
    font-size: 13px;
    color: #58a6ff;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
}
.narrative-box p {
    font-size: 13px;
    color: #c9d1d9;
    line-height: 1.7;
    margin: 0;
}

/* ---- Category header ---- */
.cat-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 20px 0 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #30363d;
}
.cat-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}
.cat-label {
    font-size: 13px;
    font-weight: 600;
    color: #e6edf3;
}
.cat-count {
    font-size: 11px;
    color: #8b949e;
    background: #1c2128;
    border: 1px solid #30363d;
    border-radius: 99px;
    padding: 0 8px;
}

/* ---- Empty state ---- */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #8b949e;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-title { font-size: 16px; font-weight: 600; color: #e6edf3; margin-bottom: 6px; }
.empty-sub { font-size: 13px; }

/* ---- Source chips ---- */
.source-chip {
    font-size: 10px;
    color: #58a6ff;
    background: #0d2137;
    border: 1px solid #1f6feb33;
    border-radius: 4px;
    padding: 1px 7px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 📡 Research Radar")
    st.caption("CPR Orbital Series · Tool 22")
    st.divider()

    domain = st.text_input(
        "Domain",
        value="AI in UX research",
        placeholder="e.g. 'payment UX', 'enterprise B2B onboarding'",
        help="The research domain you want to monitor.",
    )

    st.markdown("**Scan mode**")
    mode = st.radio(
        "Scan mode",
        ["📄 Text file (rule-based)", "🌐 Live web scan (LLM)"],
        label_visibility="collapsed",
    )

    if "Text file" in mode:
        uploaded = st.file_uploader(
            "Upload text file",
            type=["txt", "md"],
            help="Paste articles, RSS export, or research notes as .txt",
        )
    else:
        st.info("Requires an LLM API key set in your environment.", icon="🔑")
        llm_backend = st.selectbox(
            "LLM backend",
            ["openai", "anthropic", "gemini"],
        )

    st.divider()
    st.markdown("**Filter categories**")
    selected_cats = []
    for cat in SignalCategory:
        label = f"{CATEGORY_EMOJI[cat]} {CATEGORY_LABELS[cat]}"
        if st.checkbox(label, value=True, key=f"cat_{cat.value}"):
            selected_cats.append(cat)

    st.divider()
    min_strength = st.select_slider(
        "Min. signal strength",
        options=["low", "medium", "high"],
        value="low",
    )

    run_btn = st.button("🔍 Run Radar Scan", use_container_width=True, type="primary")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
<div class="radar-header">
  <div class="radar-icon">📡</div>
  <div>
    <h1>Research Radar</h1>
    <p>Automated domain-specific signal monitor for product researchers · CPR Orbital Series #22</p>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Run scan
# ---------------------------------------------------------------------------


def _run_text_scan(text: str, domain_str: str, cats: list[SignalCategory], min_str: str) -> TrendReport:
    from .models import SignalStrength as SS
    from .scanner import build_signals, scan_text

    results = scan_text(text, domain=domain_str, categories=cats)
    signals = build_signals(results, domain=domain_str, min_strength=SS(min_str))
    return TrendReport(domain=domain_str, signals=signals, llm_enriched=False)


def _run_llm_scan(domain_str: str, cats: list[SignalCategory], backend: str) -> TrendReport:
    from .llm import enrich_report

    return enrich_report(domain=domain_str, backend=backend, categories=cats)


if "report" not in st.session_state:
    st.session_state.report = None

if run_btn:
    if not domain.strip():
        st.error("Please enter a domain.")
    elif not selected_cats:
        st.error("Select at least one category.")
    else:
        try:
            if "Text file" in mode:
                if uploaded is None:
                    st.error("Please upload a text file.")
                else:
                    text_content = uploaded.read().decode("utf-8")
                    with st.spinner(f"Scanning '{domain}' signals…"):
                        st.session_state.report = _run_text_scan(
                            text_content, domain, selected_cats, min_strength
                        )
            else:
                with st.spinner(f"Searching web + synthesising with {llm_backend}…"):
                    st.session_state.report = _run_llm_scan(domain, selected_cats, llm_backend)  # type: ignore[possibly-undefined]
        except ImportError as exc:
            st.error(
                f"Missing dependencies: {exc}\n\n"
                f"Install with: `pip install 'research-radar[{llm_backend}]'`"  # type: ignore[possibly-undefined]
            )
        except Exception as exc:
            st.error(f"Scan failed: {exc}")

# ---------------------------------------------------------------------------
# Display report
# ---------------------------------------------------------------------------

report: TrendReport | None = st.session_state.report

if report is None:
    st.markdown(
        """
<div class="empty-state">
  <div class="empty-icon">📡</div>
  <div class="empty-title">No scan yet</div>
  <div class="empty-sub">
    Upload a text file or enable live web scan,<br>
    choose a domain, and click <strong>Run Radar Scan</strong>.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
else:
    # ---------------------------------------------------------------- Stats
    high = len([s for s in report.signals if s.strength == SignalStrength.HIGH])
    med = len([s for s in report.signals if s.strength == SignalStrength.MEDIUM])
    low_ = len([s for s in report.signals if s.strength == SignalStrength.LOW])
    n_cats = len(report.by_category)

    st.markdown(
        f"""
<div class="stat-row">
  <div class="stat-card">
    <div class="label">Total signals</div>
    <div class="value">{report.signal_count}</div>
    <div class="sub">{n_cats} categories</div>
  </div>
  <div class="stat-card">
    <div class="label">🔴 High</div>
    <div class="value">{high}</div>
    <div class="sub">strong evidence</div>
  </div>
  <div class="stat-card">
    <div class="label">🟡 Medium</div>
    <div class="value">{med}</div>
    <div class="sub">emerging</div>
  </div>
  <div class="stat-card">
    <div class="label">⚪ Low</div>
    <div class="value">{low_}</div>
    <div class="sub">early signal</div>
  </div>
  <div class="stat-card">
    <div class="label">Source</div>
    <div class="value" style="font-size:16px;">{'🌐 Web' if report.llm_enriched else '📄 Text'}</div>
    <div class="sub">{'LLM-enriched' if report.llm_enriched else 'Rule-based'}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------- Narrative
    if report.narrative:
        st.markdown(
            f"""
<div class="narrative-box">
  <h3>📝 Weekly Digest — {report.domain}</h3>
  <p>{report.narrative}</p>
</div>
""",
            unsafe_allow_html=True,
        )

    # ---------------------------------------------------------------- Signals
    if not report.signals:
        st.info("No signals matched. Try a broader domain or lower the minimum strength.")
    else:
        # Two-column grid
        cats_present = list(report.by_category.keys())
        mid = (len(cats_present) + 1) // 2
        col_a, col_b = st.columns(2)

        for idx, cat in enumerate(cats_present):
            signals = report.by_category[cat]
            col = col_a if idx < mid else col_b
            color = CATEGORY_COLORS[cat]
            emoji = CATEGORY_EMOJI[cat]
            label = CATEGORY_LABELS[cat]

            with col:
                st.markdown(
                    f"""
<div class="cat-header">
  <div class="cat-dot" style="background:{color};"></div>
  <span class="cat-label">{emoji} {label}</span>
  <span class="cat-count">{len(signals)}</span>
</div>
""",
                    unsafe_allow_html=True,
                )
                for sig in signals:
                    strength_cls = f"badge-{sig.strength.value}"
                    kw_html = " ".join(
                        f'<span class="kw-chip">{kw}</span>'
                        for kw in sig.keywords_matched[:4]
                    )
                    src_html = " ".join(
                        f'<span class="source-chip">{src[:40]}</span>'
                        for src in sig.sources[:2]
                    )
                    st.markdown(
                        f"""
<div class="signal-card" style="border-left-color:{color};">
  <div class="signal-title">{sig.title}</div>
  <div class="signal-summary">{sig.summary[:200]}{'…' if len(sig.summary) > 200 else ''}</div>
  <div class="signal-meta">
    <span class="badge {strength_cls}">{sig.strength.value.upper()}</span>
    {kw_html}
    {src_html}
  </div>
</div>
""",
                        unsafe_allow_html=True,
                    )

    # ---------------------------------------------------------------- Actions
    st.divider()
    dl_col, md_col, _ = st.columns([1, 1, 3])

    with dl_col:
        st.download_button(
            "⬇ Download JSON",
            data=json.dumps(report.to_dict(), indent=2),
            file_name=f"radar_{report.domain.replace(' ', '_')[:30]}.json",
            mime="application/json",
        )
    with md_col:
        st.download_button(
            "⬇ Download Markdown",
            data=render_markdown(report),
            file_name=f"radar_{report.domain.replace(' ', '_')[:30]}.md",
            mime="text/markdown",
        )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    "<p style='text-align:center;color:#8b949e;font-size:11px;margin-top:40px;'>"
    "research-radar · CPR Orbital Series #22 · "
    "<a href='https://github.com/kgkazakos/research-radar' style='color:#58a6ff;'>GitHub</a>"
    "</p>",
    unsafe_allow_html=True,
)
