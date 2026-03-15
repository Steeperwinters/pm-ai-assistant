import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io, datetime, time

from agents import generate_scope, generate_risks, generate_wbs
from cpm_utils import calculate_cpm, plot_gantt

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Project — AI PM Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_KEY = st.secrets.get("GROQ_API_KEY", "")
if not API_KEY:
    st.error("API key not configured.")
    st.stop()

# ── Session state ──────────────────────────────────────────────────────────────
defaults = {
    "screen": "landing",       # landing | wizard | dashboard
    "wizard_step": 1,          # 1 | 2 | 3
    "project_name": "",
    "project_description": "",
    "constraints": "",
    "scope": None,
    "risks": None,
    "wbs_data": None,
    "cpm_results": None,
    "manual_tasks_list": None,
    "active_tab": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=Bebas+Neue&display=swap');

/* ── RESET & BASE ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, .stApp {
    background: #080808 !important;
    color: #e8e8e8 !important;
    font-family: 'Syne', sans-serif !important;
}

/* Hide streamlit chrome */
#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── TYPOGRAPHY SYSTEM ── */
h1, h2, h3 { font-family: 'Syne', sans-serif !important; }

.t-display {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: clamp(4rem, 10vw, 9rem);
    line-height: 0.95;
    letter-spacing: 0.02em;
    color: #ffffff;
}
.t-display .accent { color: #00ff87; }

.t-headline {
    font-family: 'Syne', sans-serif !important;
    font-size: 2rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
}

.t-label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #00ff87;
}

.t-body {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.875rem;
    color: #888;
    line-height: 1.7;
}

.t-mono {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.85rem;
    color: #ccc;
    line-height: 1.8;
}

/* ── INPUTS ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: #111 !important;
    border: 1px solid #222 !important;
    border-radius: 6px !important;
    color: #fff !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.9rem !important;
    padding: 0.75rem 1rem !important;
    transition: border-color 0.2s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #00ff87 !important;
    box-shadow: 0 0 0 2px #00ff8720 !important;
    outline: none !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: #333 !important;
}
.stTextInput label, .stTextArea label, .stNumberInput label, .stSelectbox label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: #555 !important;
    margin-bottom: 0.4rem !important;
}

/* ── BUTTONS (Streamlit native) ── */
.stButton > button {
    background: transparent !important;
    border: 1px solid #333 !important;
    border-radius: 6px !important;
    color: #ccc !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.2s !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    border-color: #00ff87 !important;
    color: #00ff87 !important;
    background: #00ff8708 !important;
}
.stButton > button[kind="primary"] {
    background: #00ff87 !important;
    border-color: #00ff87 !important;
    color: #000 !important;
    font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #00e676 !important;
    border-color: #00e676 !important;
    box-shadow: 0 0 24px #00ff8740 !important;
}
.stButton > button:disabled {
    opacity: 0.25 !important;
    cursor: not-allowed !important;
}

/* ── DOWNLOAD BUTTONS ── */
.stDownloadButton > button {
    background: transparent !important;
    border: 1px solid #333 !important;
    border-radius: 6px !important;
    color: #888 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
    border-color: #00ff87 !important;
    color: #00ff87 !important;
}

/* ── METRICS ── */
[data-testid="stMetric"] {
    background: #111 !important;
    border: 1px solid #1e1e1e !important;
    border-top: 2px solid #00ff87 !important;
    border-radius: 8px !important;
    padding: 1.2rem 1.4rem !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: #444 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    color: #fff !important;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #1a1a1a !important;
    gap: 0 !important;
    padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: #444 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    padding: 1rem 2rem !important;
    transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
    color: #fff !important;
    border-bottom: 2px solid #00ff87 !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #aaa !important; }
.stTabs [data-baseweb="tab-panel"] {
    background: transparent !important;
    padding-top: 0 !important;
}

/* ── DATAFRAME ── */
[data-testid="stDataFrame"] iframe {
    border-radius: 8px !important;
}

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background: #111 !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 6px !important;
    color: #888 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* ── RADIO ── */
.stRadio > div { gap: 1rem !important; }
.stRadio [data-baseweb="radio"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
    color: #888 !important;
}

/* ── ALERTS ── */
.stAlert {
    background: #111 !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
    border: 1px solid #1e1e1e !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #222; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #00ff87; }

/* ── DIVIDERS ── */
hr { border-color: #1a1a1a !important; margin: 2rem 0 !important; }

/* ── SPINNER ── */
.stSpinner > div { border-top-color: #00ff87 !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: nav buttons
# ══════════════════════════════════════════════════════════════════════════════
def go(screen, **kwargs):
    st.session_state.screen = screen
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — LANDING
# ══════════════════════════════════════════════════════════════════════════════
def render_landing():
    st.markdown("""
<style>
/* Landing-specific overrides */
.landing-wrap {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 2rem;
    position: relative;
    overflow: hidden;
}

/* Animated grid background */
.landing-wrap::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(#00ff8706 1px, transparent 1px),
        linear-gradient(90deg, #00ff8706 1px, transparent 1px);
    background-size: 60px 60px;
    mask-image: radial-gradient(ellipse 80% 60% at 50% 50%, black 40%, transparent 100%);
    pointer-events: none;
    z-index: 0;
}

/* Glowing orb */
.landing-wrap::after {
    content: '';
    position: fixed;
    width: 600px; height: 600px;
    background: radial-gradient(circle, #00ff8710 0%, transparent 70%);
    border-radius: 50%;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    pointer-events: none;
    z-index: 0;
    animation: pulse-orb 4s ease-in-out infinite;
}
@keyframes pulse-orb {
    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.6; }
    50%       { transform: translate(-50%, -50%) scale(1.1); opacity: 1; }
}

.landing-inner {
    position: relative;
    z-index: 1;
    text-align: center;
    max-width: 800px;
}

/* Terminal badge */
.term-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #00ff8712;
    border: 1px solid #00ff8730;
    border-radius: 100px;
    padding: 0.35rem 1rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.15em;
    color: #00ff87;
    margin-bottom: 2.5rem;
    text-transform: uppercase;
}
.term-badge .dot {
    width: 6px; height: 6px;
    background: #00ff87;
    border-radius: 50%;
    animation: blink-dot 1.2s step-end infinite;
}
@keyframes blink-dot {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
}

/* Big logo text */
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(5rem, 14vw, 10rem);
    line-height: 0.9;
    color: #fff;
    letter-spacing: 0.03em;
    margin-bottom: 0.2em;
    animation: fade-up 0.8s ease both;
}
.hero-title .accent { color: #00ff87; }

@keyframes fade-up {
    from { opacity: 0; transform: translateY(30px); }
    to   { opacity: 1; transform: translateY(0); }
}

.hero-sub {
    font-family: 'Syne', sans-serif;
    font-size: clamp(1rem, 2.5vw, 1.3rem);
    color: #555;
    font-weight: 400;
    margin-bottom: 3.5rem;
    animation: fade-up 0.8s 0.15s ease both;
    line-height: 1.5;
}
.hero-sub strong { color: #999; font-weight: 600; }

/* Terminal typing box */
.term-box {
    background: #0c0c0c;
    border: 1px solid #1e1e1e;
    border-radius: 12px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 2.5rem;
    text-align: left;
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    animation: fade-up 0.8s 0.3s ease both;
    position: relative;
    overflow: hidden;
}
.term-box::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, #00ff87, transparent);
}
.term-row { display: flex; gap: 0.5rem; margin: 0.2rem 0; }
.term-prompt { color: #00ff87; }
.term-cmd    { color: #ccc; }
.term-out    { color: #555; padding-left: 1rem; }
.term-cursor {
    display: inline-block;
    width: 7px; height: 1em;
    background: #00ff87;
    vertical-align: text-bottom;
    animation: blink-dot 0.9s step-end infinite;
    margin-left: 2px;
}

/* Feature pills */
.feature-row {
    display: flex;
    justify-content: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 3rem;
    animation: fade-up 0.8s 0.45s ease both;
}
.feature-pill {
    background: #111;
    border: 1px solid #222;
    border-radius: 100px;
    padding: 0.4rem 1rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    color: #666;
    letter-spacing: 0.08em;
}

/* CTA button (HTML version for landing) */
.cta-hint {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    color: #333;
    letter-spacing: 0.1em;
    margin-top: 1rem;
    animation: fade-up 0.8s 0.6s ease both;
}
</style>

<div class="landing-wrap">
  <div class="landing-inner">

    <div class="term-badge">
      <span class="dot"></span>
      AI Agent Online
    </div>

    <div class="hero-title">
      SMART<br><span class="accent">PROJECT</span>
    </div>

    <div class="hero-sub">
      The AI agent that turns your idea into a<br>
      <strong>complete project plan</strong> — in under 60 seconds.
    </div>

    <div class="term-box">
      <div class="term-row"><span class="term-prompt">→</span><span class="term-cmd">initializing smart_project.agent</span></div>
      <div class="term-row"><span class="term-out">✓ scope_planner     loaded</span></div>
      <div class="term-row"><span class="term-out">✓ risk_engine        loaded</span></div>
      <div class="term-row"><span class="term-out">✓ cpm_pert_analyzer  loaded</span></div>
      <div class="term-row"><span class="term-out">✓ wbs_builder        loaded</span></div>
      <div class="term-row"><span class="term-prompt">→</span><span class="term-cmd">status: ready<span class="term-cursor"></span></span></div>
    </div>

    <div class="feature-row">
      <span class="feature-pill">Scope Statement</span>
      <span class="feature-pill">Risk Register</span>
      <span class="feature-pill">Work Breakdown Structure</span>
      <span class="feature-pill">CPM / PERT Timeline</span>
      <span class="feature-pill">Gantt Chart</span>
    </div>

  </div>
</div>
""", unsafe_allow_html=True)

    # Centre the button
    col = st.columns([1, 2, 1])[1]
    with col:
        if st.button("▶  START YOUR PROJECT", type="primary", use_container_width=True):
            go("wizard", wizard_step=1)
    st.markdown('<div class="cta-hint" style="text-align:center;padding-bottom:3rem">No setup required · Powered by AI</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — WIZARD
# ══════════════════════════════════════════════════════════════════════════════
def render_wizard():
    step = st.session_state.wizard_step

    # ── Wrapper ──
    st.markdown("""
<style>
.wizard-wrap {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 1rem;
    position: relative;
}
.wizard-wrap::before {
    content: '';
    position: fixed; inset: 0;
    background-image:
        linear-gradient(#00ff8705 1px, transparent 1px),
        linear-gradient(90deg, #00ff8705 1px, transparent 1px);
    background-size: 60px 60px;
    mask-image: radial-gradient(ellipse 60% 60% at 50% 30%, black 40%, transparent 100%);
    pointer-events: none; z-index: 0;
}
.wizard-card {
    position: relative; z-index: 1;
    background: #0c0c0c;
    border: 1px solid #1e1e1e;
    border-radius: 16px;
    padding: 3rem;
    width: 100%;
    max-width: 620px;
}
.wizard-card::before {
    content: '';
    position: absolute;
    top: 0; left: 10%; right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, #00ff87, transparent);
}
.step-indicator {
    display: flex; align-items: center; gap: 0;
    margin-bottom: 2.5rem;
}
.step-dot {
    width: 28px; height: 28px;
    border-radius: 50%;
    border: 1.5px solid #222;
    display: flex; align-items: center; justify-content: center;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    color: #444;
    transition: all 0.3s;
}
.step-dot.active {
    border-color: #00ff87;
    background: #00ff8715;
    color: #00ff87;
}
.step-dot.done {
    border-color: #00ff87;
    background: #00ff87;
    color: #000;
    font-weight: 700;
}
.step-line {
    flex: 1; height: 1px;
    background: #1e1e1e;
    transition: background 0.3s;
}
.step-line.done { background: #00ff8740; }
.wizard-step-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #00ff87;
    margin-bottom: 0.6rem;
}
.wizard-step-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: #fff;
    margin-bottom: 0.4rem;
    line-height: 1.15;
}
.wizard-step-hint {
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    color: #444;
    margin-bottom: 2rem;
    line-height: 1.6;
}
</style>
<div class="wizard-wrap">
""", unsafe_allow_html=True)

    # ── Step indicator HTML ──
    s1 = "done" if step > 1 else ("active" if step == 1 else "")
    s2 = "done" if step > 2 else ("active" if step == 2 else "")
    s3 = "done" if step > 3 else ("active" if step == 3 else "")
    l1 = "done" if step > 1 else ""
    l2 = "done" if step > 2 else ""

    st.markdown(f"""
<div style="position:relative;z-index:1;width:100%;max-width:620px;margin:0 auto 0">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.4rem">
    <span style="font-family:'DM Mono',monospace;font-size:0.62rem;color:#333;letter-spacing:0.1em">STEP {step} OF 3</span>
    <span style="font-family:'DM Mono',monospace;font-size:0.62rem;color:#333;letter-spacing:0.1em">SMART PROJECT</span>
  </div>
</div>
<div style="position:relative;z-index:1;width:100%;max-width:620px;margin:0 auto 1.5rem">
  <div class="step-indicator">
    <div class="step-dot {s1}">{"✓" if step > 1 else "1"}</div>
    <div class="step-line {l1}"></div>
    <div class="step-dot {s2}">{"✓" if step > 2 else "2"}</div>
    <div class="step-line {l2}"></div>
    <div class="step-dot {s3}">3</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Card wrapper (use columns to center) ──
    _, col, _ = st.columns([1, 4, 1])
    with col:
        st.markdown('<div class="wizard-card">', unsafe_allow_html=True)

        # ── STEP 1: Project Name ──────────────────────────────────────────────
        if step == 1:
            st.markdown("""
<div class="wizard-step-label">Step 01 / Name</div>
<div class="wizard-step-title">What's your<br>project called?</div>
<div class="wizard-step-hint">Give it a clear, recognisable name. This will appear across all generated documents.</div>
""", unsafe_allow_html=True)
            name = st.text_input(
                "PROJECT NAME",
                value=st.session_state.project_name,
                placeholder="e.g.  Hospital Management System",
                key="w_name",
            )
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("← Back to Home", use_container_width=True):
                    go("landing")
            with c2:
                if st.button("Continue →", type="primary", use_container_width=True):
                    if name.strip():
                        st.session_state.project_name = name.strip()
                        go("wizard", wizard_step=2)
                    else:
                        st.warning("Please enter a project name.")

        # ── STEP 2: Description ───────────────────────────────────────────────
        elif step == 2:
            st.markdown(f"""
<div class="wizard-step-label">Step 02 / Description</div>
<div class="wizard-step-title">Tell the agent<br>about <span style="color:#00ff87">{st.session_state.project_name}</span></div>
<div class="wizard-step-hint">Describe what you are building, who it is for, and what success looks like. The more detail, the better the output.</div>
""", unsafe_allow_html=True)
            desc = st.text_area(
                "PROJECT DESCRIPTION",
                value=st.session_state.project_description,
                placeholder=(
                    "Describe your project in detail...\n\n"
                    "• What are you building?\n"
                    "• Who is it for?\n"
                    "• What are the main goals?\n"
                    "• Any known tech stack or approach?"
                ),
                height=200,
                key="w_desc",
            )
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("← Back", use_container_width=True):
                    go("wizard", wizard_step=1)
            with c2:
                if st.button("Continue →", type="primary", use_container_width=True):
                    if desc.strip():
                        st.session_state.project_description = desc.strip()
                        go("wizard", wizard_step=3)
                    else:
                        st.warning("Please add a description.")

        # ── STEP 3: Constraints ───────────────────────────────────────────────
        elif step == 3:
            st.markdown(f"""
<div class="wizard-step-label">Step 03 / Constraints</div>
<div class="wizard-step-title">Set your<br>boundaries</div>
<div class="wizard-step-hint">Define budget, timeline, team size, and any technical or regulatory limits. These shape the scope and risks the AI will generate.</div>
""", unsafe_allow_html=True)

            r1c1, r1c2 = st.columns(2)
            with r1c1:
                budget = st.text_input("BUDGET", placeholder="e.g.  $500,000", key="w_budget")
            with r1c2:
                timeline = st.text_input("TIMELINE", placeholder="e.g.  6 months", key="w_timeline")

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                team = st.text_input("TEAM SIZE", placeholder="e.g.  8 people", key="w_team")
            with r2c2:
                tech = st.text_input("TECH / PLATFORM", placeholder="e.g.  Python, AWS", key="w_tech")

            other = st.text_area(
                "OTHER CONSTRAINTS",
                placeholder="Regulatory requirements, legacy systems, geographic limits...",
                height=90,
                key="w_other",
            )

            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("← Back", use_container_width=True):
                    go("wizard", wizard_step=2)
            with c2:
                if st.button("▶  LAUNCH AGENT", type="primary", use_container_width=True):
                    parts = []
                    if budget:   parts.append(f"Budget: {budget}")
                    if timeline: parts.append(f"Timeline: {timeline}")
                    if team:     parts.append(f"Team size: {team}")
                    if tech:     parts.append(f"Technology: {tech}")
                    if other:    parts.append(f"Other: {other}")
                    st.session_state.constraints = "\n".join(parts)
                    go("dashboard")

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def render_dashboard():
    pname = st.session_state.project_name
    full_description = (
        st.session_state.project_description
        + ("\n\nConstraints:\n" + st.session_state.constraints if st.session_state.constraints else "")
    )

    # ── Top nav bar ────────────────────────────────────────────────────────────
    st.markdown(f"""
<style>
.dash-topbar {{
    position: sticky; top: 0; z-index: 999;
    background: #080808ee;
    backdrop-filter: blur(12px);
    border-bottom: 1px solid #1a1a1a;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.8rem 2.5rem;
}}
.dash-brand {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.4rem;
    color: #fff;
    letter-spacing: 0.08em;
}}
.dash-brand span {{ color: #00ff87; }}
.dash-project {{
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #444;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}
.dash-project strong {{
    color: #00ff87;
    font-weight: 500;
}}
.dash-content {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 2.5rem 2rem;
}}
.section-label {{
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #00ff87;
    margin-bottom: 0.6rem;
}}
.section-title {{
    font-family: 'Syne', sans-serif;
    font-size: 1.5rem;
    font-weight: 800;
    color: #fff;
    margin-bottom: 1.5rem;
    letter-spacing: -0.01em;
}}
.result-panel {{
    background: #0c0c0c;
    border: 1px solid #1a1a1a;
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
}}
.result-panel p, .result-panel li {{
    font-family: 'DM Mono', monospace !important;
    font-size: 0.85rem !important;
    color: #aaa !important;
    line-height: 1.85 !important;
}}
.result-panel h2 {{
    font-family: 'Syne', sans-serif !important;
    font-size: 1.2rem !important;
    font-weight: 800 !important;
    color: #fff !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.6rem !important;
    border-bottom: 1px solid #1a1a1a;
    padding-bottom: 0.4rem;
}}
.result-panel h3 {{
    font-family: 'Syne', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    color: #00ff87 !important;
    margin-top: 1.2rem !important;
    margin-bottom: 0.4rem !important;
}}
.result-panel strong {{
    color: #ddd !important;
    font-weight: 600 !important;
}}
.action-row {{
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 2rem;
}}
.status-badge {{
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: #00ff8710; border: 1px solid #00ff8730;
    border-radius: 100px; padding: 0.25rem 0.8rem;
    font-family: 'DM Mono', monospace; font-size: 0.65rem;
    color: #00ff87; letter-spacing: 0.1em; text-transform: uppercase;
}}
.status-badge .dot {{
    width: 5px; height: 5px; background: #00ff87;
    border-radius: 50%; animation: blink-dot 1.2s step-end infinite;
}}
.warn-panel {{
    background: #0f0a00;
    border: 1px solid #332200;
    border-left: 3px solid #ffb300;
    border-radius: 8px;
    padding: 1rem 1.4rem;
    margin-bottom: 2rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    color: #886622;
    line-height: 1.7;
}}
.warn-panel strong {{ color: #ffb300; }}
.cp-badge {{
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    color: #00ff87;
    background: #00ff8710;
    border: 1px solid #00ff8720;
    border-radius: 6px;
    padding: 0.5rem 1rem;
    margin-bottom: 1.5rem;
    display: inline-block;
    letter-spacing: 0.04em;
}}
</style>

<div class="dash-topbar">
  <div class="dash-brand">SMART <span>PROJECT</span></div>
  <div class="dash-project">Active: <strong>{pname}</strong></div>
</div>
""", unsafe_allow_html=True)

    # ── Main content ───────────────────────────────────────────────────────────
    st.markdown('<div class="dash-content">', unsafe_allow_html=True)

    # ── Generate buttons row ───────────────────────────────────────────────────
    st.markdown('<div class="section-label">Agent Controls</div>', unsafe_allow_html=True)

    g1, g2, g3 = st.columns([2, 2, 4])
    with g1:
        scope_btn = st.button("▶  Generate Scope", type="primary", use_container_width=True)
    with g2:
        risk_btn = st.button("▶  Generate Risks", use_container_width=True)
    with g3:
        if st.button("← New Project", use_container_width=True):
            for k in ["scope","risks","wbs_data","cpm_results","project_name",
                      "project_description","constraints","manual_tasks_list"]:
                st.session_state[k] = None if k != "project_name" else ""
            go("landing")

    if scope_btn:
        with st.spinner("Agent processing — generating scope statement..."):
            try:
                scope = generate_scope(API_KEY, pname, full_description)
                st.session_state.scope = scope
                st.session_state.risks = None
                st.session_state.wbs_data = None
                st.session_state.cpm_results = None
                st.success("✓ Scope Statement generated")
            except Exception as e:
                st.error(f"Error: {e}")

    if risk_btn:
        if not st.session_state.scope:
            st.warning("Generate a Scope Statement first.")
        else:
            with st.spinner("Agent processing — mapping risks..."):
                try:
                    risks = generate_risks(API_KEY, st.session_state.scope)
                    st.session_state.risks = risks
                    st.session_state.wbs_data = None
                    st.session_state.cpm_results = None
                    st.success("✓ Risk Register compiled")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "Scope Statement",
        "Risk Register",
        "WBS & CPM / PERT",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — SCOPE
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.scope:
            st.markdown('<div class="section-label">Output</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Scope Statement</div>', unsafe_allow_html=True)

            st.markdown(f'<div class="result-panel">{st.session_state.scope}</div>',
                        unsafe_allow_html=True)

            st.download_button(
                "↓  Download Scope (.txt)",
                data=st.session_state.scope,
                file_name=f"{pname}_scope_statement.txt",
                mime="text/plain",
            )
        else:
            _empty_state("Scope Statement", "Click ▶ Generate Scope above to produce a full scope statement for this project.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — RISKS
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.risks:
            risks = st.session_state.risks
            high = sum(1 for r in risks if r["risk_score"] == "High")
            med  = sum(1 for r in risks if r["risk_score"] == "Medium")
            low  = sum(1 for r in risks if r["risk_score"] == "Low")

            st.markdown('<div class="section-label">Overview</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Risk Register</div>', unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total", len(risks))
            c2.metric("Critical", high)
            c3.metric("Moderate", med)
            c4.metric("Low", low)

            st.markdown("<br>", unsafe_allow_html=True)

            def _rc(val):
                return {
                    "High":   "background-color:#1a0000;color:#ff6b6b;font-weight:600",
                    "Medium": "background-color:#140d00;color:#ffc107;font-weight:600",
                    "Low":    "background-color:#001a0a;color:#00c853;font-weight:600",
                }.get(val, "")

            df = pd.DataFrame(risks).rename(columns={
                "risk_id": "ID", "risk_name": "Risk",
                "category": "Category", "description": "Description",
                "likelihood": "Likelihood", "impact": "Impact",
                "risk_score": "Score", "mitigation_strategy": "Mitigation",
            })
            st.dataframe(
                df.style.applymap(_rc, subset=["Likelihood", "Impact", "Score"]),
                use_container_width=True, height=420,
            )
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                "↓  Download Risk Register (.csv)",
                data=df.to_csv(index=False),
                file_name=f"{pname}_risk_register.csv",
                mime="text/csv",
            )
        elif st.session_state.scope:
            _empty_state("Risk Register", "Scope is ready. Click ▶ Generate Risks above.")
        else:
            _empty_state("Risk Register", "Generate a Scope Statement first, then generate risks.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — WBS & CPM
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)

        if not st.session_state.risks:
            _empty_state("WBS & CPM / PERT", "Complete the Scope and Risk steps first.")
        else:
            st.markdown("""
<div class="warn-panel">
  <strong>⚠ Disclaimer</strong><br>
  AI-generated timelines and WBS are rough planning estimates only.
  Real delivery depends on team experience, resource availability, vendor timelines,
  regulatory approvals, and many other factors no AI can fully predict.
  Always validate with your team before presenting to stakeholders.
</div>
""", unsafe_allow_html=True)

            st.markdown('<div class="section-label">Build Mode</div>', unsafe_allow_html=True)
            mode = st.radio(
                "",
                ["🤖  AI — Auto-generate WBS & Timeline",
                 "✏️  Manual — Enter tasks myself"],
                horizontal=True,
                label_visibility="collapsed",
            )

            # ── AI MODE ───────────────────────────────────────────────────────
            if mode.startswith("🤖"):
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("▶  Build WBS + Critical Path", type="primary"):
                    with st.spinner("Agent building work breakdown structure..."):
                        try:
                            wbs_data = generate_wbs(API_KEY, st.session_state.scope, pname)
                            st.session_state.wbs_data = wbs_data
                            G, rdf, dur, cp = calculate_cpm(wbs_data["tasks"])
                            st.session_state.cpm_results = {
                                "G": G, "df": rdf, "duration": dur,
                                "critical_path": cp, "tasks": wbs_data["tasks"],
                            }
                            st.success("✓ WBS and CPM/PERT analysis complete")
                        except Exception as e:
                            st.error(f"Error: {e}")

            # ── MANUAL MODE ───────────────────────────────────────────────────
            else:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-label">Task Input</div>', unsafe_allow_html=True)
                st.caption("Task IDs: T1, T2, T3 …  |  Durations in DAYS  |  Dependencies: comma-separated (e.g. T1, T2)")

                if st.session_state.manual_tasks_list is None:
                    st.session_state.manual_tasks_list = [
                        {"task_id": f"T{i+1}", "task_name": "",
                         "optimistic": 1, "most_likely": 3, "pessimistic": 6,
                         "dependencies": ""}
                        for i in range(4)
                    ]

                if st.button("+ Add Task"):
                    n = len(st.session_state.manual_tasks_list) + 1
                    st.session_state.manual_tasks_list.append({
                        "task_id": f"T{n}", "task_name": "",
                        "optimistic": 1, "most_likely": 3, "pessimistic": 6,
                        "dependencies": "",
                    })

                updated = []
                for i, task in enumerate(st.session_state.manual_tasks_list):
                    label = task["task_name"] or f"Task {i+1}"
                    with st.expander(f"{task['task_id']} — {label}", expanded=(i < 2)):
                        ca, cb = st.columns([1, 3])
                        tid   = ca.text_input("ID",          value=task["task_id"],   key=f"tid_{i}")
                        tname = cb.text_input("Task Name",   value=task["task_name"], key=f"tn_{i}")
                        cc, cd, ce, cf = st.columns(4)
                        opt  = cc.number_input("Optimistic",  min_value=1, value=int(task["optimistic"]),  key=f"op_{i}")
                        ml   = cd.number_input("Most Likely", min_value=1, value=int(task["most_likely"]), key=f"ml_{i}")
                        pess = ce.number_input("Pessimistic", min_value=1, value=int(task["pessimistic"]), key=f"pe_{i}")
                        deps = cf.text_input("Dependencies",  value=task["dependencies"],                  key=f"dp_{i}")
                        updated.append({"task_id": tid.strip(), "task_name": tname.strip(),
                                        "optimistic": opt, "most_likely": ml,
                                        "pessimistic": pess, "dependencies": deps})

                st.session_state.manual_tasks_list = updated

                if st.button("▶  Calculate CPM / PERT", type="primary"):
                    parsed = [
                        {**t, "dependencies": [d.strip() for d in t["dependencies"].split(",") if d.strip()]}
                        for t in updated if t["task_name"] and t["task_id"]
                    ]
                    if len(parsed) < 2:
                        st.warning("Enter at least 2 named tasks.")
                    else:
                        try:
                            G, rdf, dur, cp = calculate_cpm(parsed)
                            st.session_state.cpm_results = {
                                "G": G, "df": rdf, "duration": dur,
                                "critical_path": cp, "tasks": parsed,
                            }
                            st.session_state.wbs_data = None
                            st.success("✓ CPM/PERT analysis complete")
                        except Exception as e:
                            st.error(f"Error: {e}")

            # ── WBS TREE ──────────────────────────────────────────────────────
            if st.session_state.wbs_data:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-label">Work Breakdown Structure</div>', unsafe_allow_html=True)
                st.markdown('<div class="section-title">WBS Tree</div>', unsafe_allow_html=True)

                icons   = {1: "▣", 2: "▷", 3: "·"}
                colours = {1: "#fff", 2: "#ccc", 3: "#666"}
                weights = {1: "800", 2: "600", 3: "400"}
                sizes   = {1: "0.95rem", 2: "0.85rem", 3: "0.8rem"}
                rows = ""
                for item in st.session_state.wbs_data["wbs"]:
                    indent = "&nbsp;" * 8 * (item["level"] - 1)
                    ic = icons.get(item["level"], "·")
                    co = colours.get(item["level"], "#666")
                    fw = weights.get(item["level"], "400")
                    fs = sizes.get(item["level"], "0.8rem")
                    dot = '<span style="color:#00ff87;margin-right:0.4rem">·</span>' if item["level"] == 1 else ""
                    rows += (
                        f'<div style="font-family:DM Mono,monospace;color:{co};'
                        f'font-weight:{fw};font-size:{fs};'
                        f'padding:0.22rem 0;letter-spacing:0.02em">'
                        f'{indent}{dot}{ic} <span style="color:#444;margin-right:0.4rem">{item["id"]}</span>{item["name"]}</div>\n'
                    )
                st.markdown(
                    f'<div class="result-panel" style="padding:1.5rem 2rem">{rows}</div>',
                    unsafe_allow_html=True,
                )

            # ── CPM RESULTS ───────────────────────────────────────────────────
            if st.session_state.cpm_results:
                cpm = st.session_state.cpm_results
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-label">Analysis</div>', unsafe_allow_html=True)
                st.markdown('<div class="section-title">CPM / PERT Results</div>', unsafe_allow_html=True)

                m1, m2, m3 = st.columns(3)
                m1.metric("Estimated Duration", f"{cpm['duration']:.1f} days")
                m2.metric("Critical Tasks",      len(cpm["critical_path"]))
                m3.metric("Total Tasks",         len(cpm["tasks"]))

                st.markdown("<br>", unsafe_allow_html=True)
                cp_str = " → ".join(cpm["critical_path"])
                st.markdown(
                    f'<div class="cp-badge">Critical Path: {cp_str}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown('<div class="section-label" style="margin-top:1.5rem">Task Table</div>', unsafe_allow_html=True)

                def _hl(row):
                    if row["Critical"] == "✅ Yes":
                        return ["background-color:#1a0000;color:#ff8888"] * len(row)
                    return ["background-color:#0c0c0c;color:#888"] * len(row)

                st.dataframe(
                    cpm["df"].style.apply(_hl, axis=1),
                    use_container_width=True, height=380,
                )

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-label">Gantt Chart</div>', unsafe_allow_html=True)
                fig = plot_gantt(cpm["G"], cpm["tasks"])
                st.pyplot(fig)
                plt.close(fig)

                # ── FULL REPORT ────────────────────────────────────────────────
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)

                report = "\n".join([
                    "=" * 64,
                    f"  SMART PROJECT — FULL REPORT",
                    f"  Project  : {pname}",
                    f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    "=" * 64, "",
                    "SCOPE STATEMENT", "-" * 64,
                    st.session_state.scope or "", "",
                    "RISK REGISTER", "-" * 64,
                ] + [
                    f"[{r['risk_id']}] {r['risk_name']}  |  {r['risk_score']}  |  "
                    f"Likelihood: {r['likelihood']}  Impact: {r['impact']}\n"
                    f"     Mitigation: {r['mitigation_strategy']}\n"
                    for r in (st.session_state.risks or [])
                ] + [
                    "CPM / PERT SUMMARY", "-" * 64,
                    f"Duration      : {cpm['duration']:.1f} days",
                    f"Critical Path : {cp_str}", "",
                    "TASK TABLE", "-" * 64,
                ] + [
                    f"{row['Task ID']} | {row['Task Name']:<30} | PERT:{row['PERT Duration (d)']}d"
                    f" | ES:{row['ES']} EF:{row['EF']} Float:{row['Float']} | {row['Critical']}"
                    for _, row in cpm["df"].iterrows()
                ] + [
                    "", "=" * 64,
                    "  Disclaimer: AI-generated estimates. Validate before use.",
                    "=" * 64,
                ])

                dl1, dl2, dl3, _ = st.columns([2, 2, 2, 2])
                dl1.download_button(
                    "↓  Full Report (.txt)", data=report,
                    file_name=f"{pname}_full_report.txt", mime="text/plain",
                )
                dl2.download_button(
                    "↓  CPM Table (.csv)", data=cpm["df"].to_csv(index=False),
                    file_name=f"{pname}_cpm.csv", mime="text/csv",
                )
                buf = io.BytesIO()
                fig2 = plot_gantt(cpm["G"], cpm["tasks"])
                fig2.savefig(buf, format="png", dpi=150,
                             bbox_inches="tight", facecolor="#0e1117")
                plt.close(fig2)
                buf.seek(0)
                dl3.download_button(
                    "↓  Gantt (.png)", data=buf,
                    file_name=f"{pname}_gantt.png", mime="image/png",
                )

    st.markdown('</div>', unsafe_allow_html=True)   # dash-content


def _empty_state(title, hint):
    st.markdown(f"""
<div style="
    text-align:center; padding: 4rem 2rem;
    border: 1px dashed #1e1e1e; border-radius: 12px;
    margin-top: 1rem;
">
  <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#2a2a2a;margin-bottom:0.5rem">{title}</div>
  <div style="font-family:'DM Mono',monospace;font-size:0.78rem;color:#2a2a2a">{hint}</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
screen = st.session_state.screen
if screen == "landing":
    render_landing()
elif screen == "wizard":
    render_wizard()
elif screen == "dashboard":
    render_dashboard()
