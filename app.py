import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import datetime

from agents import generate_scope, generate_risks, generate_wbs
from cpm_utils import calculate_cpm, plot_gantt

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SMART PROJECT — AI Agent",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load API key ───────────────────────────────────────────────────────────────
API_KEY = st.secrets.get("GROQ_API_KEY", "")
if not API_KEY:
    st.error("⚠️ API key not configured. Contact the administrator.")
    st.stop()

# ── CYBERPUNK CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=VT323&display=swap');

/* ── GLOBAL RESET ── */
*, *::before, *::after { box-sizing: border-box; }

/* ── ROOT VARS ── */
:root {
    --neon-green:  #00ff41;
    --neon-cyan:   #00e5ff;
    --neon-pink:   #ff0080;
    --neon-yellow: #ffe600;
    --dark-bg:     #000000;
    --panel-bg:    #060606;
    --panel-border:#0a2a0a;
    --text-dim:    #4a7c59;
    --text-mid:    #00cc33;
    --scanline: rgba(0,255,65,0.03);
}

/* ── APP BACKGROUND ── */
.stApp {
    background-color: var(--dark-bg) !important;
    background-image:
        repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            var(--scanline) 2px,
            var(--scanline) 4px
        ) !important;
    font-family: 'Share Tech Mono', monospace !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background-color: #020c02 !important;
    border-right: 1px solid #00ff4133 !important;
}
[data-testid="stSidebar"] * {
    font-family: 'Share Tech Mono', monospace !important;
    color: var(--neon-green) !important;
}
[data-testid="stSidebar"] .stMarkdown p {
    color: var(--text-mid) !important;
    font-size: 0.8rem !important;
}

/* ── ALL TEXT ── */
.stApp p, .stApp li, .stApp span, .stApp div,
.stApp label, .stApp .stMarkdown {
    font-family: 'Share Tech Mono', monospace !important;
    color: #aaffcc !important;
}

h1, h2, h3, h4 {
    font-family: 'Orbitron', monospace !important;
    color: var(--neon-green) !important;
    letter-spacing: 0.08em !important;
}

/* ── INPUTS ── */
.stTextInput input, .stTextArea textarea {
    background-color: #000800 !important;
    border: 1px solid #00ff4155 !important;
    border-radius: 0 !important;
    color: var(--neon-green) !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.9rem !important;
    caret-color: var(--neon-green) !important;
    outline: none !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--neon-green) !important;
    box-shadow: 0 0 12px #00ff4144 !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: #1a4d2a !important;
}

/* ── LABELS ── */
.stTextInput label, .stTextArea label, .stNumberInput label,
.stSelectbox label, .stRadio label {
    color: var(--neon-cyan) !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

/* ── BUTTONS ── */
.stButton > button {
    background: transparent !important;
    border: 1px solid var(--neon-green) !important;
    border-radius: 0 !important;
    color: var(--neon-green) !important;
    font-family: 'Orbitron', monospace !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1rem !important;
    transition: all 0.15s ease !important;
    position: relative !important;
    overflow: hidden !important;
}
.stButton > button:hover {
    background: #00ff4115 !important;
    box-shadow: 0 0 20px #00ff4155, inset 0 0 20px #00ff4108 !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"] {
    border-color: var(--neon-cyan) !important;
    color: var(--neon-cyan) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #00e5ff15 !important;
    box-shadow: 0 0 20px #00e5ff55 !important;
    color: #ffffff !important;
}
.stButton > button:disabled {
    opacity: 0.3 !important;
    cursor: not-allowed !important;
}

/* ── DOWNLOAD BUTTONS ── */
.stDownloadButton > button {
    background: transparent !important;
    border: 1px solid var(--neon-yellow) !important;
    border-radius: 0 !important;
    color: var(--neon-yellow) !important;
    font-family: 'Orbitron', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
.stDownloadButton > button:hover {
    background: #ffe60015 !important;
    box-shadow: 0 0 16px #ffe60055 !important;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #00ff4133 !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: var(--text-dim) !important;
    font-family: 'Orbitron', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
    color: var(--neon-green) !important;
    border-bottom: 2px solid var(--neon-green) !important;
    text-shadow: 0 0 10px var(--neon-green) !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--neon-green) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent !important;
    padding-top: 1.5rem !important;
}

/* ── METRICS ── */
[data-testid="stMetric"] {
    background: #000a00 !important;
    border: 1px solid #00ff4122 !important;
    border-left: 3px solid var(--neon-green) !important;
    padding: 0.8rem 1rem !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-dim) !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}
[data-testid="stMetricValue"] {
    color: var(--neon-green) !important;
    font-family: 'Orbitron', monospace !important;
    font-size: 1.4rem !important;
    text-shadow: 0 0 10px var(--neon-green) !important;
}

/* ── DATAFRAME ── */
[data-testid="stDataFrame"] {
    border: 1px solid #00ff4122 !important;
}
.dvn-scroller { background: #000800 !important; }

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background: #000a00 !important;
    border: 1px solid #00ff4122 !important;
    border-radius: 0 !important;
    color: var(--neon-green) !important;
    font-family: 'Share Tech Mono', monospace !important;
}
.streamlit-expanderContent {
    background: #000500 !important;
    border: 1px solid #00ff4111 !important;
    border-top: none !important;
}

/* ── ALERTS / INFO ── */
.stAlert {
    background: #000a00 !important;
    border: 1px solid #00ff4133 !important;
    border-radius: 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
}

/* ── RADIO ── */
.stRadio [data-baseweb="radio"] {
    font-family: 'Share Tech Mono', monospace !important;
    color: var(--neon-green) !important;
}

/* ── NUMBER INPUT ── */
.stNumberInput input {
    background: #000800 !important;
    border: 1px solid #00ff4133 !important;
    border-radius: 0 !important;
    color: var(--neon-green) !important;
    font-family: 'Share Tech Mono', monospace !important;
}

/* ── SPINNER ── */
.stSpinner > div {
    border-top-color: var(--neon-green) !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #00ff4133; }
::-webkit-scrollbar-thumb:hover { background: var(--neon-green); }

/* ── CUSTOM COMPONENTS ── */
.cyber-header {
    border: 1px solid #00ff4133;
    padding: 2.5rem 2rem 2rem;
    margin-bottom: 2rem;
    position: relative;
    background: #000500;
    overflow: hidden;
}
.cyber-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--neon-green), var(--neon-cyan), transparent);
    animation: scanH 3s linear infinite;
}
.cyber-header::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, #00ff4133, transparent);
}
@keyframes scanH {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

.cyber-logo {
    font-family: 'Orbitron', monospace;
    font-size: 3rem;
    font-weight: 900;
    color: var(--neon-green);
    text-shadow: 0 0 20px var(--neon-green), 0 0 60px #00ff4155;
    letter-spacing: 0.2em;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.cyber-logo span { color: var(--neon-cyan); }

.cyber-tagline {
    font-family: 'Share Tech Mono', monospace;
    color: var(--text-mid);
    font-size: 0.85rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

.cyber-desc {
    font-family: 'Share Tech Mono', monospace;
    color: #4a9960;
    font-size: 0.78rem;
    letter-spacing: 0.05em;
    border-left: 2px solid var(--neon-green);
    padding-left: 1rem;
    line-height: 1.8;
}

.tag-pill {
    display: inline-block;
    border: 1px solid var(--neon-cyan);
    color: var(--neon-cyan);
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    padding: 0.15rem 0.6rem;
    margin-right: 0.4rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.corner-tl {
    position: absolute;
    top: 8px; left: 8px;
    width: 16px; height: 16px;
    border-top: 2px solid var(--neon-green);
    border-left: 2px solid var(--neon-green);
}
.corner-tr {
    position: absolute;
    top: 8px; right: 8px;
    width: 16px; height: 16px;
    border-top: 2px solid var(--neon-green);
    border-right: 2px solid var(--neon-green);
}
.corner-bl {
    position: absolute;
    bottom: 8px; left: 8px;
    width: 16px; height: 16px;
    border-bottom: 2px solid var(--neon-green);
    border-left: 2px solid var(--neon-green);
}
.corner-br {
    position: absolute;
    bottom: 8px; right: 8px;
    width: 16px; height: 16px;
    border-bottom: 2px solid var(--neon-green);
    border-right: 2px solid var(--neon-green);
}

.section-head {
    font-family: 'Orbitron', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--neon-cyan);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    border-bottom: 1px solid #00e5ff22;
    padding-bottom: 0.5rem;
    margin: 1.5rem 0 1rem;
}

.warn-cyber {
    background: #0a0400;
    border: 1px solid #ffe60033;
    border-left: 3px solid var(--neon-yellow);
    padding: 1rem 1.2rem;
    margin: 1rem 0 1.5rem;
    font-family: 'Share Tech Mono', monospace;
    color: #ffe600aa;
    font-size: 0.8rem;
    line-height: 1.7;
    position: relative;
}
.warn-cyber strong { color: var(--neon-yellow); }

.status-ok   { color: var(--neon-green)  !important; }
.status-pend { color: #1a3a1a            !important; }

.prompt-line {
    font-family: 'VT323', monospace;
    color: var(--neon-green);
    font-size: 1rem;
    letter-spacing: 0.05em;
}
.prompt-line::before { content: '> '; color: var(--neon-cyan); }

@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
}
.cursor {
    display: inline-block;
    width: 8px; height: 1em;
    background: var(--neon-green);
    animation: blink 1s step-end infinite;
    vertical-align: text-bottom;
    margin-left: 2px;
}

@keyframes glitch {
    0%  { text-shadow: 0 0 20px var(--neon-green), 0 0 60px #00ff4155; transform: translate(0); }
    2%  { text-shadow: -2px 0 var(--neon-pink), 2px 0 var(--neon-cyan); transform: translate(-1px, 1px); }
    4%  { text-shadow: 0 0 20px var(--neon-green), 0 0 60px #00ff4155; transform: translate(0); }
    96% { text-shadow: 0 0 20px var(--neon-green), 0 0 60px #00ff4155; transform: translate(0); }
    98% { text-shadow: 2px 0 var(--neon-pink), -2px 0 var(--neon-cyan); transform: translate(1px, -1px); }
    100%{ text-shadow: 0 0 20px var(--neon-green), 0 0 60px #00ff4155; transform: translate(0); }
}
.glitch { animation: glitch 4s infinite; }

/* sidebar branding */
.sidebar-brand {
    font-family: 'Orbitron', monospace;
    font-size: 1.1rem;
    font-weight: 900;
    color: var(--neon-green) !important;
    letter-spacing: 0.15em;
    text-shadow: 0 0 10px var(--neon-green);
}
.sidebar-sub {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-dim) !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for k in ["scope", "risks", "wbs_data", "cpm_results",
          "project_name", "manual_tasks_list"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
<div style="padding:1rem 0 0.5rem">
  <div class="sidebar-brand">⬡ SMART PROJECT</div>
  <div class="sidebar-sub">AI AGENT v1.0 // ONLINE</div>
</div>
<hr style="border-color:#00ff4122; margin:0.5rem 0 1rem"/>
""", unsafe_allow_html=True)

    st.markdown('<div class="section-head">// PROJECT INPUT</div>', unsafe_allow_html=True)

    project_name = st.text_input(
        "PROJECT NAME",
        placeholder="e.g. Hospital Management System",
    )
    project_description = st.text_area(
        "PROJECT DESCRIPTION",
        placeholder=(
            "Describe your project...\n\n"
            "• What are you building?\n"
            "• Who is it for?\n"
            "• Key goals & budget?\n"
            "• Rough timeline?"
        ),
        height=200,
    )

    st.markdown('<div class="section-head">// EXECUTE</div>', unsafe_allow_html=True)

    can_go = bool(project_name and project_description)
    gen_scope_btn = st.button("▶  GENERATE SCOPE", use_container_width=True, type="primary")
    gen_risks_btn = st.button("▶  GENERATE RISK REGISTER", use_container_width=True)

    st.markdown('<div class="section-head">// SYSTEM STATUS</div>', unsafe_allow_html=True)

    steps = [
        ("SCOPE DEFINED",    st.session_state.scope is not None),
        ("RISKS MAPPED",     st.session_state.risks is not None),
        ("CPM COMPUTED",     st.session_state.cpm_results is not None),
    ]
    for label, done in steps:
        if done:
            st.markdown(f'<div class="prompt-line"><span class="status-ok">✓ {label}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="prompt-line"><span class="status-pend">○ {label}</span></div>', unsafe_allow_html=True)

    if not can_go:
        st.markdown('<br><div style="font-family:Share Tech Mono;font-size:0.72rem;color:#1a3a1a;letter-spacing:0.05em">[ AWAITING PROJECT INPUT ]<span class="cursor"></span></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="cyber-header">
  <div class="corner-tl"></div>
  <div class="corner-tr"></div>
  <div class="corner-bl"></div>
  <div class="corner-br"></div>

  <div class="cyber-logo glitch">SMART <span>PROJECT</span></div>
  <div class="cyber-tagline">// The AI Agent That Does the Heavy Lifting For You</div>
  <div class="cyber-desc">
    Stop drowning in documentation. SMART PROJECT deploys intelligent agents
    to define your scope, map your risks, and plot your critical path —
    in seconds, not days. Built for PMs who move fast.
  </div>
  <br>
  <span class="tag-pill">SCOPE AI</span>
  <span class="tag-pill">RISK ENGINE</span>
  <span class="tag-pill">CPM / PERT</span>
  <span class="tag-pill">WBS BUILDER</span>
  <span class="tag-pill">ZERO SETUP</span>
</div>
""", unsafe_allow_html=True)

# ── Action handlers ────────────────────────────────────────────────────────────
if gen_scope_btn:
    if not can_go:
        st.warning("⚡ Enter a project name and description first.")
    else:
        with st.spinner("[ AGENT PROCESSING — GENERATING SCOPE STATEMENT... ]"):
            try:
                scope = generate_scope(API_KEY, project_name, project_description)
                st.session_state.scope        = scope
                st.session_state.project_name = project_name
                st.session_state.risks        = None
                st.session_state.wbs_data     = None
                st.session_state.cpm_results  = None
                st.success("✓ SCOPE STATEMENT GENERATED — SEE TAB 01")
            except Exception as exc:
                st.error(f"AGENT ERROR: {exc}")

if gen_risks_btn:
    if not st.session_state.scope:
        st.warning("⚡ Generate a Scope Statement first (click ▶ GENERATE SCOPE).")
    else:
        with st.spinner("[ AGENT PROCESSING — MAPPING RISKS... ]"):
            try:
                risks = generate_risks(API_KEY, st.session_state.scope)
                st.session_state.risks       = risks
                st.session_state.wbs_data    = None
                st.session_state.cpm_results = None
                st.success("✓ RISK REGISTER COMPILED — SEE TAB 02")
            except Exception as exc:
                st.error(f"AGENT ERROR: {exc}")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "01 // SCOPE STATEMENT",
    "02 // RISK REGISTER",
    "03 // WBS & CPM/PERT",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 01 — SCOPE STATEMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if st.session_state.scope:
        st.markdown('<div class="section-head">// SCOPE STATEMENT OUTPUT</div>', unsafe_allow_html=True)

        # Render scope in a styled box
        st.markdown(f"""
<div style="
    background:#000500;
    border:1px solid #00ff4122;
    border-left:3px solid var(--neon-green);
    padding:1.5rem 2rem;
    font-family:'Share Tech Mono',monospace;
    color:#aaffcc;
    font-size:0.85rem;
    line-height:1.9;
    white-space:pre-wrap;
">
{st.session_state.scope}
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            "⬇  EXPORT SCOPE STATEMENT (.TXT)",
            data=st.session_state.scope,
            file_name=f"{st.session_state.project_name}_scope_statement.txt",
            mime="text/plain",
        )

    else:
        st.markdown("""
<div style="padding:3rem;text-align:center;border:1px dashed #00ff4122;font-family:'Share Tech Mono',monospace;">
  <div style="font-family:'VT323',monospace;font-size:2rem;color:#1a4d2a;letter-spacing:0.2em">
    [ AWAITING INPUT ]
  </div>
  <div style="color:#0d2a0d;font-size:0.8rem;margin-top:0.5rem;letter-spacing:0.1em">
    Enter project details in the sidebar and click ▶ GENERATE SCOPE
  </div>
</div>
""", unsafe_allow_html=True)
        with st.expander("WHAT IS A SCOPE STATEMENT?"):
            st.markdown("""
A **Project Scope Statement** defines the boundaries of your project:

- **What** will be built (deliverables)
- **Why** it exists (business justification)
- **What's in** and **what's out** of scope
- Constraints, assumptions, and success criteria

It is the single most important document to prevent scope creep.
""")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 02 — RISK REGISTER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    if st.session_state.risks:
        risks = st.session_state.risks

        high = sum(1 for r in risks if r["risk_score"] == "High")
        med  = sum(1 for r in risks if r["risk_score"] == "Medium")
        low  = sum(1 for r in risks if r["risk_score"] == "Low")

        st.markdown('<div class="section-head">// RISK MATRIX OVERVIEW</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TOTAL RISKS", len(risks))
        c2.metric("CRITICAL",    high)
        c3.metric("MODERATE",    med)
        c4.metric("LOW",         low)

        st.markdown('<div class="section-head">// FULL RISK REGISTER</div>', unsafe_allow_html=True)

        def _colour(val):
            m = {
                "High":   "background-color:#3a0000;color:#ff6666;font-weight:700",
                "Medium": "background-color:#2a1a00;color:#ffcc44;font-weight:700",
                "Low":    "background-color:#001a00;color:#44ff88;font-weight:700",
            }
            return m.get(val, "")

        df = pd.DataFrame(risks).rename(columns={
            "risk_id": "ID", "risk_name": "Risk",
            "category": "Category", "description": "Description",
            "likelihood": "Likelihood", "impact": "Impact",
            "risk_score": "Score", "mitigation_strategy": "Mitigation",
        })
        st.dataframe(
            df.style.applymap(_colour, subset=["Likelihood", "Impact", "Score"]),
            use_container_width=True, height=420,
        )

        st.download_button(
            "⬇  EXPORT RISK REGISTER (.CSV)",
            data=df.to_csv(index=False),
            file_name=f"{st.session_state.project_name}_risk_register.csv",
            mime="text/csv",
        )

    elif st.session_state.scope:
        st.markdown("""
<div style="padding:3rem;text-align:center;border:1px dashed #00ff4122;font-family:'Share Tech Mono',monospace;color:#1a4d2a">
  Scope defined. Click ▶ GENERATE RISK REGISTER in the sidebar to proceed.
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="padding:3rem;text-align:center;border:1px dashed #00ff4122;font-family:'Share Tech Mono',monospace;color:#1a4d2a">
  [ GENERATE SCOPE FIRST ]
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 03 — WBS & CPM/PERT
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    if not st.session_state.risks:
        st.markdown("""
<div style="padding:3rem;text-align:center;border:1px dashed #00ff4122;font-family:'Share Tech Mono',monospace;color:#1a4d2a">
  [ COMPLETE SCOPE + RISK STEPS FIRST ]
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="warn-cyber">
⚠ <strong>AGENT DISCLAIMER</strong><br>
AI-generated WBS and timelines are <em>rough planning estimates only</em>.
Real delivery depends on team experience, resource availability, vendor timelines,
regulatory approvals, and dozens of factors no AI can predict with certainty.<br>
<strong>Validate with your team before presenting to stakeholders.</strong>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="section-head">// SELECT BUILD MODE</div>', unsafe_allow_html=True)
        mode = st.radio(
            "",
            ["🤖  AI — Auto-generate WBS & Timeline", "✏️  MANUAL — Enter my own tasks"],
            horizontal=True,
        )

        # ── AI MODE ───────────────────────────────────────────────────────────
        if mode.startswith("🤖"):
            if st.button("▶  DEPLOY WBS + CPM AGENT", type="primary"):
                with st.spinner("[ AGENT PROCESSING — BUILDING WORK BREAKDOWN STRUCTURE... ]"):
                    try:
                        wbs_data = generate_wbs(
                            API_KEY,
                            st.session_state.scope,
                            st.session_state.project_name,
                        )
                        st.session_state.wbs_data = wbs_data
                        G, results_df, duration, cp = calculate_cpm(wbs_data["tasks"])
                        st.session_state.cpm_results = {
                            "G": G, "df": results_df,
                            "duration": duration, "critical_path": cp,
                            "tasks": wbs_data["tasks"],
                        }
                        st.success("✓ WBS AND CPM/PERT ANALYSIS COMPLETE")
                    except Exception as exc:
                        st.error(f"AGENT ERROR: {exc}")

        # ── MANUAL MODE ───────────────────────────────────────────────────────
        else:
            st.markdown('<div class="section-head">// TASK INPUT</div>', unsafe_allow_html=True)
            st.caption("IDs: T1, T2, T3...  |  Durations in DAYS  |  Dependencies: comma-separated (e.g. T1, T2)")

            if st.session_state.manual_tasks_list is None:
                st.session_state.manual_tasks_list = [
                    {"task_id": f"T{i+1}", "task_name": "",
                     "optimistic": 1, "most_likely": 3, "pessimistic": 6,
                     "dependencies": ""}
                    for i in range(4)
                ]

            if st.button("➕  ADD TASK"):
                n = len(st.session_state.manual_tasks_list) + 1
                st.session_state.manual_tasks_list.append({
                    "task_id": f"T{n}", "task_name": "",
                    "optimistic": 1, "most_likely": 3, "pessimistic": 6,
                    "dependencies": "",
                })

            updated = []
            for i, task in enumerate(st.session_state.manual_tasks_list):
                label = task["task_name"] or f"TASK_{i+1}"
                with st.expander(f"{task['task_id']} // {label}", expanded=(i < 2)):
                    c1, c2 = st.columns([1, 3])
                    tid   = c1.text_input("ID",          value=task["task_id"],   key=f"tid_{i}")
                    tname = c2.text_input("TASK NAME",   value=task["task_name"], key=f"tname_{i}")
                    c3, c4, c5, c6 = st.columns(4)
                    opt  = c3.number_input("OPTIMISTIC",  min_value=1, value=int(task["optimistic"]),  key=f"opt_{i}")
                    ml   = c4.number_input("MOST LIKELY", min_value=1, value=int(task["most_likely"]), key=f"ml_{i}")
                    pess = c5.number_input("PESSIMISTIC", min_value=1, value=int(task["pessimistic"]), key=f"pess_{i}")
                    deps = c6.text_input("DEPENDENCIES",  value=task["dependencies"],                  key=f"deps_{i}")
                    updated.append({
                        "task_id": tid.strip(), "task_name": tname.strip(),
                        "optimistic": opt, "most_likely": ml, "pessimistic": pess,
                        "dependencies": deps,
                    })

            st.session_state.manual_tasks_list = updated

            if st.button("▶  CALCULATE CPM / PERT", type="primary"):
                parsed = [
                    {**t, "dependencies": [d.strip() for d in t["dependencies"].split(",") if d.strip()]}
                    for t in updated if t["task_name"] and t["task_id"]
                ]
                if len(parsed) < 2:
                    st.warning("Enter at least 2 named tasks.")
                else:
                    try:
                        G, results_df, duration, cp = calculate_cpm(parsed)
                        st.session_state.cpm_results = {
                            "G": G, "df": results_df,
                            "duration": duration, "critical_path": cp,
                            "tasks": parsed,
                        }
                        st.session_state.wbs_data = None
                        st.success("✓ CPM/PERT ANALYSIS COMPLETE")
                    except Exception as exc:
                        st.error(f"ERROR: {exc}")

        # ── WBS DISPLAY ───────────────────────────────────────────────────────
        if st.session_state.wbs_data:
            st.markdown('<div class="section-head">// WORK BREAKDOWN STRUCTURE</div>', unsafe_allow_html=True)
            icons = {1: "▣", 2: "▷", 3: "·"}
            colours = {1: "#00e5ff", 2: "#00ff41", 3: "#4a9960"}
            rows_html = ""
            for item in st.session_state.wbs_data["wbs"]:
                indent  = "&nbsp;" * 8 * (item["level"] - 1)
                icon    = icons.get(item["level"], "·")
                colour  = colours.get(item["level"], "#4a9960")
                weight  = "700" if item["level"] == 1 else "400"
                rows_html += (
                    f'<div style="font-family:Share Tech Mono,monospace;'
                    f'color:{colour};font-weight:{weight};'
                    f'padding:0.18rem 0;font-size:0.82rem;letter-spacing:0.04em">'
                    f'{indent}{icon} {item["id"]} — {item["name"]}</div>\n'
                )
            st.markdown(
                f'<div style="background:#000500;border:1px solid #00ff4122;'
                f'padding:1rem 1.5rem;">{rows_html}</div>',
                unsafe_allow_html=True,
            )

        # ── CPM RESULTS ───────────────────────────────────────────────────────
        if st.session_state.cpm_results:
            cpm = st.session_state.cpm_results

            st.markdown('<div class="section-head">// CPM / PERT ANALYSIS</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("TOTAL DURATION", f"{cpm['duration']:.1f} days")
            c2.metric("CRITICAL TASKS", len(cpm["critical_path"]))
            c3.metric("TOTAL TASKS",    len(cpm["tasks"]))

            cp_str = " → ".join(cpm["critical_path"])
            st.markdown(
                f'<div style="font-family:Share Tech Mono,monospace;'
                f'color:#00e5ff;font-size:0.8rem;padding:0.5rem 0;'
                f'letter-spacing:0.05em">CRITICAL PATH: '
                f'<span style="color:#00ff41">{cp_str}</span></div>',
                unsafe_allow_html=True,
            )

            st.markdown('<div class="section-head">// TASK ANALYSIS TABLE</div>', unsafe_allow_html=True)

            def _hl(row):
                if row["Critical"] == "✅ Yes":
                    return ["background-color:#200000;color:#ff8888"] * len(row)
                return ["background-color:#000800;color:#aaffcc"] * len(row)

            st.dataframe(
                cpm["df"].style.apply(_hl, axis=1),
                use_container_width=True, height=380,
            )

            st.markdown('<div class="section-head">// GANTT CHART</div>', unsafe_allow_html=True)
            fig = plot_gantt(cpm["G"], cpm["tasks"])
            st.pyplot(fig)
            plt.close(fig)

            # ── DOWNLOADS ─────────────────────────────────────────────────────
            st.markdown('<div class="section-head">// EXPORT</div>', unsafe_allow_html=True)

            # Build full report text
            report_lines = [
                "=" * 60,
                f"  SMART PROJECT — FULL PROJECT REPORT",
                f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"  Project: {st.session_state.project_name}",
                "=" * 60,
                "",
                "SCOPE STATEMENT",
                "-" * 60,
                st.session_state.scope or "",
                "",
                "RISK REGISTER",
                "-" * 60,
            ]
            if st.session_state.risks:
                for r in st.session_state.risks:
                    report_lines.append(
                        f"[{r['risk_id']}] {r['risk_name']} | "
                        f"Score: {r['risk_score']} | "
                        f"Likelihood: {r['likelihood']} | Impact: {r['impact']}"
                    )
                    report_lines.append(f"     → Mitigation: {r['mitigation_strategy']}")
                    report_lines.append("")
            report_lines += [
                "CPM / PERT SUMMARY",
                "-" * 60,
                f"Estimated Project Duration : {cpm['duration']:.1f} days",
                f"Critical Path              : {cp_str}",
                "",
                "TASK ANALYSIS",
                "-" * 60,
            ]
            for _, row in cpm["df"].iterrows():
                report_lines.append(
                    f"{row['Task ID']} | {row['Task Name']:<30} | "
                    f"PERT: {row['PERT Duration (d)']} d | "
                    f"ES: {row['ES']} | EF: {row['EF']} | "
                    f"Float: {row['Float']} | {row['Critical']}"
                )
            report_lines += ["", "=" * 60,
                             "  DISCLAIMER: AI-generated estimates. Validate before use.",
                             "=" * 60]
            full_report = "\n".join(report_lines)

            dl1, dl2, dl3 = st.columns(3)
            dl1.download_button(
                "⬇  FULL REPORT (.TXT)",
                data=full_report,
                file_name=f"{st.session_state.project_name}_full_report.txt",
                mime="text/plain",
            )
            dl2.download_button(
                "⬇  CPM TABLE (.CSV)",
                data=cpm["df"].to_csv(index=False),
                file_name=f"{st.session_state.project_name}_cpm.csv",
                mime="text/csv",
            )
            buf = io.BytesIO()
            fig2 = plot_gantt(cpm["G"], cpm["tasks"])
            fig2.savefig(buf, format="png", dpi=150,
                         bbox_inches="tight", facecolor="#0e1117")
            plt.close(fig2)
            buf.seek(0)
            dl3.download_button(
                "⬇  GANTT CHART (.PNG)",
                data=buf,
                file_name=f"{st.session_state.project_name}_gantt.png",
                mime="image/png",
            )
