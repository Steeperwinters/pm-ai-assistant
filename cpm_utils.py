import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import pandas as pd


def calculate_pert_duration(o, m, p):
    return (o + 4 * m + p) / 6


def calculate_pert_variance(o, p):
    return ((p - o) / 6) ** 2


def calculate_cpm(tasks):
    G = nx.DiGraph()

    for t in tasks:
        dur = calculate_pert_duration(t["optimistic"], t["most_likely"], t["pessimistic"])
        var = calculate_pert_variance(t["optimistic"], t["pessimistic"])
        G.add_node(t["task_id"],
            name=t["task_name"],
            duration=round(dur, 2),
            variance=round(var, 2),
            optimistic=t["optimistic"],
            most_likely=t["most_likely"],
            pessimistic=t["pessimistic"],
            phase=t.get("phase", ""),
            resource=t.get("resource", ""),
            deliverable=t.get("deliverable", ""),
            ES=0, EF=0, LS=0, LF=0, float=0,
        )

    for t in tasks:
        for dep in t.get("dependencies", []):
            if dep in G.nodes:
                G.add_edge(dep, t["task_id"])

    if not nx.is_directed_acyclic_graph(G):
        raise ValueError("Circular dependency detected — please review your task list.")

    # Forward pass
    for node in nx.topological_sort(G):
        preds = list(G.predecessors(node))
        G.nodes[node]["ES"] = max((G.nodes[p]["EF"] for p in preds), default=0)
        G.nodes[node]["EF"] = round(G.nodes[node]["ES"] + G.nodes[node]["duration"], 2)

    project_duration = max(G.nodes[n]["EF"] for n in G.nodes)

    # Backward pass
    for node in reversed(list(nx.topological_sort(G))):
        succs = list(G.successors(node))
        G.nodes[node]["LF"] = min((G.nodes[s]["LS"] for s in succs), default=project_duration)
        G.nodes[node]["LS"] = round(G.nodes[node]["LF"] - G.nodes[node]["duration"], 2)
        G.nodes[node]["float"] = round(G.nodes[node]["LS"] - G.nodes[node]["ES"], 2)

    critical_path = [n for n in nx.topological_sort(G) if abs(G.nodes[n]["float"]) < 0.01]

    rows = []
    for t in tasks:
        tid = t["task_id"]
        if tid not in G.nodes:
            continue
        nd = G.nodes[tid]
        is_critical = abs(nd["float"]) < 0.01
        rows.append({
            "Task ID":          tid,
            "Task Name":        nd["name"],
            "Phase":            nd.get("phase", ""),
            "Resource":         nd.get("resource", ""),
            "Optimistic (d)":   nd["optimistic"],
            "Most Likely (d)":  nd["most_likely"],
            "Pessimistic (d)":  nd["pessimistic"],
            "PERT Duration (d)":nd["duration"],
            "Variance":         nd["variance"],
            "ES":  nd["ES"],
            "EF":  nd["EF"],
            "LS":  nd["LS"],
            "LF":  nd["LF"],
            "Float (d)":        nd["float"],
            "Critical":         "🔴 Critical" if is_critical else "🟢 Non-Critical",
        })

    return G, pd.DataFrame(rows), project_duration, critical_path


def plot_gantt(G, tasks):
    task_ids = [t["task_id"] for t in tasks if t["task_id"] in G.nodes]
    n = len(task_ids)
    fig_h = max(6, n * 0.62 + 2.5)
    fig, ax = plt.subplots(figsize=(15, fig_h))
    fig.patch.set_facecolor("#080808")
    ax.set_facecolor("#0c0c0c")

    phase_colors = {
        "Initiation":             "#1a3a5c",
        "Planning":               "#1a3a2a",
        "Execution":              "#3a1a3a",
        "Monitoring & Control":   "#3a2a1a",
        "Monitoring and Control": "#3a2a1a",
        "Closure":                "#2a2a1a",
    }

    for i, tid in enumerate(task_ids):
        nd = G.nodes[tid]
        is_critical = abs(nd["float"]) < 0.01
        phase = nd.get("phase", "")

        bar_color  = "#ff4060" if is_critical else "#1e6fff"
        glow_color = "#ff406088" if is_critical else "#1e6fff55"

        # Phase background
        ph_col = phase_colors.get(phase, "#111")
        ax.barh(i, nd["duration"], left=nd["ES"],
                color=ph_col, height=0.72, alpha=0.35)

        # Main bar
        ax.barh(i, nd["duration"], left=nd["ES"],
                color=bar_color, alpha=0.90, height=0.62,
                edgecolor="#ffffff18", linewidth=0.5)

        # Float bar (non-critical only)
        if nd["float"] > 0:
            ax.barh(i, nd["float"], left=nd["EF"],
                    color="#1e6fff", alpha=0.18, height=0.3,
                    edgecolor="#1e6fff55", linewidth=0.5,
                    linestyle="--")
            ax.annotate(
                f"+{nd['float']:.0f}d float",
                xy=(nd["EF"] + nd["float"] / 2, i),
                fontfamily="monospace", fontsize=6.5,
                color="#1e6fff", alpha=0.7, ha="center", va="center",
            )

        # Duration label inside bar
        if nd["duration"] > 1:
            ax.text(nd["ES"] + nd["duration"] / 2, i,
                    f"{nd['duration']:.1f}d",
                    ha="center", va="center",
                    color="white", fontsize=7.5, fontweight="bold")

        # Start marker
        ax.plot(nd["ES"], i, "o", color=bar_color, markersize=4, alpha=0.8)

    # Y-axis labels
    ylabels = [f"{tid}  {G.nodes[tid]['name'][:30]}" for tid in task_ids]
    ax.set_yticks(range(n))
    ax.set_yticklabels(ylabels, color="#cccccc", fontsize=8.5, fontfamily="monospace")

    ax.set_xlabel("Days from Project Start", color="#888", fontsize=9, fontfamily="monospace")
    ax.set_title("Gantt Chart — Critical Path & Float Analysis",
                 color="#ffffff", fontsize=12, fontweight="bold", pad=14,
                 fontfamily="monospace")

    ax.tick_params(colors="#555", labelsize=8)
    for sp in ["top", "right"]:  ax.spines[sp].set_visible(False)
    for sp in ["bottom", "left"]: ax.spines[sp].set_color("#1e1e1e")

    ax.xaxis.grid(True, color="#1a1a1a", linewidth=0.6, linestyle="--")
    ax.set_axisbelow(True)

    # Today line at 0
    ax.axvline(x=0, color="#00ff8740", linewidth=1, linestyle=":")

    # Legend
    p1 = mpatches.Patch(color="#ff4060", label="Critical Path")
    p2 = mpatches.Patch(color="#1e6fff", label="Non-Critical")
    p3 = mpatches.Patch(color="#1e6fff", alpha=0.25, label="Free Float")
    ax.legend(handles=[p1, p2, p3], loc="lower right",
              facecolor="#0c0c0c", edgecolor="#1e1e1e",
              labelcolor="#aaa", fontsize=8.5)

    plt.tight_layout()
    return fig
