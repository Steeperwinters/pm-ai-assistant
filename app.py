import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

from agents import generate_scope, generate_risks, generate_wbs
from cpm_utils import calculate_cpm, plot_gantt

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI PM Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Header banner */
.pm-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 60%, #7c3aed 100%);
    padding: 1.6rem 2rem;
    border-radius: 14px;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 4px 24px rgba(37,99,235,0.25);
}
.pm-header h1 { color: white; margin: 0 0 0.3rem; font-size: 2rem; }
.pm-header p  { color: rgba(255,255,255,0.82); margin: 0; font-size: 0.95rem; }

/* Disclaimer / warning box */
.warn-box {
    background: linear-gradient(135deg, #78350f, #b45309);
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 1rem 0 1.4rem;
    color: #fef3c7;
    font-size: 0.9rem;
    line-height: 1.5;
}

/* Progress steps in sidebar */
.step-done  { color: #4ade80; }
.step-pend  { color: #64748b; }

/* Section dividers */
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #93c5fd;
    border-bottom: 1px solid #1e3a5f;
    padding-bottom: 0.3rem;
    margin: 1.2rem 0 0.8rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ──────────────────────────────────────────────────────────────
for key in ["scope", "risks", "wbs_data", "cpm_results", "project_name",
            "manual_tasks_list"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AI PM Assistant")
    st.markdown("---")

    st.markdown("### 🔑 Gemini API Key (Free)")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="AIza...",
        help="Get yours FREE at aistudio.google.com",
    )

    st.markdown("---")
    st.markdown("### 📋 Project Info")
    project_name = st.text_input("Project Name", placeholder="e.g. Hospital Management System")
    project_description = st.text_area(
        "Project Description",
        placeholder=(
            "Describe your project in detail.\n\n"
            "Include:\n"
            "• What you're building\n"
            "• Who it's for\n"
            "• Key goals\n"
            "• Rough timeline & budget"
        ),
        height=220,
    )

    st.markdown("---")
    st.markdown("### 🚀 Actions")

    can_scope = bool(api_key and project_name and project_description)
    gen_scope_btn = st.button(
        "📋  Step 1 — Generate Scope",
        use_container_width=True,
        type="primary",
        disabled=not can_scope,
    )
    gen_risks_btn = st.button(
        "⚠️  Step 2 — Generate Risk Register",
        use_container_width=True,
        disabled=not st.session_state.scope,
    )

    st.markdown("---")
    st.markdown("### 📊 Progress")
    steps = [
        ("Scope Statement", st.session_state.scope is not None),
        ("Risk Register", st.session_state.risks is not None),
        ("WBS / CPM", st.session_state.cpm_results is not None),
    ]
    for label, done in steps:
        icon = "✅" if done else "⬜"
        colour = "#4ade80" if done else "#475569"
        st.markdown(
            f'<span style="color:{colour}">{icon} {label}</span>',
            unsafe_allow_html=True,
        )

    if not can_scope:
        st.info("Fill in your API key, project name and description above to begin.")


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="pm-header">
  <h1>🤖 AI Project Management Assistant</h1>
  <p>Scope Planning &nbsp;·&nbsp; Risk Assessment &nbsp;·&nbsp; WBS &nbsp;·&nbsp; CPM / PERT Timeline</p>
</div>
""",
    unsafe_allow_html=True,
)

# ── Action handlers ────────────────────────────────────────────────────────────
if gen_scope_btn:
    with st.spinner("✍️  Generating Scope Statement…"):
        try:
            scope = generate_scope(api_key, project_name, project_description)
            st.session_state.scope = scope
            st.session_state.project_name = project_name
            # Reset downstream state
            st.session_state.risks = None
            st.session_state.wbs_data = None
            st.session_state.cpm_results = None
            st.success("✅ Scope Statement generated — see the first tab.")
        except Exception as exc:
            st.error(f"❌ Could not generate scope: {exc}")

if gen_risks_btn:
    with st.spinner("🔍  Identifying and assessing risks…"):
        try:
            risks = generate_risks(api_key, st.session_state.scope)
            st.session_state.risks = risks
            st.session_state.wbs_data = None
            st.session_state.cpm_results = None
            st.success("✅ Risk Register generated — see the second tab.")
        except Exception as exc:
            st.error(f"❌ Could not generate risks: {exc}")


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(
    ["📋  Scope Statement", "⚠️  Risk Register", "📊  WBS & CPM / PERT"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SCOPE STATEMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if st.session_state.scope:
        st.markdown(st.session_state.scope)
        st.download_button(
            "⬇️  Download Scope Statement (.txt)",
            data=st.session_state.scope,
            file_name=f"{st.session_state.project_name}_scope_statement.txt",
            mime="text/plain",
        )
    else:
        st.info(
            "👈  Fill in the sidebar and click **Step 1 — Generate Scope** to begin."
        )
        with st.expander("What is a Scope Statement?"):
            st.markdown(
                """
A **Project Scope Statement** is a foundational document that defines:

- **What** the project will produce (deliverables)
- **Why** it is being done (purpose & justification)
- **What is included** and, equally important, **what is not**
- The **constraints, assumptions, and success criteria**

It prevents scope creep and aligns all stakeholders before work begins.
"""
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RISK REGISTER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    if st.session_state.risks:
        risks = st.session_state.risks

        # Summary metrics
        high = sum(1 for r in risks if r["risk_score"] == "High")
        med  = sum(1 for r in risks if r["risk_score"] == "Medium")
        low  = sum(1 for r in risks if r["risk_score"] == "Low")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Risks",   len(risks))
        col2.metric("🔴 High",       high)
        col3.metric("🟡 Medium",     med)
        col4.metric("🟢 Low",        low)

        st.markdown("---")

        def _colour_score(val):
            mapping = {
                "High":   "background-color:#7f1d1d; color:#fca5a5; font-weight:700",
                "Medium": "background-color:#78350f; color:#fcd34d; font-weight:700",
                "Low":    "background-color:#14532d; color:#86efac; font-weight:700",
            }
            return mapping.get(val, "")

        df = pd.DataFrame(risks).rename(
            columns={
                "risk_id": "ID", "risk_name": "Risk Name",
                "category": "Category", "description": "Description",
                "likelihood": "Likelihood", "impact": "Impact",
                "risk_score": "Risk Score",
                "mitigation_strategy": "Mitigation Strategy",
            }
        )
        styled = df.style.applymap(
            _colour_score, subset=["Likelihood", "Impact", "Risk Score"]
        )
        st.dataframe(styled, use_container_width=True, height=420)

        csv = df.to_csv(index=False)
        st.download_button(
            "⬇️  Download Risk Register (.csv)",
            data=csv,
            file_name=f"{st.session_state.project_name}_risk_register.csv",
            mime="text/csv",
        )

    elif st.session_state.scope:
        st.info("👈  Click **Step 2 — Generate Risk Register** in the sidebar.")
    else:
        st.info("📋  Please generate a Scope Statement first (Tab 1).")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — WBS & CPM/PERT
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    if not st.session_state.risks:
        st.info("⚠️  Please complete the Scope Statement and Risk Register first.")
    else:
        # ── AI disclaimer ──────────────────────────────────────────────────────
        st.markdown(
            """
<div class="warn-box">
⚠️ <strong>Important Disclaimer — Please Read</strong><br>
The AI-generated Work Breakdown Structure and project timeline below are <em>rough planning estimates</em>
based solely on the text you provided. Actual timelines depend on real-world factors that AI cannot
account for: team skill levels, resource availability, organisational culture, client responsiveness,
regulatory approval times, technical debt, vendor delays, and many more.<br><br>
<strong>Use this as a starting point for discussion, not as a committed delivery schedule.
Always validate and adjust with your project team before sharing with stakeholders.</strong>
</div>
""",
            unsafe_allow_html=True,
        )

        # ── Mode selection ─────────────────────────────────────────────────────
        st.markdown("### How would you like to build the WBS & Timeline?")
        mode = st.radio(
            "",
            ["🤖  Let AI generate the WBS & Timeline", "✏️  I'll enter tasks manually"],
            horizontal=True,
        )

        # ────────────────────────────────────────────────────────────────────────
        # AI MODE
        # ────────────────────────────────────────────────────────────────────────
        if mode.startswith("🤖"):
            if st.button("🤖  Generate AI WBS & CPM/PERT", type="primary"):
                with st.spinner("🧠  Building WBS and calculating critical path…"):
                    try:
                        wbs_data = generate_wbs(
                            api_key,
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
                        st.success("✅  WBS and CPM/PERT analysis complete!")
                    except Exception as exc:
                        st.error(f"❌  Error: {exc}")

        # ────────────────────────────────────────────────────────────────────────
        # MANUAL MODE
        # ────────────────────────────────────────────────────────────────────────
        else:
            st.markdown("#### ✏️  Enter Your Tasks")
            st.caption(
                "Task IDs: T1, T2, T3 … &nbsp;|&nbsp; "
                "Durations in **days** &nbsp;|&nbsp; "
                "Dependencies: comma-separated IDs (e.g. T1, T2)"
            )

            if st.session_state.manual_tasks_list is None:
                st.session_state.manual_tasks_list = [
                    {
                        "task_id": f"T{i+1}", "task_name": "",
                        "optimistic": 1, "most_likely": 3, "pessimistic": 6,
                        "dependencies": "",
                    }
                    for i in range(4)
                ]

            if st.button("➕  Add Task"):
                n = len(st.session_state.manual_tasks_list) + 1
                st.session_state.manual_tasks_list.append(
                    {
                        "task_id": f"T{n}", "task_name": "",
                        "optimistic": 1, "most_likely": 3, "pessimistic": 6,
                        "dependencies": "",
                    }
                )

            updated = []
            for i, task in enumerate(st.session_state.manual_tasks_list):
                label = task["task_name"] or f"Task {i+1} (unnamed)"
                with st.expander(f"**{task['task_id']}** — {label}", expanded=(i < 3)):
                    c1, c2 = st.columns([1, 3])
                    tid   = c1.text_input("Task ID",   value=task["task_id"],   key=f"tid_{i}")
                    tname = c2.text_input("Task Name", value=task["task_name"], key=f"tname_{i}")

                    c3, c4, c5, c6 = st.columns(4)
                    opt  = c3.number_input("Optimistic (d)",  min_value=1, value=int(task["optimistic"]),  key=f"opt_{i}")
                    ml   = c4.number_input("Most Likely (d)", min_value=1, value=int(task["most_likely"]), key=f"ml_{i}")
                    pess = c5.number_input("Pessimistic (d)", min_value=1, value=int(task["pessimistic"]), key=f"pess_{i}")
                    deps = c6.text_input("Dependencies",      value=task["dependencies"],                  key=f"deps_{i}")

                    updated.append(
                        {
                            "task_id": tid.strip(), "task_name": tname.strip(),
                            "optimistic": opt, "most_likely": ml, "pessimistic": pess,
                            "dependencies": deps,
                        }
                    )

            # Persist form state
            st.session_state.manual_tasks_list = updated

            if st.button("📊  Calculate CPM / PERT", type="primary"):
                parsed = [
                    {
                        **t,
                        "dependencies": [
                            d.strip() for d in t["dependencies"].split(",") if d.strip()
                        ],
                    }
                    for t in updated
                    if t["task_name"] and t["task_id"]
                ]
                if len(parsed) < 2:
                    st.warning("Please enter at least 2 named tasks.")
                else:
                    try:
                        G, results_df, duration, cp = calculate_cpm(parsed)
                        st.session_state.cpm_results = {
                            "G": G, "df": results_df,
                            "duration": duration, "critical_path": cp,
                            "tasks": parsed,
                        }
                        st.session_state.wbs_data = None
                        st.success("✅  CPM/PERT analysis complete!")
                    except Exception as exc:
                        st.error(f"❌  {exc}")

        # ── WBS Display (AI mode only) ──────────────────────────────────────────
        if st.session_state.wbs_data:
            st.markdown("---")
            st.markdown('<div class="section-title">📁  Work Breakdown Structure</div>', unsafe_allow_html=True)

            wbs = st.session_state.wbs_data["wbs"]
            icons = {1: "📁", 2: "📂", 3: "📄"}
            for item in wbs:
                indent = "&nbsp;" * 6 * (item["level"] - 1)
                icon   = icons.get(item["level"], "📄")
                weight = "bold" if item["level"] == 1 else "normal"
                st.markdown(
                    f'{indent}{icon} <span style="font-weight:{weight}">'
                    f'{item["id"]} — {item["name"]}</span>',
                    unsafe_allow_html=True,
                )

        # ── CPM Results ────────────────────────────────────────────────────────
        if st.session_state.cpm_results:
            cpm = st.session_state.cpm_results

            st.markdown("---")
            st.markdown('<div class="section-title">📊  CPM / PERT Results</div>', unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            col1.metric("📅  Estimated Duration", f"{cpm['duration']:.1f} days")
            col2.metric("🔴  Critical Tasks",      len(cpm["critical_path"]))
            col3.metric("📋  Total Tasks",         len(cpm["tasks"]))

            cp_str = "  →  ".join(cpm["critical_path"])
            st.markdown(f"**Critical Path:** `{cp_str}`")

            # Task table
            st.markdown("#### Task Analysis Table")

            def _highlight_critical(row):
                if row["Critical"] == "✅ Yes":
                    return ["background-color:#450a0a; color:#fca5a5"] * len(row)
                return [""] * len(row)

            styled_df = cpm["df"].style.apply(_highlight_critical, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=380)

            # Gantt
            st.markdown("#### 📅  Gantt Chart (Critical Path)")
            fig = plot_gantt(cpm["G"], cpm["tasks"])
            st.pyplot(fig)
            plt.close(fig)

            # Downloads
            dl_col1, dl_col2 = st.columns(2)
            csv = cpm["df"].to_csv(index=False)
            dl_col1.download_button(
                "⬇️  Download CPM Table (.csv)",
                data=csv,
                file_name=f"{st.session_state.project_name}_cpm_analysis.csv",
                mime="text/csv",
            )

            # Save Gantt as PNG for download
            buf = io.BytesIO()
            fig2 = plot_gantt(cpm["G"], cpm["tasks"])
            fig2.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                         facecolor="#0e1117")
            plt.close(fig2)
            buf.seek(0)
            dl_col2.download_button(
                "⬇️  Download Gantt Chart (.png)",
                data=buf,
                file_name=f"{st.session_state.project_name}_gantt.png",
                mime="image/png",
            )
