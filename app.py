import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io, datetime, base64

from agents import generate_scope, generate_risks, generate_wbs
from cpm_utils import calculate_cpm, plot_gantt
from image_gen import generate_cyberpunk_svg

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
    "scope": None, "risks": None, "wbs_data": None, "cpm_results": None,
    "manual_tasks_list": None, "portfolio": [],
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def go(screen, **kw):
    st.session_state.screen = screen
    for k, v in kw.items():
        st.session_state[k] = v
    st.rerun()

def save_to_portfolio():
    """Save current project to portfolio if it has at least a scope."""
    if not st.session_state.scope:
        return
    pname = st.session_state.project_name
    # Update existing or add new
    existing = next((i for i, p in enumerate(st.session_state.portfolio)
                     if p["name"] == pname), None)
    entry = {
        "name":        pname,
        "description": st.session_state.project_description[:200],
        "constraints": st.session_state.constraints,
        "scope":       st.session_state.scope,
        "risks":       st.session_state.risks,
        "cpm":         st.session_state.cpm_results,
        "wbs":         st.session_state.wbs_data,
        "saved_at":    datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "svg":         generate_cyberpunk_svg(pname),
    }
    if existing is not None:
        st.session_state.portfolio[existing] = entry
    else:
        st.session_state.portfolio.append(entry)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=Bebas+Neue&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    background: #080808 !important;
    color: #d0d0d0 !important;
    font-family: 'Syne', sans-serif !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header, [data-testid="stDecoration"] { visibility: hidden !important; }
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ═══════════════════════════════════════
   INPUTS
═══════════════════════════════════════ */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: #0e0e0e !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
    color: #ffffff !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.9rem !important;
    padding: 0.75rem 1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #00ff87 !important;
    box-shadow: 0 0 0 3px #00ff8722 !important;
    outline: none !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #2a2a2a !important; }

.stTextInput label, .stTextArea label, .stNumberInput label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color: #666 !important;
    margin-bottom: 0.3rem !important;
    display: block !important;
}

/* ═══════════════════════════════════════
   BUTTONS
═══════════════════════════════════════ */
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

/* ═══════════════════════════════════════
   DOWNLOAD BUTTONS
═══════════════════════════════════════ */
.stDownloadButton > button {
    background: transparent !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
    color: #999 !important;
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

/* ═══════════════════════════════════════
   TABS
═══════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #1e1e1e !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: #444 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    padding: 0.9rem 2rem !important;
    transition: all 0.2s !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #999 !important; }
.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 2px solid #00ff87 !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab-panel"] { background: transparent !important; padding-top: 0 !important; }

/* ═══════════════════════════════════════
   METRICS
═══════════════════════════════════════ */
[data-testid="stMetric"] {
    background: #0c0c0c !important;
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
    color: #555 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.9rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
}

/* ═══════════════════════════════════════
   DATAFRAME
═══════════════════════════════════════ */
[data-testid="stDataFrame"] { border-radius: 10px !important; overflow: hidden !important; }

/* ═══════════════════════════════════════
   EXPANDER
═══════════════════════════════════════ */
.streamlit-expanderHeader {
    background: #0c0c0c !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 8px !important;
    color: #aaa !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
}

/* ═══════════════════════════════════════
   RADIO
═══════════════════════════════════════ */
.stRadio > div { gap: 1.5rem !important; }
.stRadio [data-baseweb="radio"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.84rem !important;
    color: #bbb !important;
    font-weight: 500 !important;
}

/* ═══════════════════════════════════════
   ALERTS / MISC
═══════════════════════════════════════ */
.stAlert {
    background: #0c0c0c !important;
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

/* ═══════════════════════════════════════
   SCOPE MARKDOWN — proper hierarchy
═══════════════════════════════════════ */
.scope-render h1, .scope-render h2 {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.15rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    border-bottom: 1px solid #1e1e1e !important;
    padding-bottom: 0.4rem !important;
    margin: 1.8rem 0 0.8rem !important;
}
.scope-render h3 {
    font-family: 'Syne', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #00ff87 !important;
    margin: 1.3rem 0 0.5rem !important;
    letter-spacing: 0.01em !important;
}
.scope-render p {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.86rem !important;
    color: #cccccc !important;
    line-height: 1.85 !important;
    margin-bottom: 0.75rem !important;
}
.scope-render li {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.84rem !important;
    color: #bbbbbb !important;
    line-height: 1.8 !important;
    margin-bottom: 0.3rem !important;
}
.scope-render strong { color: #eeeeee !important; font-weight: 600 !important; }
.scope-render ul, .scope-render ol { padding-left: 1.5rem !important; margin-bottom: 0.8rem !important; }

/* ═══════════════════════════════════════
   LANDING
═══════════════════════════════════════ */
@keyframes blink   { 0%,100%{opacity:1} 50%{opacity:0} }
@keyframes rise    { from{opacity:0;transform:translateY(36px)} to{opacity:1;transform:none} }
@keyframes orb-pulse { 0%,100%{opacity:.5;transform:translate(-50%,-50%) scale(1)} 50%{opacity:1;transform:translate(-50%,-50%) scale(1.08)} }
@keyframes float   { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }

/* ═══════════════════════════════════════
   WIZARD STEP DOT CLASSES
═══════════════════════════════════════ */
.sd {
    width:30px; height:30px; border-radius:50%;
    border:1.5px solid #1e1e1e;
    display:inline-flex; align-items:center; justify-content:center;
    font-family:'DM Mono',monospace; font-size:0.7rem; color:#2a2a2a;
}
.sd.active { border-color:#00ff87; background:#00ff8712; color:#00ff87; }
.sd.done   { border-color:#00ff87; background:#00ff87;   color:#000; font-weight:700; }
.sl        { display:inline-block; height:1px; background:#1a1a1a; flex:1; }
.sl.done   { background:#00ff8740; }

/* ═══════════════════════════════════════
   DASHBOARD
═══════════════════════════════════════ */
.topbar {
    position:sticky; top:0; z-index:999;
    background:#080808ee; backdrop-filter:blur(12px);
    border-bottom:1px solid #141414;
    display:flex; align-items:center; justify-content:space-between;
    padding:0.85rem 3rem;
}
.topbar-brand { font-family:'Bebas Neue',sans-serif; font-size:1.35rem; color:#fff; letter-spacing:0.08em; }
.topbar-brand span { color:#00ff87; }
.topbar-proj  { font-family:'DM Mono',monospace; font-size:0.7rem; color:#444; letter-spacing:0.1em; text-transform:uppercase; }
.topbar-proj strong { color:#00ff87; font-weight:500; }

.dash-body { max-width:1060px; margin:0 auto; padding:2.5rem 2.5rem; }

.sec-lbl {
    display:block; font-family:'DM Mono',monospace; font-size:0.62rem;
    letter-spacing:0.22em; text-transform:uppercase; color:#00ff87; margin-bottom:0.5rem;
}
.sec-title {
    font-family:'Syne',sans-serif; font-size:1.5rem;
    font-weight:800; color:#fff; letter-spacing:-0.01em; margin-bottom:1.5rem;
}

.warn-box {
    background:#0c0800; border:1px solid #2a1e00; border-left:3px solid #f59e0b;
    border-radius:10px; padding:1rem 1.4rem; margin-bottom:1.8rem;
    font-family:'DM Mono',monospace; font-size:0.82rem; color:#aa8030; line-height:1.7;
}
.warn-box strong { color:#f59e0b; }

.cp-tag {
    display:inline-block; font-family:'DM Mono',monospace; font-size:0.8rem;
    color:#00ff87; background:#00ff8710; border:1px solid #00ff8720;
    border-radius:6px; padding:0.45rem 1rem; margin-bottom:1.5rem; letter-spacing:0.04em;
}

.empty-state {
    text-align:center; padding:4rem 2rem;
    border:1px dashed #1a1a1a; border-radius:12px; margin-top:1rem;
}
.empty-title { font-family:'Syne',sans-serif; font-size:1rem; font-weight:700; color:#2a2a2a; margin-bottom:0.5rem; }
.empty-hint  { font-family:'DM Mono',monospace; font-size:0.78rem; color:#2a2a2a; }

/* ═══════════════════════════════════════
   PORTFOLIO CARD
═══════════════════════════════════════ */
.port-card {
    background:#0c0c0c; border:1px solid #1e1e1e;
    border-radius:12px; overflow:hidden;
    transition:border-color 0.2s, box-shadow 0.2s;
    cursor:pointer;
}
.port-card:hover {
    border-color:#00ff8755;
    box-shadow:0 0 20px #00ff8715;
}
.port-card-body { padding:1.2rem 1.4rem; }
.port-card-name {
    font-family:'Syne',sans-serif; font-size:1rem; font-weight:800;
    color:#fff; margin-bottom:0.3rem;
}
.port-card-desc {
    font-family:'DM Mono',monospace; font-size:0.72rem;
    color:#555; line-height:1.6; margin-bottom:0.8rem;
}
.port-card-meta {
    font-family:'DM Mono',monospace; font-size:0.65rem;
    color:#333; letter-spacing:0.08em;
}
.port-card-badges { display:flex; gap:0.4rem; flex-wrap:wrap; margin-top:0.6rem; }
.port-badge {
    font-family:'DM Mono',monospace; font-size:0.6rem; letter-spacing:0.1em;
    text-transform:uppercase; padding:0.15rem 0.5rem;
    border-radius:4px; color:#00ff87; border:1px solid #00ff8733;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════════════════
def render_landing():
    port_count = len(st.session_state.portfolio)

    st.markdown("""
<div style="position:fixed;inset:0;z-index:0;pointer-events:none;
    background-image:linear-gradient(#00ff8707 1px,transparent 1px),
    linear-gradient(90deg,#00ff8707 1px,transparent 1px);
    background-size:55px 55px;
    mask-image:radial-gradient(ellipse 70% 60% at 50% 50%, black 30%, transparent 100%)">
</div>
<div style="position:fixed;width:700px;height:700px;border-radius:50%;
    background:radial-gradient(circle,#00ff8712 0%,transparent 65%);
    top:50%;left:50%;transform:translate(-50%,-50%);
    animation:orb-pulse 5s ease-in-out infinite;z-index:0;pointer-events:none">
</div>""", unsafe_allow_html=True)

    st.markdown("""
<div style="min-height:100vh;display:flex;flex-direction:column;
    align-items:center;justify-content:center;
    text-align:center;padding:3rem 1rem 2rem;position:relative;z-index:1">
  <div style="max-width:760px;margin:0 auto">
    <div style="display:inline-flex;align-items:center;gap:0.5rem;
        background:#00ff8710;border:1px solid #00ff8728;border-radius:100px;
        padding:0.3rem 1rem;font-family:'DM Mono',monospace;font-size:0.68rem;
        letter-spacing:0.16em;color:#00ff87;text-transform:uppercase;margin-bottom:2rem">
      <span style="width:6px;height:6px;background:#00ff87;border-radius:50%;animation:blink 1.2s step-end infinite;display:inline-block"></span>
      AI Agent Online
    </div>
    <div style="font-family:'Bebas Neue',sans-serif;font-size:clamp(5rem,13vw,9.5rem);
        line-height:0.92;color:#fff;letter-spacing:0.03em;margin-bottom:0.15em;
        animation:rise 0.9s cubic-bezier(.16,1,.3,1) both">
      SMART<br><span style="color:#00ff87">PROJECT</span>
    </div>
    <div style="font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:400;
        color:#666;margin-bottom:2.8rem;line-height:1.55;
        animation:rise 0.9s 0.12s cubic-bezier(.16,1,.3,1) both">
      The agent that turns your idea into a<br>
      <span style="color:#999;font-weight:600">complete project plan</span> — in under 60 seconds.
    </div>
    <div style="background:#0b0b0b;border:1px solid #1a1a1a;border-radius:12px;
        padding:1.2rem 1.8rem;text-align:left;margin-bottom:2.5rem;position:relative;
        overflow:hidden;animation:rise 0.9s 0.22s cubic-bezier(.16,1,.3,1) both">
      <div style="position:absolute;top:0;left:10%;right:10%;height:1px;
          background:linear-gradient(90deg,transparent,#00ff87,transparent)"></div>
      <div style="font-family:'DM Mono',monospace;font-size:0.78rem;padding:0.18rem 0;display:flex;gap:0.6rem"><span style="color:#00ff87">→</span><span style="color:#ddd">initializing smart_project.agent</span></div>
      <div style="font-family:'DM Mono',monospace;font-size:0.78rem;padding:0.18rem 0;color:#333;padding-left:1.4rem">✓  scope_planner &nbsp;&nbsp;&nbsp;&nbsp; loaded</div>
      <div style="font-family:'DM Mono',monospace;font-size:0.78rem;padding:0.18rem 0;color:#333;padding-left:1.4rem">✓  risk_engine &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; loaded</div>
      <div style="font-family:'DM Mono',monospace;font-size:0.78rem;padding:0.18rem 0;color:#333;padding-left:1.4rem">✓  cpm_pert_analyzer &nbsp; loaded</div>
      <div style="font-family:'DM Mono',monospace;font-size:0.78rem;padding:0.18rem 0;color:#333;padding-left:1.4rem">✓  wbs_builder &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; loaded</div>
      <div style="font-family:'DM Mono',monospace;font-size:0.78rem;padding:0.18rem 0;display:flex;gap:0.6rem"><span style="color:#00ff87">→</span><span style="color:#ddd">status: ready<span style="display:inline-block;width:7px;height:1em;background:#00ff87;vertical-align:text-bottom;animation:blink 0.9s step-end infinite;margin-left:2px"></span></span></div>
    </div>
    <div style="display:flex;justify-content:center;gap:0.6rem;flex-wrap:wrap;margin-bottom:2.8rem;animation:rise 0.9s 0.32s cubic-bezier(.16,1,.3,1) both">
      <span style="background:#0e0e0e;border:1px solid #1e1e1e;border-radius:100px;padding:0.35rem 1rem;font-family:'DM Mono',monospace;font-size:0.67rem;color:#666;letter-spacing:0.08em">Scope Statement</span>
      <span style="background:#0e0e0e;border:1px solid #1e1e1e;border-radius:100px;padding:0.35rem 1rem;font-family:'DM Mono',monospace;font-size:0.67rem;color:#666;letter-spacing:0.08em">Risk Register</span>
      <span style="background:#0e0e0e;border:1px solid #1e1e1e;border-radius:100px;padding:0.35rem 1rem;font-family:'DM Mono',monospace;font-size:0.67rem;color:#666;letter-spacing:0.08em">Work Breakdown Structure</span>
      <span style="background:#0e0e0e;border:1px solid #1e1e1e;border-radius:100px;padding:0.35rem 1rem;font-family:'DM Mono',monospace;font-size:0.67rem;color:#666;letter-spacing:0.08em">CPM / PERT + Non-Critical Paths</span>
      <span style="background:#0e0e0e;border:1px solid #1e1e1e;border-radius:100px;padding:0.35rem 1rem;font-family:'DM Mono',monospace;font-size:0.67rem;color:#666;letter-spacing:0.08em">Gantt Chart</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    _, c1, gap, c2, _ = st.columns([1, 3, 0.3, 1.5, 1])
    with c1:
        if st.button("▶  START NEW PROJECT", type="primary", use_container_width=True):
            for k in ["scope","risks","wbs_data","cpm_results","project_name",
                      "project_description","constraints","manual_tasks_list"]:
                st.session_state[k] = None if k != "project_name" else ""
            go("wizard", wizard_step=1)
    with c2:
        label = f"◫  PORTFOLIO ({port_count})" if port_count else "◫  PORTFOLIO"
        if st.button(label, use_container_width=True):
            go("portfolio")

    st.markdown('<div style="font-family:DM Mono,monospace;font-size:0.65rem;color:#222;letter-spacing:0.12em;text-align:center;padding-bottom:2rem">No setup required · Powered by AI</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
def render_portfolio():
    st.markdown("""
<div style="position:sticky;top:0;z-index:999;background:#080808ee;
    backdrop-filter:blur(12px);border-bottom:1px solid #141414;
    display:flex;align-items:center;justify-content:space-between;
    padding:0.85rem 3rem">
  <div style="font-family:'Bebas Neue',sans-serif;font-size:1.35rem;color:#fff;letter-spacing:0.08em">
    SMART <span style="color:#00ff87">PROJECT</span>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#444;letter-spacing:0.12em;text-transform:uppercase">
    Project Portfolio
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div style="max-width:1060px;margin:0 auto;padding:2.5rem 2.5rem">', unsafe_allow_html=True)

    _, bc, _ = st.columns([3, 1, 3])
    with bc:
        if st.button("← Back to Home", use_container_width=True):
            go("landing")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="sec-lbl">All Projects</span>', unsafe_allow_html=True)
    st.markdown('<div class="sec-title">Project Portfolio</div>', unsafe_allow_html=True)

    portfolio = st.session_state.portfolio

    if not portfolio:
        st.markdown("""
<div class="empty-state" style="margin-top:2rem">
  <div class="empty-title">No saved projects yet</div>
  <div class="empty-hint">Create and generate a scope for a project — it will appear here automatically.</div>
</div>""", unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for i, proj in enumerate(portfolio):
            with cols[i % 3]:
                svg_b64 = base64.b64encode(proj["svg"].encode()).decode()
                has_risks = bool(proj.get("risks"))
                has_cpm   = bool(proj.get("cpm"))

                st.markdown(f"""
<div class="port-card">
  <img src="data:image/svg+xml;base64,{svg_b64}"
       style="width:100%;height:120px;object-fit:cover;display:block" alt="{proj['name']}"/>
  <div class="port-card-body">
    <div class="port-card-name">{proj['name']}</div>
    <div class="port-card-desc">{proj['description'][:120]}{"..." if len(proj['description']) > 120 else ""}</div>
    <div class="port-card-badges">
      <span class="port-badge">Scope ✓</span>
      {"<span class='port-badge'>Risks ✓</span>" if has_risks else ""}
      {"<span class='port-badge'>CPM ✓</span>" if has_cpm else ""}
    </div>
    <div class="port-card-meta" style="margin-top:0.8rem">Saved {proj['saved_at']}</div>
  </div>
</div>
""", unsafe_allow_html=True)
                if st.button(f"Open  →", key=f"open_{i}", use_container_width=True):
                    st.session_state.project_name        = proj["name"]
                    st.session_state.project_description = proj["description"]
                    st.session_state.constraints         = proj.get("constraints","")
                    st.session_state.scope               = proj["scope"]
                    st.session_state.risks               = proj.get("risks")
                    st.session_state.wbs_data            = proj.get("wbs")
                    st.session_state.cpm_results         = proj.get("cpm")
                    go("dashboard")

                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# WIZARD
# ══════════════════════════════════════════════════════════════════════════════
def render_wizard():
    step = st.session_state.wizard_step

    s = ["active" if i+1 == step else ("done" if i+1 < step else "") for i in range(3)]
    l = ["done" if step > i+1 else "" for i in range(2)]

    st.markdown("""<div style="position:fixed;inset:0;z-index:0;pointer-events:none;
    background-image:linear-gradient(#00ff8705 1px,transparent 1px),
    linear-gradient(90deg,#00ff8705 1px,transparent 1px);background-size:55px 55px;
    mask-image:radial-gradient(ellipse 60% 50% at 50% 25%, black 30%, transparent 100%)">
</div>""", unsafe_allow_html=True)

    # Centre everything
    _, mid, _ = st.columns([1, 4, 1])
    with mid:
        st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
    font-family:'DM Mono',monospace;font-size:0.62rem;letter-spacing:0.12em;
    text-transform:uppercase;color:#2a2a2a;margin:2rem 0 1rem">
  <span>Step {step} of 3</span><span>Smart Project</span>
</div>
<div style="display:flex;align-items:center;margin-bottom:2rem;gap:0">
  <div class="sd {s[0]}">{"✓" if step>1 else "1"}</div>
  <div style="flex:1;height:1px;background:{'#00ff8740' if step>1 else '#1a1a1a'}"></div>
  <div class="sd {s[1]}">{"✓" if step>2 else "2"}</div>
  <div style="flex:1;height:1px;background:{'#00ff8740' if step>2 else '#1a1a1a'}"></div>
  <div class="sd {s[2]}">3</div>
</div>
""", unsafe_allow_html=True)

        # Card
        st.markdown("""<div style="background:#0b0b0b;border:1px solid #1a1a1a;border-radius:16px;
    padding:2.5rem 2.5rem 2rem;position:relative;overflow:hidden">
  <div style="position:absolute;top:0;left:12%;right:12%;height:1px;
      background:linear-gradient(90deg,transparent,#00ff87,transparent)"></div>
""", unsafe_allow_html=True)

        if step == 1:
            st.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:0.65rem;letter-spacing:0.18em;
    text-transform:uppercase;color:#00ff87;margin-bottom:0.5rem">Step 01 / Name</div>
<div style="font-family:'Syne',sans-serif;font-size:1.75rem;font-weight:800;
    color:#fff;line-height:1.15;margin-bottom:0.5rem;letter-spacing:-0.01em">
    What's your<br>project called?</div>
<div style="font-family:'DM Mono',monospace;font-size:0.82rem;color:#666;
    line-height:1.65;margin-bottom:1.8rem">
    Give it a clear, recognisable name. This will appear across all generated documents.</div>
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

        elif step == 2:
            pname = st.session_state.project_name
            st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:0.65rem;letter-spacing:0.18em;
    text-transform:uppercase;color:#00ff87;margin-bottom:0.5rem">Step 02 / Description</div>
<div style="font-family:'Syne',sans-serif;font-size:1.75rem;font-weight:800;
    color:#fff;line-height:1.15;margin-bottom:0.5rem;letter-spacing:-0.01em">
    Tell the agent<br>about <span style="color:#00ff87">{pname}</span></div>
<div style="font-family:'DM Mono',monospace;font-size:0.82rem;color:#666;
    line-height:1.65;margin-bottom:1.8rem">
    Describe what you are building, who it is for, and what success looks like.
    More detail → better output.</div>
""", unsafe_allow_html=True)
            desc = st.text_area("PROJECT DESCRIPTION", value=st.session_state.project_description,
                placeholder="Describe your project...\n\n• What are you building?\n• Who is it for?\n• Main goals?\n• Any approach or technology?",
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

        elif step == 3:
            st.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:0.65rem;letter-spacing:0.18em;
    text-transform:uppercase;color:#00ff87;margin-bottom:0.5rem">Step 03 / Constraints</div>
<div style="font-family:'Syne',sans-serif;font-size:1.75rem;font-weight:800;
    color:#fff;line-height:1.15;margin-bottom:0.5rem;letter-spacing:-0.01em">
    Set your<br>boundaries</div>
<div style="font-family:'DM Mono',monospace;font-size:0.82rem;color:#666;
    line-height:1.65;margin-bottom:0.5rem">
    Define any known limits. All fields are optional — fill in what applies to your project.</div>
<div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#333;
    letter-spacing:0.08em;margin-bottom:1.5rem">All fields optional</div>
""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            budget   = c1.text_input("BUDGET",       placeholder="e.g.  $500,000",  key="w_budget")
            timeline = c2.text_input("TIMELINE",     placeholder="e.g.  6 months",  key="w_timeline")
            c3, c4 = st.columns(2)
            team     = c3.text_input("TEAM SIZE",    placeholder="e.g.  10 people", key="w_team")
            tech     = c4.text_input("TECH / TOOLS", placeholder="e.g.  Python, AWS", key="w_tech")
            other    = st.text_area("OTHER CONSTRAINTS",
                placeholder="Regulatory requirements, geographic limits, compliance...",
                height=75, key="w_other")
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
                        f"Other: {other}" if other else "",
                    ] if x]
                    st.session_state.constraints = "\n".join(parts)
                    go("dashboard")

        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def render_dashboard():
    pname    = st.session_state.project_name
    full_desc = (st.session_state.project_description
                 + ("\n\nConstraints:\n" + st.session_state.constraints
                    if st.session_state.constraints else ""))

    # Generate project image
    svg      = generate_cyberpunk_svg(pname)
    svg_b64  = base64.b64encode(svg.encode()).decode()

    # ── Top bar ────────────────────────────────────────────────────────────────
    st.markdown(f"""
<div class="topbar">
  <div class="topbar-brand">SMART <span>PROJECT</span></div>
  <div class="topbar-proj">Active: <strong>{pname.upper()}</strong></div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="dash-body">', unsafe_allow_html=True)

    # ── Hero image + controls ──────────────────────────────────────────────────
    img_col, ctrl_col = st.columns([2, 3])

    with img_col:
        st.markdown(f"""
<img src="data:image/svg+xml;base64,{svg_b64}"
     style="width:100%;border-radius:10px;display:block;border:1px solid #1e1e1e" alt="{pname}"/>
<div style="font-family:'DM Mono',monospace;font-size:0.62rem;color:#333;
    letter-spacing:0.1em;text-align:center;margin-top:0.5rem">
  AI-GENERATED · {pname.upper()[:20]}
</div>""", unsafe_allow_html=True)

    with ctrl_col:
        st.markdown('<span class="sec-lbl">Agent Controls</span>', unsafe_allow_html=True)
        st.markdown(f'<div class="sec-title" style="font-size:1.3rem;margin-bottom:1rem">{pname}</div>', unsafe_allow_html=True)

        if st.session_state.constraints:
            st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:0.75rem;color:#555;line-height:1.7;margin-bottom:1.2rem">{st.session_state.constraints.replace(chr(10)," · ")}</div>', unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            scope_btn = st.button("▶  Generate Scope",  type="primary", use_container_width=True)
        with b2:
            risk_btn  = st.button("▶  Generate Risks",  use_container_width=True)

        b3, b4 = st.columns(2)
        with b3:
            wbs_btn   = st.button("▶  Build WBS & CPM", use_container_width=True)
        with b4:
            if st.button("◫  Save to Portfolio",        use_container_width=True):
                save_to_portfolio()
                st.success("✓  Saved to portfolio")

        if st.button("← New Project", use_container_width=True):
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
                save_to_portfolio()
                st.success("✓  Scope Statement generated")
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
                    save_to_portfolio()
                    st.success("✓  Risk Register compiled")
                except Exception as e:
                    st.error(f"Error: {e}")

    if wbs_btn:
        if not st.session_state.risks:
            st.warning("Generate Scope and Risks first.")
        else:
            with st.spinner("Agent building detailed WBS and critical path analysis..."):
                try:
                    wbs_data = generate_wbs(API_KEY, st.session_state.scope, pname)
                    st.session_state.wbs_data = wbs_data
                    G, rdf, dur, cp = calculate_cpm(wbs_data["tasks"])
                    st.session_state.cpm_results = {
                        "G": G, "df": rdf, "duration": dur,
                        "critical_path": cp, "tasks": wbs_data["tasks"],
                    }
                    save_to_portfolio()
                    st.success("✓  WBS and CPM/PERT complete")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["Scope Statement", "Risk Register", "WBS & CPM / PERT"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — SCOPE
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.scope:
            st.markdown('<span class="sec-lbl">Output</span>', unsafe_allow_html=True)
            st.markdown('<div class="sec-title">Scope Statement</div>', unsafe_allow_html=True)

            # Render scope using st.markdown (proper markdown rendering)
            # Wrap in a div we can target with CSS — use st.container
            scope_text = st.session_state.scope
            # Strip echoed title if AI added it
            for strip in ["## Project Scope Statement\n", "# Project Scope Statement\n"]:
                if scope_text.strip().startswith(strip.strip()):
                    scope_text = scope_text[scope_text.index("\n")+1:].lstrip()

            with st.container():
                st.markdown(f'<div class="scope-render">', unsafe_allow_html=True)
                st.markdown(scope_text)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("↓  Download Scope Statement (.txt)",
                data=st.session_state.scope,
                file_name=f"{pname}_scope_statement.txt", mime="text/plain")
        else:
            _empty("Scope Statement", "Click ▶ Generate Scope in the controls above.")

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
                    "High":   "background-color:#1a0000;color:#ff6060;font-weight:700",
                    "Medium": "background-color:#141000;color:#ffc107;font-weight:700",
                    "Low":    "background-color:#001408;color:#00c853;font-weight:700",
                }.get(val, "color:#ccc")

            cols_show = ["risk_id","risk_name","category","description",
                         "likelihood","impact","risk_score","mitigation_strategy","contingency_plan"]
            cols_show = [c for c in cols_show if c in risks[0]]

            df = pd.DataFrame([{k: r.get(k,"") for k in cols_show} for r in risks])
            df.columns = [c.replace("_"," ").title() for c in df.columns]

            style_cols = [c for c in ["Likelihood","Impact","Risk Score"] if c in df.columns]
            st.dataframe(
                df.style.applymap(_rc, subset=style_cols),
                use_container_width=True, height=460,
            )
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("↓  Download Risk Register (.csv)",
                data=df.to_csv(index=False),
                file_name=f"{pname}_risk_register.csv", mime="text/csv")

        elif st.session_state.scope:
            _empty("Risk Register", "Click ▶ Generate Risks in the controls above.")
        else:
            _empty("Risk Register", "Generate a Scope Statement first.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — WBS & CPM
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)

        if not st.session_state.risks:
            _empty("WBS & CPM / PERT", "Complete Scope and Risk steps first, then click ▶ Build WBS & CPM.")
        else:
            st.markdown("""
<div class="warn-box">
  <strong>⚠  Disclaimer</strong> — AI-generated timelines are rough planning estimates only.
  Real delivery depends on team experience, resource availability, vendor timelines, and
  many real-world factors. <strong>Validate with your team before presenting to stakeholders.</strong>
</div>""", unsafe_allow_html=True)

            # Manual tasks inside expander
            with st.expander("✏️  Manual task entry (override AI)"):
                st.caption("Task IDs: T1, T2 …  |  Durations in DAYS  |  Dependencies: T1, T2")
                if st.session_state.manual_tasks_list is None:
                    st.session_state.manual_tasks_list = [
                        {"task_id":f"T{i+1}","task_name":"","optimistic":1,
                         "most_likely":3,"pessimistic":6,"dependencies":""}
                        for i in range(4)]
                if st.button("+ Add Task"):
                    n = len(st.session_state.manual_tasks_list)+1
                    st.session_state.manual_tasks_list.append(
                        {"task_id":f"T{n}","task_name":"","optimistic":1,
                         "most_likely":3,"pessimistic":6,"dependencies":""})
                updated = []
                for i, task in enumerate(st.session_state.manual_tasks_list):
                    lbl = task["task_name"] or f"Task {i+1}"
                    with st.expander(f"{task['task_id']} — {lbl}", expanded=(i<2)):
                        ca,cb = st.columns([1,3])
                        tid = ca.text_input("ID",   value=task["task_id"],   key=f"tid_{i}")
                        tnm = cb.text_input("Name", value=task["task_name"], key=f"tnm_{i}")
                        cc,cd,ce,cf = st.columns(4)
                        opt  = cc.number_input("Optimistic",  min_value=1, value=int(task["optimistic"]),  key=f"op_{i}")
                        ml   = cd.number_input("Most Likely", min_value=1, value=int(task["most_likely"]), key=f"ml_{i}")
                        pess = ce.number_input("Pessimistic", min_value=1, value=int(task["pessimistic"]), key=f"ps_{i}")
                        deps = cf.text_input("Deps", value=task["dependencies"], key=f"dp_{i}")
                        updated.append({"task_id":tid.strip(),"task_name":tnm.strip(),
                                        "optimistic":opt,"most_likely":ml,
                                        "pessimistic":pess,"dependencies":deps})
                st.session_state.manual_tasks_list = updated
                if st.button("▶  Calculate CPM from Manual Tasks", type="primary"):
                    parsed = [{**t,"dependencies":[d.strip() for d in t["dependencies"].split(",") if d.strip()]}
                              for t in updated if t["task_name"] and t["task_id"]]
                    if len(parsed) < 2:
                        st.warning("Enter at least 2 tasks.")
                    else:
                        try:
                            G,rdf,dur,cp = calculate_cpm(parsed)
                            st.session_state.cpm_results = {"G":G,"df":rdf,"duration":dur,"critical_path":cp,"tasks":parsed}
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
                phase_icons = {1:"◆",2:"▷",3:"·"}
                ph_colors   = {1:"#fff",2:"#ccc",3:"#777"}
                ph_weights  = {1:"800",2:"600",3:"400"}
                ph_sizes    = {1:"0.92rem",2:"0.86rem",3:"0.8rem"}

                for item in st.session_state.wbs_data["wbs"]:
                    lvl  = item["level"]
                    ind  = "&nbsp;" * 8 * (lvl-1)
                    icon = phase_icons.get(lvl,"·")
                    col  = ph_colors.get(lvl,"#777")
                    fw   = ph_weights.get(lvl,"400")
                    fs   = ph_sizes.get(lvl,"0.8rem")
                    grn  = f'<span style="color:#00ff87;margin-right:0.4rem">{icon}</span>' if lvl==1 else f'<span style="color:#333;margin-right:0.3rem">{icon}</span>'
                    wbs_rows += (
                        f'<div style="font-family:DM Mono,monospace;color:{col};'
                        f'font-weight:{fw};font-size:{fs};padding:0.22rem 0">'
                        f'{ind}{grn}<span style="color:#444;margin-right:0.5rem;font-size:0.75em">{item["id"]}</span>'
                        f'{item["name"]}</div>\n'
                    )
                st.markdown(
                    f'<div style="background:#0b0b0b;border:1px solid #1a1a1a;'
                    f'border-radius:10px;padding:1.5rem 2rem">{wbs_rows}</div>',
                    unsafe_allow_html=True,
                )

            # ── CPM RESULTS ───────────────────────────────────────────────────
            if st.session_state.cpm_results:
                cpm = st.session_state.cpm_results
                df  = cpm["df"]

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<span class="sec-lbl">Analysis</span>', unsafe_allow_html=True)
                st.markdown('<div class="sec-title">CPM / PERT Results</div>', unsafe_allow_html=True)

                # Summary metrics
                n_crit    = len(cpm["critical_path"])
                n_noncrit = len(cpm["tasks"]) - n_crit
                max_float = df["Float (d)"].max() if "Float (d)" in df.columns else 0

                m1,m2,m3,m4 = st.columns(4)
                m1.metric("Project Duration", f"{cpm['duration']:.1f} days")
                m2.metric("Critical Tasks",   n_crit)
                m3.metric("Non-Critical",     n_noncrit)
                m4.metric("Max Float",        f"{max_float:.1f}d")

                st.markdown("<br>", unsafe_allow_html=True)
                cp_str = " → ".join(cpm["critical_path"])
                st.markdown(f'<div class="cp-tag">🔴 Critical Path: {cp_str}</div>', unsafe_allow_html=True)

                # Float summary for non-critical
                nc_df = df[df["Critical"] == "🟢 Non-Critical"][["Task ID","Task Name","Phase","Resource","PERT Duration (d)","Float (d)"]].copy() if "Phase" in df.columns else df[df["Critical"] == "🟢 Non-Critical"][["Task ID","Task Name","PERT Duration (d)","Float (d)"]].copy()
                if not nc_df.empty:
                    st.markdown('<span class="sec-lbl" style="margin-top:1rem;display:block">Non-Critical Tasks with Float</span>', unsafe_allow_html=True)
                    st.dataframe(nc_df, use_container_width=True, height=min(200, len(nc_df)*38+50))

                # Full table
                st.markdown('<span class="sec-lbl" style="margin-top:1.5rem;display:block">Full Task Analysis Table</span>', unsafe_allow_html=True)

                def _hl(row):
                    if row["Critical"] == "🔴 Critical":
                        return ["background-color:#1a0000;color:#ff8888"]*len(row)
                    return ["background-color:#0b0b0b;color:#aaa"]*len(row)

                st.dataframe(df.style.apply(_hl, axis=1), use_container_width=True, height=420)

                # Gantt
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<span class="sec-lbl">Gantt Chart — Critical & Non-Critical Paths</span>', unsafe_allow_html=True)
                fig = plot_gantt(cpm["G"], cpm["tasks"])
                st.pyplot(fig)
                plt.close(fig)

                # Exports
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<span class="sec-lbl">Export</span>', unsafe_allow_html=True)

                report = "\n".join([
                    "="*68, f"  SMART PROJECT — FULL REPORT",
                    f"  Project  : {pname}",
                    f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    "="*68,"",
                    "SCOPE STATEMENT","-"*68,
                    st.session_state.scope or "","",
                    "RISK REGISTER","-"*68,
                ] + [
                    f"[{r.get('risk_id','')}] {r.get('risk_name','')}  |  {r.get('risk_score','')}  |  "
                    f"Likelihood:{r.get('likelihood','')}  Impact:{r.get('impact','')}\n"
                    f"     Mitigation: {r.get('mitigation_strategy','')}\n"
                    f"     Contingency: {r.get('contingency_plan','')}\n"
                    for r in (st.session_state.risks or [])
                ] + [
                    "CPM / PERT SUMMARY","-"*68,
                    f"Duration        : {cpm['duration']:.1f} days",
                    f"Critical Path   : {cp_str}",
                    f"Non-Critical    : {n_noncrit} tasks  |  Max Float: {max_float:.1f} days","",
                    "TASK TABLE","-"*68,
                ] + [
                    f"{row['Task ID']} | {row['Task Name']:<30} | "
                    f"PERT:{row['PERT Duration (d)']}d | "
                    f"ES:{row['ES']} EF:{row['EF']} Float:{row['Float (d)']} | {row['Critical']}"
                    for _, row in df.iterrows()
                ] + ["","="*68,"  AI-generated estimates. Validate before use.","="*68])

                d1,d2,d3,_ = st.columns([2,2,2,2])
                d1.download_button("↓  Full Report (.txt)", data=report,
                    file_name=f"{pname}_full_report.txt", mime="text/plain")
                d2.download_button("↓  CPM Table (.csv)", data=df.to_csv(index=False),
                    file_name=f"{pname}_cpm.csv", mime="text/csv")
                buf = io.BytesIO()
                fig2 = plot_gantt(cpm["G"], cpm["tasks"])
                fig2.savefig(buf,format="png",dpi=150,bbox_inches="tight",facecolor="#080808")
                plt.close(fig2); buf.seek(0)
                d3.download_button("↓  Gantt (.png)", data=buf,
                    file_name=f"{pname}_gantt.png", mime="image/png")
            else:
                if not st.session_state.wbs_data:
                    st.markdown("<br>", unsafe_allow_html=True)
                    _empty("WBS & CPM / PERT", "Click ▶ Build WBS & CPM in the controls at the top of the page.")

    st.markdown('</div>', unsafe_allow_html=True)


def _empty(title, hint):
    st.markdown(f'<div class="empty-state"><div class="empty-title">{title}</div><div class="empty-hint">{hint}</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
s = st.session_state.screen
if   s == "landing":   render_landing()
elif s == "wizard":    render_wizard()
elif s == "dashboard": render_dashboard()
elif s == "portfolio": render_portfolio()
