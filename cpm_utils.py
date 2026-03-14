import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd


def calculate_pert_duration(optimistic, most_likely, pessimistic):
    return (optimistic + 4 * most_likely + pessimistic) / 6


def calculate_pert_variance(optimistic, pessimistic):
    return ((pessimistic - optimistic) / 6) ** 2


def calculate_cpm(tasks):
    """
    tasks: list of dicts with keys:
        task_id, task_name, optimistic, most_likely, pessimistic, dependencies (list)
    Returns: (G, results_df, project_duration, critical_path)
    """
    G = nx.DiGraph()

    for task in tasks:
        duration = calculate_pert_duration(
            task["optimistic"], task["most_likely"], task["pessimistic"]
        )
        variance = calculate_pert_variance(task["optimistic"], task["pessimistic"])
        G.add_node(
            task["task_id"],
            name=task["task_name"],
            duration=round(duration, 2),
            variance=round(variance, 2),
            optimistic=task["optimistic"],
            most_likely=task["most_likely"],
            pessimistic=task["pessimistic"],
            ES=0, EF=0, LS=0, LF=0, float=0,
        )

    for task in tasks:
        for dep in task.get("dependencies", []):
            if dep in G.nodes:
                G.add_edge(dep, task["task_id"])

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
        G.nodes[node]["LF"] = min(
            (G.nodes[s]["LS"] for s in succs), default=project_duration
        )
        G.nodes[node]["LS"] = round(G.nodes[node]["LF"] - G.nodes[node]["duration"], 2)
        G.nodes[node]["float"] = round(G.nodes[node]["LS"] - G.nodes[node]["ES"], 2)

    critical_path = [n for n in G.nodes if G.nodes[n]["float"] == 0]

    rows = []
    for task in tasks:
        tid = task["task_id"]
        if tid not in G.nodes:
            continue
        nd = G.nodes[tid]
        rows.append(
            {
                "Task ID": tid,
                "Task Name": nd["name"],
                "Optimistic (d)": nd["optimistic"],
                "Most Likely (d)": nd["most_likely"],
                "Pessimistic (d)": nd["pessimistic"],
                "PERT Duration (d)": nd["duration"],
                "Variance": nd["variance"],
                "ES": nd["ES"],
                "EF": nd["EF"],
                "LS": nd["LS"],
                "LF": nd["LF"],
                "Float": nd["float"],
                "Critical": "✅ Yes" if nd["float"] == 0 else "No",
            }
        )

    results_df = pd.DataFrame(rows)
    return G, results_df, project_duration, critical_path


def plot_gantt(G, tasks):
    task_ids = [t["task_id"] for t in tasks if t["task_id"] in G.nodes]
    fig_height = max(5, len(task_ids) * 0.55 + 2)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#161b22")

    for i, tid in enumerate(task_ids):
        nd = G.nodes[tid]
        color = "#e74c3c" if nd["float"] == 0 else "#3b82f6"
        ax.barh(
            i, nd["duration"], left=nd["ES"],
            color=color, alpha=0.88, edgecolor="#ffffff22", linewidth=0.5, height=0.6,
        )
        if nd["duration"] > 0.8:
            ax.text(
                nd["ES"] + nd["duration"] / 2, i,
                f"{nd['duration']}d",
                ha="center", va="center", color="white", fontsize=7.5, fontweight="bold",
            )

    labels = [f"{tid}  {G.nodes[tid]['name'][:28]}" for tid in task_ids]
    ax.set_yticks(range(len(task_ids)))
    ax.set_yticklabels(labels, color="#e2e8f0", fontsize=8.5)
    ax.set_xlabel("Days from Project Start", color="#94a3b8", fontsize=9)
    ax.set_title("Gantt Chart — Critical Path Highlighted in Red", color="white", fontsize=12, fontweight="bold", pad=12)
    ax.tick_params(colors="#94a3b8", labelsize=8)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["bottom", "left"]:
        ax.spines[spine].set_color("#334155")
    ax.xaxis.grid(True, color="#1e293b", linewidth=0.7, linestyle="--")
    ax.set_axisbelow(True)

    critical_patch = mpatches.Patch(color="#e74c3c", label="Critical Path")
    normal_patch = mpatches.Patch(color="#3b82f6", label="Non-Critical")
    legend = ax.legend(
        handles=[critical_patch, normal_patch], loc="lower right",
        facecolor="#1e293b", edgecolor="#334155", labelcolor="white", fontsize=9,
    )
    plt.tight_layout()
    return fig
