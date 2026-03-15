import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io, datetime

from agents import generate_scope, generate_risks, generate_wbs
from cpm_utils import calculate_cpm, plot_gantt

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
for k, v in {
    "screen": "landing", "wizard_step": 1,
    "project_name": "", "project_description": "", "constraints": "",
    "scope": None, "risks": None, "wbs_data": None,
    "cpm_results": None, "manual_tasks_list": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def go(screen, **kw):
    st.session_state.screen = screen
    for k, v in kw.items():
        st.session_state[k] = v
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS — all styles live here, nothing in render functions
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=Bebas+Neue&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    background: #080808 !important;
    color: #e2e2e2 !important;
    font-family: 'Syne', sans-serif !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stSidebar"]  { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ── Scroll to top helper ── */
.scroll-anchor { position: absolute; top: 0; }

/* ═══════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════ */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: #111 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
    color: #fff !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.9rem !important;
    padding: 0.75rem 1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #00ff87 !important;
    box-shadow: 0 0 0 3px #00ff8720 !important;
    outline: none !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #2e2e2e !important; }
.stTextInput label, .stTextArea label, .stNumberInput label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color: #555 !important;
    margin-bottom: 0.3rem !important;
    display: block !important;
}

/* ═══════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════ */
.stButton > button {
    background: transparent !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
    color: #bbb !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.74rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    padding: 0.65rem 1.4rem !important;
    transition: all 0.18s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    border-color: #00ff87 !important;
    color: #00ff87 !important;
    background: #00ff870a !important;
}
.stButton > button[kind="primary"] {
    background: #00ff87 !important;
    border-color: #00ff87 !important;
    color: #000 !important;
    font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #00e676 !important;
    box-shadow: 0 0 28px #00ff8750 !important;
}
.stButton > button:disabled { opacity: 0.2 !important; }

/* ═══════════════════════════════════════════
   DOWNLOAD BUTTONS
═══════════════════════════════════════════ */
.stDownloadButton > button {
    background: transparent !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
    color: #888 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    transition: all 0.18s !important;
}
.stDownloadButton > button:hover {
    border-color: #00ff87 !important;
    color: #00ff87 !important;
}

/* ═══════════════════════════════════════════
   TABS  — fix active color & font weight
═══════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #1e1e1e !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: #3a3a3a !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    padding: 0.9rem 2rem !important;
    transition: all 0.2s !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #888 !important; }
.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 2px solid #00ff87 !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent !important;
    padding-top: 0 !important;
}

/* ═══════════════════════════════════════════
   METRICS
═══════════════════════════════════════════ */
[data-testid="stMetric"] {
    background: #0e0e0e !important;
    border: 1px solid #1e1e1e !important;
    border-top: 2px solid #00ff87 !important;
    border-radius: 10px !important;
    padding: 1.1rem 1.4rem !important;
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
    font-size: 1.9rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
}

/* ═══════════════════════════════════════════
   DATAFRAME
═══════════════════════════════════════════ */
[data-testid="stDataFrame"] { border-radius: 10px !important; overflow: hidden !important; }

/* ═══════════════════════════════════════════
   EXPANDER
═══════════════════════════════════════════ */
.streamlit-expanderHeader {
    background: #0e0e0e !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 8px !important;
    color: #aaa !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
}

/* ═══════════════════════════════════════════
   RADIO
═══════════════════════════════════════════ */
.stRadio > div { gap: 1.5rem !important; }
.stRadio [data-baseweb="radio"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.84rem !important;
    color: #bbb !important;
    font-weight: 500 !important;
}

/* ═══════════════════════════════════════════
   ALERTS / SPINNER / MISC
═══════════════════════════════════════════ */
.stAlert {
    background: #0e0e0e !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
}
.stSpinner > div { border-top-color: #00ff87 !important; }
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1e1e1e; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #00ff87; }
hr { border-color: #1a1a1a !important; margin: 1.5rem 0 !important; }

/* ═══════════════════════════════════════════
   SCOPE MARKDOWN RENDERING
   Targets st.markdown() output in scope area
═══════════════════════════════════════════ */
.scope-area .stMarkdown h1,
.scope-area .stMarkdown h2 {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.1rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    border-bottom: 1px solid #1e1e1e !important;
    padding-bottom: 0.5rem !important;
    margin: 1.5rem 0 0.8rem !important;
    letter-spacing: -0.01em !important;
}
.scope-area .stMarkdown h3 {
    font-family: 'Syne', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #00ff87 !important;
    margin: 1.2rem 0 0.5rem !important;
    letter-spacing: 0.01em !important;
}
.scope-area .stMarkdown p {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.85rem !important;
    color: #aaa !important;
    line-height: 1.8 !important;
    margin-bottom: 0.8rem !important;
}
.scope-area .stMarkdown li {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.84rem !important;
    color: #999 !important;
    line-height: 1.75 !important;
    margin-bottom: 0.25rem !important;
}
.scope-area .stMarkdown strong {
    color: #ddd !important;
    font-weight: 600 !important;
}
.scope-area .stMarkdown ul, .scope-area .stMarkdown ol {
    padding-left: 1.5rem !important;
    margin-bottom: 0.8rem !important;
}
/* Remove the "## Project Scope Statement" header text */
.scope-area .stMarkdown h2:first-child { margin-top: 0 !important; }

/* ═══════════════════════════════════════════
   LANDING PAGE ELEMENTS
═══════════════════════════════════════════ */
.landing-root {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 3rem 1rem 2rem;
    position: relative;
    overflow: hidden;
}
.grid-bg {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
        linear-gradient(#00ff8707 1px, transparent 1px),
        linear-gradient(90deg, #00ff8707 1px, transparent 1px);
    background-size: 55px 55px;
    mask-image: radial-gradient(ellipse 70% 60% at 50% 50%, black 30%, transparent 100%);
}
.orb {
    position: fixed; z-index: 0; pointer-events: none;
    width: 700px; height: 700px; border-radius: 50%;
    background: radial-gradient(circle, #00ff8712 0%, transparent 65%);
    top: 50%; left: 50%; transform: translate(-50%, -50%);
    animation: orb-pulse 5s ease-in-out infinite;
}
@keyframes orb-pulse {
    0%, 100% { opacity: 0.5; transform: translate(-50%, -50%) scale(1); }
    50%       { opacity: 1;   transform: translate(-50%, -50%) scale(1.08); }
}
.landing-inner { position: relative; z-index: 1; max-width: 760px; margin: 0 auto; }
.badge {
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: #00ff8710; border: 1px solid #00ff8728;
    border-radius: 100px; padding: 0.3rem 1rem;
    font-family: 'DM Mono', monospace; font-size: 0.68rem;
    letter-spacing: 0.16em; color: #00ff87; text-transform: uppercase;
    margin-bottom: 2rem;
}
.badge-dot {
    width: 6px; height: 6px; background: #00ff87;
    border-radius: 50%; animation: blink 1.2s step-end infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }

.hero-logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(5rem, 13vw, 9.5rem);
    line-height: 0.92; color: #fff; letter-spacing: 0.03em;
    margin-bottom: 0.15em;
    animation: rise 0.9s cubic-bezier(.16,1,.3,1) both;
}
.hero-logo .g { color: #00ff87; }
@keyframes rise { from{opacity:0;transform:translateY(40px)} to{opacity:1;transform:none} }

.hero-sub {
    font-family: 'Syne', sans-serif; font-size: 1.15rem; font-weight: 400;
    color: #444; margin-bottom: 2.8rem; line-height: 1.55;
    animation: rise 0.9s 0.12s cubic-bezier(.16,1,.3,1) both;
}
.hero-sub em { color: #888; font-style: normal; font-weight: 600; }

.term {
    background: #0b0b0b; border: 1px solid #1a1a1a; border-radius: 12px;
    padding: 1.2rem 1.8rem; text-align: left; margin-bottom: 2.5rem;
    position: relative; overflow: hidden;
    animation: rise 0.9s 0.22s cubic-bezier(.16,1,.3,1) both;
}
.term::before {
    content:''; position:absolute; top:0; left:10%; right:10%; height:1px;
    background: linear-gradient(90deg, transparent, #00ff87, transparent);
}
.term-line { display:flex; gap:0.6rem; padding:0.18rem 0; font-family:'DM Mono',monospace; font-size:0.78rem; }
.tp { color:#00ff87; }
.tc { color:#ddd; }
.to { color:#333; padding-left:0.8rem; }
.cur {
    display:inline-block; width:7px; height:1em;
    background:#00ff87; vertical-align:text-bottom;
    animation:blink 0.9s step-end infinite; margin-left:1px;
}

.pills {
    display:flex; justify-content:center; gap:0.6rem;
    flex-wrap:wrap; margin-bottom:2.8rem;
    animation: rise 0.9s 0.32s cubic-bezier(.16,1,.3,1) both;
}
.pill {
    background:#0e0e0e; border:1px solid #1e1e1e;
    border-radius:100px; padding:0.35rem 1rem;
    font-family:'DM Mono',monospace; font-size:0.67rem;
    color:#555; letter-spacing:0.08em;
}
.cta-hint {
    font-family:'DM Mono',monospace; font-size:0.65rem;
    color:#222; letter-spacing:0.12em; text-align:center;
    padding-bottom:2rem;
    animation: rise 0.9s 0.52s cubic-bezier(.16,1,.3,1) both;
}

/* ═══════════════════════════════════════════
   WIZARD
═══════════════════════════════════════════ */
.wiz-wrap {
    min-height: 100vh; padding: 2rem 1rem 3rem;
    display: flex; flex-direction: column;
    align-items: center; position: relative;
}
.wiz-wrap::before {
    content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
    background-image:
        linear-gradient(#00ff8705 1px, transparent 1px),
        linear-gradient(90deg, #00ff8705 1px, transparent 1px);
    background-size:55px 55px;
    mask-image:radial-gradient(ellipse 60% 50% at 50% 25%, black 30%, transparent 100%);
}
.wiz-top-bar {
    position:relative; z-index:1;
    width:100%; max-width:580px;
    display:flex; justify-content:space-between; align-items:center;
    margin-bottom:1.2rem;
    font-family:'DM Mono',monospace; font-size:0.62rem;
    letter-spacing:0.12em; text-transform:uppercase; color:#2a2a2a;
}
.step-bar {
    position:relative; z-index:1;
    width:100%; max-width:580px;
    display:flex; align-items:center;
    margin-bottom:2.2rem;
}
.sd {
    width:30px; height:30px; border-radius:50%;
    border:1.5px solid #1e1e1e;
    display:flex; align-items:center; justify-content:center;
    font-family:'DM Mono',monospace; font-size:0.7rem; color:#2a2a2a;
    flex-shrink:0; transition:all 0.3s;
}
.sd.active { border-color:#00ff87; background:#00ff8712; color:#00ff87; }
.sd.done   { border-color:#00ff87; background:#00ff87; color:#000; font-weight:700; }
.sl { flex:1; height:1px; background:#1a1a1a; }
.sl.done { background:#00ff8740; }

.wiz-card {
    position:relative; z-index:1;
    width:100%; max-width:580px;
    background:#0b0b0b; border:1px solid #1a1a1a;
    border-radius:16px; padding:2.5rem 2.5rem 2rem;
}
.wiz-card::before {
    content:''; position:absolute;
    top:0; left:12%; right:12%; height:1px;
    background:linear-gradient(90deg, transparent, #00ff87, transparent);
}
.wiz-step-lbl {
    font-family:'DM Mono',monospace; font-size:0.65rem;
    letter-spacing:0.18em; text-transform:uppercase;
    color:#00ff87; margin-bottom:0.5rem;
}
.wiz-step-title {
    font-family:'Syne',sans-serif; font-size:1.75rem;
    font-weight:800; color:#fff; line-height:1.15;
    margin-bottom:0.5rem; letter-spacing:-0.01em;
}
.wiz-step-title .hi { color:#00ff87; }
.wiz-step-hint {
    font-family:'DM Mono',monospace; font-size:0.78rem;
    color:#333; line-height:1.65; margin-bottom:1.8rem;
}
.wiz-optional {
    font-family:'DM Mono',monospace; font-size:0.68rem;
    color:#1e1e1e; margin-bottom:1.2rem; letter-spacing:0.08em;
}

/* ═══════════════════════════════════════════
   DASHBOARD
═══════════════════════════════════════════ */
.topbar {
    position:sticky; top:0; z-index:999;
    background:#080808ee; backdrop-filter:blur(12px);
    border-bottom:1px solid #141414;
    display:flex; align-items:center; justify-content:space-between;
    padding:0.85rem 2.5rem;
}
.topbar-brand {
    font-family:'Bebas Neue',sans-serif; font-size:1.35rem;
    color:#fff; letter-spacing:0.08em;
}
.topbar-brand span { color:#00ff87; }
.topbar-proj {
    font-family:'DM Mono',monospace; font-size:0.7rem;
    color:#333; letter-spacing:0.1em; text-transform:uppercase;
}
.topbar-proj strong { color:#00ff87; font-weight:500; }

.dash-body { max-width:1080px; margin:0 auto; padding:2.5rem 2rem; }

.sec-lbl {
    font-family:'DM Mono',monospace; font-size:0.62rem;
    letter-spacing:0.22em; text-transform:uppercase;
    color:#00ff87; margin-bottom:0.5rem; display:block;
}
.sec-title {
    font-family:'Syne',sans-serif; font-size:1.5rem;
    font-weight:800; color:#fff; letter-spacing:-0.01em;
    margin-bottom:1.5rem;
}

.warn-box {
    background:#0c0800; border:1px solid #2a1e00;
    border-left:3px solid #f59e0b; border-radius:10px;
    padding:1rem 1.4rem; margin-bottom:1.8rem;
    font-family:'DM Mono',monospace; font-size:0.78rem;
    color:#7a5a10; line-height:1.7;
}
.warn-box strong { color:#f59e0b; }

.cp-tag {
    display:inline-block;
    font-family:'DM Mono',monospace; font-size:0.78rem;
    color:#00ff87; background:#00ff8710; border:1px solid #00ff8720;
    border-radius:6px; padding:0.45rem 1rem;
    margin-bottom:1.5rem; letter-spacing:0.04em;
}

.empty-state {
    text-align:center; padding:4rem 2rem;
    border:1px dashed #1a1a1a; border-radius:12px; margin-top:1rem;
}
.empty-state-title {
    font-family:'Syne',sans-serif; font-size:1rem;
    font-weight:700; color:#1e1e1e; margin-bottom:0.5rem;
}
.empty-state-hint {
    font-family:'DM Mono',monospace; font-size:0.75rem; color:#1e1e1e;
}

/* Scope panel background */
.scope-bg {
    background:#0b0b0b; border:1px solid #1a1a1a;
    border-left:3px solid #00ff87;
    border-radius:10px; padding:2rem 2.5rem;
    margin-bottom:1.5rem;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════════════════
def render_landing():
    st.markdown('<div class="grid-bg"></div><div class="orb"></div>', unsafe_allow_html=True)
    st.markdown("""
<div class="landing-root">
  <div class="landing-inner">
    <div class="badge"><span class="badge-dot"></span>AI Agent Online</div>
    <div class="hero-logo">SMART<br><span class="g">PROJECT</span></div>
    <div class="hero-sub">
      The agent that turns your idea into a<br>
      <em>complete project plan</em> — in under 60 seconds.
    </div>
    <div class="term">
      <div class="term-line"><span class="tp">→</span><span class="tc">initializing smart_project.agent</span></div>
      <div class="term-line"><span class="to">✓  scope_planner      loaded</span></div>
      <div class="term-line"><span class="to">✓  risk_engine         loaded</span></div>
      <div class="term-line"><span class="to">✓  cpm_pert_analyzer   loaded</span></div>
      <div class="term-line"><span class="to">✓  wbs_builder         loaded</span></div>
      <div class="term-line"><span class="tp">→</span><span class="tc">status: ready<span class="cur"></span></span></div>
    </div>
    <div class="pills">
      <span class="pill">Scope Statement</span>
      <span class="pill">Risk Register</span>
      <span class="pill">Work Breakdown Structure</span>
      <span class="pill">CPM / PERT Timeline</span>
      <span class="pill">Gantt Chart</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # CTA button — centred with columns
    _, c, _ = st.columns([1, 2, 1])
    with c:
        if st.button("▶  START YOUR PROJECT", type="primary", use_container_width=True):
            go("wizard", wizard_step=1)

    st.markdown('<div class="cta-hint">No setup required · Powered by AI</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# WIZARD
# ══════════════════════════════════════════════════════════════════════════════
def render_wizard():
    step = st.session_state.wizard_step

    # inject scroll-to-top
    st.markdown("""
<script>
  try { window.parent.document.querySelector('[data-testid="stAppViewContainer"]').scrollTop = 0; } catch(e) {}
  window.scrollTo(0,0);
</script>
""", unsafe_allow_html=True)

    s = ["", "", ""]
    for i in range(3):
        if i + 1 < step: s[i] = "done"
        elif i + 1 == step: s[i] = "active"
    l = ["done" if step > i+1 else "" for i in range(2)]

    # ── Background grid (HTML only, no Streamlit widgets inside)
    st.markdown('<div class="grid-bg" style="mask-image:radial-gradient(ellipse 60% 50% at 50% 25%, black 30%, transparent 100%)"></div>', unsafe_allow_html=True)

    # ── Top bar + step dots (centred via columns)
    _, mid, _ = st.columns([1, 4, 1])
    with mid:
        st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            font-family:'DM Mono',monospace;font-size:0.62rem;
            letter-spacing:0.12em;text-transform:uppercase;color:#2a2a2a;
            margin:1.5rem 0 1rem">
  <span>Step {step} of 3</span>
  <span>Smart Project</span>
</div>
<div style="display:flex;align-items:center;margin-bottom:2rem">
  <div class="sd {s[0]}">{"✓" if step > 1 else "1"}</div>
  <div class="sl {l[0]}"></div>
  <div class="sd {s[1]}">{"✓" if step > 2 else "2"}</div>
  <div class="sl {l[1]}"></div>
  <div class="sd {s[2]}">3</div>
</div>
""", unsafe_allow_html=True)

        # ── Card
        st.markdown('<div class="wiz-card">', unsafe_allow_html=True)

        # ── STEP 1 ────────────────────────────────────────────────────────────
        if step == 1:
            st.markdown("""
<div class="wiz-step-lbl">Step 01 / Name</div>
<div class="wiz-step-title">What's your<br>project called?</div>
<div class="wiz-step-hint">Give it a clear, recognisable name. This will appear across all generated documents.</div>
""", unsafe_allow_html=True)
            name = st.text_input("PROJECT NAME", value=st.session_state.project_name,
                                 placeholder="e.g.  Hospital Management System", key="w_name")
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

        # ── STEP 2 ────────────────────────────────────────────────────────────
        elif step == 2:
            pname = st.session_state.project_name
            st.markdown(f"""
<div class="wiz-step-lbl">Step 02 / Description</div>
<div class="wiz-step-title">Tell the agent<br>about <span class="hi">{pname}</span></div>
<div class="wiz-step-hint">Describe what you are building, who it is for, and what success looks like. More detail → better output.</div>
""", unsafe_allow_html=True)
            desc = st.text_area("PROJECT DESCRIPTION", value=st.session_state.project_description,
                placeholder="Describe your project in detail...\n\n• What are you building?\n• Who is it for?\n• What are the main goals?\n• Any known approach or tech?",
                height=195, key="w_desc")
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
                        st.warning("Please add a project description.")

        # ── STEP 3 ────────────────────────────────────────────────────────────
        elif step == 3:
            st.markdown("""
<div class="wiz-step-lbl">Step 03 / Constraints</div>
<div class="wiz-step-title">Set your<br>boundaries</div>
<div class="wiz-step-hint">Define any known limits — budget, timeline, team size, technology. All fields are optional; fill in what applies to your project.</div>
<div class="wiz-optional">All fields below are optional — fill in what's relevant</div>
""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            budget   = c1.text_input("BUDGET",       placeholder="e.g.  $500,000", key="w_budget")
            timeline = c2.text_input("TIMELINE",     placeholder="e.g.  6 months",  key="w_timeline")
            c3, c4 = st.columns(2)
            team     = c3.text_input("TEAM SIZE",    placeholder="e.g.  10 people", key="w_team")
            tech     = c4.text_input("TECH / TOOLS", placeholder="e.g.  Python, AWS", key="w_tech")
            other    = st.text_area("OTHER CONSTRAINTS",
                placeholder="Regulatory requirements, geographical limits, compliance needs...",
                height=80, key="w_other")
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("← Back", use_container_width=True):
                    go("wizard", wizard_step=2)
            with c2:
                if st.button("▶  Launch Agent", type="primary", use_container_width=True):
                    parts = [x for x in [
                        f"Budget: {budget}" if budget else "",
                        f"Timeline: {timeline}" if timeline else "",
                        f"Team size: {team}" if team else "",
                        f"Technology: {tech}" if tech else "",
                        f"Other constraints: {other}" if other else "",
                    ] if x]
                    st.session_state.constraints = "\n".join(parts)
                    go("dashboard")

        st.markdown('</div>', unsafe_allow_html=True)  # wiz-card


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def render_dashboard():
    pname = st.session_state.project_name
    full_desc = (st.session_state.project_description
                 + ("\n\nConstraints:\n" + st.session_state.constraints
                    if st.session_state.constraints else ""))

    # ── Top navigation bar ─────────────────────────────────────────────────────
    st.markdown(f"""
<div class="topbar">
  <div class="topbar-brand">SMART <span>PROJECT</span></div>
  <div class="topbar-proj">Active: <strong>{pname.upper()}</strong></div>
</div>
""", unsafe_allow_html=True)

    # ── Body ───────────────────────────────────────────────────────────────────
    st.markdown('<div class="dash-body">', unsafe_allow_html=True)

    # ── Controls row ───────────────────────────────────────────────────────────
    st.markdown('<span class="sec-lbl">Agent Controls</span>', unsafe_allow_html=True)
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 2, 2, 2])

    with ctrl1:
        scope_btn = st.button("▶  Generate Scope",    type="primary", use_container_width=True)
    with ctrl2:
        risk_btn  = st.button("▶  Generate Risks",    use_container_width=True)
    with ctrl3:
        wbs_btn   = st.button("▶  Build WBS & CPM",   use_container_width=True)
    with ctrl4:
        if st.button("← New Project", use_container_width=True):
            for k in ["scope","risks","wbs_data","cpm_results",
                      "project_name","project_description","constraints","manual_tasks_list"]:
                st.session_state[k] = None if k != "project_name" else ""
            go("landing")

    # ── Agent processing ───────────────────────────────────────────────────────
    if scope_btn:
        with st.spinner("Agent processing — generating scope statement..."):
            try:
                scope = generate_scope(API_KEY, pname, full_desc)
                st.session_state.scope = scope
                st.session_state.risks = None
                st.session_state.wbs_data = None
                st.session_state.cpm_results = None
                st.success("✓  Scope Statement generated — see Scope Statement tab")
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
                    st.success("✓  Risk Register compiled — see Risk Register tab")
                except Exception as e:
                    st.error(f"Error: {e}")

    if wbs_btn:
        if not st.session_state.risks:
            st.warning("Generate Scope and Risks first before building the WBS.")
        else:
            with st.spinner("Agent building work breakdown structure and critical path..."):
                try:
                    wbs_data = generate_wbs(API_KEY, st.session_state.scope, pname)
                    st.session_state.wbs_data = wbs_data
                    G, rdf, dur, cp = calculate_cpm(wbs_data["tasks"])
                    st.session_state.cpm_results = {
                        "G": G, "df": rdf, "duration": dur,
                        "critical_path": cp, "tasks": wbs_data["tasks"],
                    }
                    st.success("✓  WBS and CPM/PERT complete — see WBS & CPM / PERT tab")
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
            st.markdown('<span class="sec-lbl">Output</span>', unsafe_allow_html=True)
            st.markdown('<div class="sec-title">Scope Statement</div>', unsafe_allow_html=True)

            # Render scope inside styled container — st.markdown renders markdown properly
            st.markdown('<div class="scope-bg scope-area">', unsafe_allow_html=True)
            with st.container():
                # Strip the raw "## Project Scope Statement" header if AI echoes it
                scope_text = st.session_state.scope
                if scope_text.strip().startswith("## Project Scope Statement"):
                    lines = scope_text.split("\n")
                    scope_text = "\n".join(lines[1:]).lstrip()
                st.markdown(scope_text)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                "↓  Download Scope Statement (.txt)",
                data=st.session_state.scope,
                file_name=f"{pname}_scope_statement.txt",
                mime="text/plain",
            )
        else:
            _empty("Scope Statement",
                   "Click ▶ Generate Scope in the controls above to produce a full scope statement.")

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

            st.markdown('<span class="sec-lbl">Overview</span>', unsafe_allow_html=True)
            st.markdown('<div class="sec-title">Risk Register</div>', unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Risks", len(risks))
            m2.metric("Critical",    high)
            m3.metric("Moderate",    med)
            m4.metric("Low",         low)

            st.markdown("<br>", unsafe_allow_html=True)

            def _rc(val):
                return {
                    "High":   "background-color:#200000;color:#ff7070;font-weight:700",
                    "Medium": "background-color:#18100000;color:#ffc107;font-weight:700",
                    "Low":    "background-color:#001a08;color:#00c853;font-weight:700",
                }.get(val, "color:#ccc")

            df = pd.DataFrame(risks).rename(columns={
                "risk_id":"ID", "risk_name":"Risk", "category":"Category",
                "description":"Description", "likelihood":"Likelihood",
                "impact":"Impact", "risk_score":"Score",
                "mitigation_strategy":"Mitigation Strategy",
            })
            st.dataframe(
                df.style.applymap(_rc, subset=["Likelihood","Impact","Score"]),
                use_container_width=True, height=430,
            )
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                "↓  Download Risk Register (.csv)",
                data=df.to_csv(index=False),
                file_name=f"{pname}_risk_register.csv",
                mime="text/csv",
            )
        elif st.session_state.scope:
            _empty("Risk Register",
                   "Scope is ready. Click ▶ Generate Risks in the controls above.")
        else:
            _empty("Risk Register", "Generate a Scope Statement first.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — WBS & CPM
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)

        if not st.session_state.risks:
            _empty("WBS & CPM / PERT",
                   "Complete the Scope and Risk steps first, then click ▶ Build WBS & CPM above.")
        else:
            st.markdown("""
<div class="warn-box">
  <strong>⚠  Disclaimer</strong><br>
  AI-generated timelines and WBS are rough planning estimates only. Real delivery depends
  on team experience, resource availability, vendor timelines, regulatory approvals, and
  many other real-world factors. <strong>Always validate with your team before presenting
  to stakeholders.</strong>
</div>
""", unsafe_allow_html=True)

            # Manual mode still available inside tab
            st.markdown('<span class="sec-lbl">Manual Override</span>', unsafe_allow_html=True)
            with st.expander("✏️  Enter tasks manually instead of using AI"):
                st.caption("Task IDs: T1, T2 …  |  Durations in DAYS  |  Dependencies: T1, T2")

                if st.session_state.manual_tasks_list is None:
                    st.session_state.manual_tasks_list = [
                        {"task_id":f"T{i+1}","task_name":"",
                         "optimistic":1,"most_likely":3,"pessimistic":6,"dependencies":""}
                        for i in range(4)
                    ]
                if st.button("+ Add Task"):
                    n = len(st.session_state.manual_tasks_list)+1
                    st.session_state.manual_tasks_list.append(
                        {"task_id":f"T{n}","task_name":"",
                         "optimistic":1,"most_likely":3,"pessimistic":6,"dependencies":""})

                updated = []
                for i, task in enumerate(st.session_state.manual_tasks_list):
                    lbl = task["task_name"] or f"Task {i+1}"
                    with st.expander(f"{task['task_id']} — {lbl}", expanded=(i<2)):
                        ca,cb = st.columns([1,3])
                        tid  = ca.text_input("ID",   value=task["task_id"],   key=f"tid_{i}")
                        tnm  = cb.text_input("Name", value=task["task_name"], key=f"tnm_{i}")
                        cc,cd,ce,cf = st.columns(4)
                        opt  = cc.number_input("Optimistic",  min_value=1, value=int(task["optimistic"]),  key=f"op_{i}")
                        ml   = cd.number_input("Most Likely", min_value=1, value=int(task["most_likely"]), key=f"ml_{i}")
                        pess = ce.number_input("Pessimistic", min_value=1, value=int(task["pessimistic"]), key=f"ps_{i}")
                        deps = cf.text_input("Deps", value=task["dependencies"], key=f"dp_{i}")
                        updated.append({"task_id":tid.strip(),"task_name":tnm.strip(),
                                        "optimistic":opt,"most_likely":ml,
                                        "pessimistic":pess,"dependencies":deps})
                st.session_state.manual_tasks_list = updated

                if st.button("▶  Calculate CPM / PERT from Manual Tasks", type="primary"):
                    parsed = [
                        {**t,"dependencies":[d.strip() for d in t["dependencies"].split(",") if d.strip()]}
                        for t in updated if t["task_name"] and t["task_id"]
                    ]
                    if len(parsed) < 2:
                        st.warning("Enter at least 2 tasks.")
                    else:
                        try:
                            G, rdf, dur, cp = calculate_cpm(parsed)
                            st.session_state.cpm_results = {
                                "G":G,"df":rdf,"duration":dur,
                                "critical_path":cp,"tasks":parsed,
                            }
                            st.session_state.wbs_data = None
                            st.success("✓  CPM/PERT complete")
                        except Exception as e:
                            st.error(f"Error: {e}")

            # ── WBS TREE ──────────────────────────────────────────────────────
            if st.session_state.wbs_data:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<span class="sec-lbl">Work Breakdown Structure</span>', unsafe_allow_html=True)
                st.markdown('<div class="sec-title">WBS Tree</div>', unsafe_allow_html=True)

                wbs_rows = ""
                for item in st.session_state.wbs_data["wbs"]:
                    ind = "&nbsp;" * 8 * (item["level"]-1)
                    icon = {"1":"▣","2":"▷"}.get(str(item["level"]),"·")
                    col  = {"1":"#fff","2":"#ccc","3":"#555"}.get(str(item["level"]),"#555")
                    fw   = {"1":"800","2":"600","3":"400"}.get(str(item["level"]),"400")
                    fs   = {"1":"0.92rem","2":"0.85rem","3":"0.8rem"}.get(str(item["level"]),"0.8rem")
                    dot  = '<span style="color:#00ff87;margin-right:0.35rem">◆</span>' if item["level"]==1 else ""
                    wbs_rows += (
                        f'<div style="font-family:DM Mono,monospace;color:{col};font-weight:{fw};'
                        f'font-size:{fs};padding:0.2rem 0;letter-spacing:0.02em">'
                        f'{ind}{dot}{icon} '
                        f'<span style="color:#333;margin-right:0.4rem">{item["id"]}</span>'
                        f'{item["name"]}</div>\n'
                    )
                st.markdown(
                    f'<div style="background:#0b0b0b;border:1px solid #1a1a1a;'
                    f'border-radius:10px;padding:1.5rem 2rem;">{wbs_rows}</div>',
                    unsafe_allow_html=True,
                )

            # ── CPM RESULTS ───────────────────────────────────────────────────
            if st.session_state.cpm_results:
                cpm = st.session_state.cpm_results
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<span class="sec-lbl">Analysis</span>', unsafe_allow_html=True)
                st.markdown('<div class="sec-title">CPM / PERT Results</div>', unsafe_allow_html=True)

                m1, m2, m3 = st.columns(3)
                m1.metric("Estimated Duration", f"{cpm['duration']:.1f} days")
                m2.metric("Critical Tasks",     len(cpm["critical_path"]))
                m3.metric("Total Tasks",        len(cpm["tasks"]))

                st.markdown("<br>", unsafe_allow_html=True)
                cp_str = " → ".join(cpm["critical_path"])
                st.markdown(
                    f'<div class="cp-tag">Critical Path: {cp_str}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown('<span class="sec-lbl" style="margin-top:1.5rem;display:block">Task Table</span>', unsafe_allow_html=True)

                def _hl(row):
                    if row["Critical"] == "✅ Yes":
                        return ["background-color:#1a0000;color:#ff8888"] * len(row)
                    return ["background-color:#0b0b0b;color:#888"] * len(row)

                st.dataframe(
                    cpm["df"].style.apply(_hl, axis=1),
                    use_container_width=True, height=380,
                )

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<span class="sec-lbl">Gantt Chart</span>', unsafe_allow_html=True)
                fig = plot_gantt(cpm["G"], cpm["tasks"])
                st.pyplot(fig)
                plt.close(fig)

                # ── Exports ───────────────────────────────────────────────────
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<span class="sec-lbl">Export</span>', unsafe_allow_html=True)

                report = "\n".join([
                    "="*64,
                    f"  SMART PROJECT — FULL REPORT",
                    f"  Project  : {pname}",
                    f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    "="*64, "",
                    "SCOPE STATEMENT", "-"*64,
                    st.session_state.scope or "", "",
                    "RISK REGISTER", "-"*64,
                ] + [
                    f"[{r['risk_id']}] {r['risk_name']}  |  {r['risk_score']}  |  "
                    f"Likelihood:{r['likelihood']}  Impact:{r['impact']}\n"
                    f"     Mitigation: {r['mitigation_strategy']}\n"
                    for r in (st.session_state.risks or [])
                ] + [
                    "CPM / PERT SUMMARY", "-"*64,
                    f"Duration      : {cpm['duration']:.1f} days",
                    f"Critical Path : {cp_str}", "",
                    "TASK TABLE", "-"*64,
                ] + [
                    f"{row['Task ID']} | {row['Task Name']:<30} | "
                    f"PERT:{row['PERT Duration (d)']}d | "
                    f"ES:{row['ES']} EF:{row['EF']} Float:{row['Float']} | {row['Critical']}"
                    for _, row in cpm["df"].iterrows()
                ] + [
                    "", "="*64,
                    "  Disclaimer: AI-generated. Validate before use.",
                    "="*64,
                ])

                d1, d2, d3, _ = st.columns([2,2,2,2])
                d1.download_button("↓  Full Report (.txt)", data=report,
                    file_name=f"{pname}_full_report.txt", mime="text/plain")
                d2.download_button("↓  CPM Table (.csv)", data=cpm["df"].to_csv(index=False),
                    file_name=f"{pname}_cpm.csv", mime="text/csv")
                buf = io.BytesIO()
                fig2 = plot_gantt(cpm["G"], cpm["tasks"])
                fig2.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0e1117")
                plt.close(fig2); buf.seek(0)
                d3.download_button("↓  Gantt Chart (.png)", data=buf,
                    file_name=f"{pname}_gantt.png", mime="image/png")
            else:
                if not st.session_state.wbs_data:
                    st.markdown("<br>", unsafe_allow_html=True)
                    _empty("WBS & CPM / PERT", "Click ▶ Build WBS & CPM in the controls at the top of the page.")

    st.markdown('</div>', unsafe_allow_html=True)  # dash-body


def _empty(title, hint):
    st.markdown(f"""
<div class="empty-state">
  <div class="empty-state-title">{title}</div>
  <div class="empty-state-hint">{hint}</div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
screen = st.session_state.screen
if   screen == "landing":   render_landing()
elif screen == "wizard":    render_wizard()
elif screen == "dashboard": render_dashboard()
