import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
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
            name=t["task_name"], duration=round(dur,2), variance=round(var,2),
            optimistic=t["optimistic"], most_likely=t["most_likely"], pessimistic=t["pessimistic"],
            phase=t.get("phase",""), resource=t.get("resource",""), deliverable=t.get("deliverable",""),
            ES=0, EF=0, LS=0, LF=0, float=0)
    for t in tasks:
        for dep in t.get("dependencies",[]):
            if dep in G.nodes:
                G.add_edge(dep, t["task_id"])
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError("Circular dependency detected.")
    for node in nx.topological_sort(G):
        preds = list(G.predecessors(node))
        G.nodes[node]["ES"] = max((G.nodes[p]["EF"] for p in preds), default=0)
        G.nodes[node]["EF"] = round(G.nodes[node]["ES"] + G.nodes[node]["duration"], 2)
    project_duration = max(G.nodes[n]["EF"] for n in G.nodes)
    for node in reversed(list(nx.topological_sort(G))):
        succs = list(G.successors(node))
        G.nodes[node]["LF"] = min((G.nodes[s]["LS"] for s in succs), default=project_duration)
        G.nodes[node]["LS"] = round(G.nodes[node]["LF"] - G.nodes[node]["duration"], 2)
        G.nodes[node]["float"] = round(G.nodes[node]["LS"] - G.nodes[node]["ES"], 2)
    critical_path = [n for n in nx.topological_sort(G) if abs(G.nodes[n]["float"]) < 0.01]
    rows = []
    for t in tasks:
        tid = t["task_id"]
        if tid not in G.nodes: continue
        nd = G.nodes[tid]
        is_crit = abs(nd["float"]) < 0.01
        rows.append({
            "ID": tid, "Task": nd["name"], "Phase": nd.get("phase",""),
            "Resource": nd.get("resource",""),
            "Opt": nd["optimistic"], "ML": nd["most_likely"], "Pess": nd["pessimistic"],
            "PERT (d)": nd["duration"], "Variance": nd["variance"],
            "ES": nd["ES"], "EF": nd["EF"], "LS": nd["LS"], "LF": nd["LF"],
            "Float (d)": nd["float"],
            "Path": "🔴 Critical" if is_crit else "🟢 Non-Critical",
        })
    return G, pd.DataFrame(rows), project_duration, critical_path


def plot_gantt(G, tasks):
    task_ids = [t["task_id"] for t in tasks if t["task_id"] in G.nodes]
    n = len(task_ids)
    fig_h = max(7, n * 0.70 + 3.5)

    plt.rcParams.update({
        "font.family":    "monospace",
        "text.color":     "#aaaaaa",
        "axes.labelcolor":"#555555",
        "xtick.color":    "#333333",
        "ytick.color":    "#bbbbbb",
    })

    fig, ax = plt.subplots(figsize=(16, fig_h))
    fig.patch.set_facecolor("#080808")
    ax.set_facecolor("#0a0a0a")

    phase_tints = {
        "Initiation":             "#091522",
        "Planning":               "#091508",
        "Execution":              "#150915",
        "Monitoring & Control":   "#150f09",
        "Monitoring and Control": "#150f09",
        "Closure":                "#0e0e0e",
    }

    max_ef = max((G.nodes[tid]["EF"] + G.nodes[tid]["float"]) for tid in task_ids) * 1.05

    # Row bands
    for i in range(n):
        ax.axhspan(i - 0.5, i + 0.5,
                   color="#0d0d0d" if i % 2 == 0 else "#0a0a0a", zorder=0)

    for i, tid in enumerate(task_ids):
        nd        = G.nodes[tid]
        is_crit   = abs(nd["float"]) < 0.01
        phase     = nd.get("phase", "")

        # Phase tint
        tint = phase_tints.get(phase, "#0c0c0c")
        ax.barh(i, max_ef, left=0, color=tint, height=0.95, alpha=1.0, zorder=1)

        # Float bar
        if nd["float"] > 0.1:
            ax.barh(i, nd["float"], left=nd["EF"],
                    color="#0d2040", alpha=0.8, height=0.32, zorder=2,
                    edgecolor="#1e4080", linewidth=0.6)
            ax.text(nd["EF"] + nd["float"]/2, i,
                    "+{:.1f}d".format(nd["float"]),
                    ha="center", va="center", color="#2a5080",
                    fontsize=6, fontfamily="monospace", zorder=5)

        # Main bar
        if is_crit:
            bar_c = "#8b1a1a"; edge_c = "#dd4444"; lbl_c = "#ffaaaa"
        else:
            bar_c = "#0e2d5c"; edge_c = "#2a6acc"; lbl_c = "#88aadd"

        ax.barh(i, nd["duration"], left=nd["ES"],
                color=bar_c, alpha=0.95, height=0.50,
                edgecolor=edge_c, linewidth=0.9, zorder=3)

        # Start marker
        ax.plot(nd["ES"], i, "|", color=edge_c,
                markersize=8, markeredgewidth=1.2, alpha=0.8, zorder=4)

        # Duration label
        if nd["duration"] >= 1.5:
            ax.text(nd["ES"] + nd["duration"]/2, i,
                    "{:.1f}d".format(nd["duration"]),
                    ha="center", va="center", color=lbl_c,
                    fontsize=7, fontfamily="monospace", fontweight="bold", zorder=5)

    # Y labels
    ylabels = []
    for tid in task_ids:
        nd   = G.nodes[tid]
        name = nd["name"][:29] + ("…" if len(nd["name"]) > 29 else "")
        ylabels.append("{}  {}".format(tid, name))

    ax.set_yticks(range(n))
    ax.set_yticklabels(ylabels, fontsize=8.5, fontfamily="monospace", color="#bbbbbb")
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlim(0, max_ef)

    # Grid
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(5))
    ax.grid(True, axis="x", which="major", color="#161616", linewidth=0.6, zorder=1)
    ax.grid(True, axis="x", which="minor", color="#111111", linewidth=0.3, zorder=1)
    ax.set_axisbelow(True)

    ax.set_xlabel("Days from Project Start", fontsize=8.5, color="#444444",
                  fontfamily="monospace", labelpad=10)
    ax.set_title("GANTT CHART  ·  Critical Path & Float Analysis",
                 fontsize=9.5, fontfamily="monospace", color="#555555",
                 fontweight="normal", pad=14, loc="left")

    for sp in ["top","right"]: ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#1a1a1a")
    ax.spines["left"].set_color("#1a1a1a")
    ax.tick_params(axis="x", colors="#333", labelsize=8)
    ax.tick_params(axis="y", colors="#777", labelsize=8.5)

    # Legend
    p1 = mpatches.Patch(facecolor="#8b1a1a", edgecolor="#dd4444", lw=0.9, label="Critical Path")
    p2 = mpatches.Patch(facecolor="#0e2d5c", edgecolor="#2a6acc", lw=0.9, label="Non-Critical")
    p3 = mpatches.Patch(color="#0d2040", alpha=0.8, label="Free Float")
    ax.legend(handles=[p1,p2,p3], loc="lower right",
              facecolor="#0c0c0c", edgecolor="#1e1e1e",
              labelcolor="#777777", fontsize=8, framealpha=0.95, borderpad=0.8)

    plt.tight_layout(pad=1.8)
    return fig
