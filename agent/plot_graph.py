import sys
import json
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Visual config ─────────────────────────────────────────────────────────────

SKILL_COLORS = {
    "planner":          "#AED6F1",   # blue
    "researcher":       "#A9DFBF",   # green
    "distiller":        "#F9E79F",   # yellow
    "summariser":       "#F0E6FF",   # lavender
    "critic":           "#FAD7A0",   # orange
    "formatter":        "#85C1E9",   # strong blue
    "coder":            "#F1948A",   # salmon
    "sandbox_executor": "#FDEBD0",   # peach
    "retriever":        "#D5F5E3",   # mint
    "browser":          "#E8DAEF",   # lilac
}
DEFAULT_SKILL_COLOR = "#EAECEE"

STATUS_BORDER = {
    "complete": ("#27AE60", 2.5),   # green border
    "failed":   ("#E74C3C", 3.0),   # red border
    "skipped":  ("#95A5A6", 1.5),   # gray border, dashed
    "running":  ("#2980B9", 2.5),   # blue border
    "pending":  ("#BDC3C7", 1.5),   # light gray
}
STATUS_ALPHA = {
    "complete": 1.0,
    "failed":   1.0,
    "skipped":  0.45,
    "running":  1.0,
    "pending":  0.7,
}


def _layered_layout(g: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Compute a top-to-bottom layered (Sugiyama-style) layout using
    longest-path layer assignment so the DAG reads naturally."""
    # Assign each node to a layer = length of the longest path from any root.
    layers: dict[str, int] = {}
    for node in nx.topological_sort(g):
        preds = list(g.predecessors(node))
        layers[node] = 0 if not preds else max(layers[p] for p in preds) + 1

    # Group nodes per layer; sort within a layer by node id for stability.
    from collections import defaultdict
    layer_members: dict[int, list[str]] = defaultdict(list)
    for node, layer in layers.items():
        layer_members[layer].append(node)
    for members in layer_members.values():
        members.sort()

    max_width = max(len(m) for m in layer_members.values())
    x_gap = max(2.5, 8.0 / max(max_width, 1))
    y_gap = 2.0

    pos: dict[str, tuple[float, float]] = {}
    for layer, members in layer_members.items():
        n = len(members)
        # Centre the row horizontally.
        x_start = -((n - 1) * x_gap) / 2
        for i, node in enumerate(members):
            pos[node] = (x_start + i * x_gap, -(layer * y_gap))
    return pos


def plot_session_graph(session_id: str):
    session_dir = Path(__file__).parent / "state" / "sessions" / session_id
    graph_path = session_dir / "graph.json"

    if not graph_path.exists():
        print(f"Graph file not found: {graph_path}")
        return

    with open(graph_path) as f:
        payload = json.load(f)
    g = nx.node_link_graph(payload, edges="edges", directed=True)

    if not g:
        print("Graph is empty.")
        return

    # ── Layout ────────────────────────────────────────────────────────────────
    # Fall back to spring if the graph has cycles (shouldn't happen, but safe).
    try:
        pos = _layered_layout(g)
    except nx.NetworkXUnfeasible:
        pos = nx.spring_layout(g, seed=42)

    # ── Per-node visuals ──────────────────────────────────────────────────────
    nodes = list(g.nodes())
    node_colors, border_colors, border_widths, alphas = [], [], [], []
    labels = {}

    for node in nodes:
        data = g.nodes[node]
        skill = data.get("skill", "unknown")
        status = data.get("status", "pending")
        question = (data.get("metadata") or {}).get("question", "")
        truncated = (question[:28] + "...") if len(question) > 28 else question
        question_hint = f'\n"{truncated}"' if question else ""

        labels[node] = f"{node}\n{skill}{question_hint}"
        node_colors.append(SKILL_COLORS.get(skill, DEFAULT_SKILL_COLOR))
        bc, bw = STATUS_BORDER.get(status, ("#BDC3C7", 1.5))
        border_colors.append(bc)
        border_widths.append(bw)
        alphas.append(STATUS_ALPHA.get(status, 0.8))

    # ── Figure ────────────────────────────────────────────────────────────────
    n_nodes = len(nodes)
    fig_w = max(12, n_nodes * 1.8)
    fig_h = max(8, (max(pos[n][1] for n in pos) - min(pos[n][1] for n in pos)) * 0.9 + 4)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_facecolor("#FAFAFA")
    fig.patch.set_facecolor("#FAFAFA")

    # Draw edges first so they sit under nodes.
    nx.draw_networkx_edges(
        g, pos, ax=ax,
        edge_color="#7F8C8D",
        arrows=True,
        arrowstyle="-|>",
        arrowsize=18,
        width=1.8,
        connectionstyle="arc3,rad=0.08",
        min_source_margin=22,
        min_target_margin=22,
    )

    # Draw nodes one at a time so we can vary border colour and alpha.
    for node, color, bc, bw, alpha in zip(
            nodes, node_colors, border_colors, border_widths, alphas):
        nx.draw_networkx_nodes(
            g, pos, nodelist=[node], ax=ax,
            node_color=[color],
            node_size=2200,
            alpha=alpha,
            edgecolors=bc,
            linewidths=bw,
        )

    nx.draw_networkx_labels(g, pos, labels=labels, ax=ax,
                            font_size=7, font_weight="bold", font_color="#1A1A2E")

    # ── Legend ────────────────────────────────────────────────────────────────
    skill_legend = [
        mpatches.Patch(facecolor=c, edgecolor="#555", label=s)
        for s, c in SKILL_COLORS.items() if any(
            g.nodes[n].get("skill") == s for n in g.nodes
        )
    ]
    status_legend = [
        mpatches.Patch(facecolor="white", edgecolor=bc, linewidth=bw,
                       label=f"{st} (border)")
        for st, (bc, bw) in STATUS_BORDER.items()
    ]
    legend1 = ax.legend(handles=skill_legend, title="Skill", loc="upper left",
                        fontsize=7, title_fontsize=8, framealpha=0.85)
    ax.add_artist(legend1)
    ax.legend(handles=status_legend, title="Status", loc="upper right",
              fontsize=7, title_fontsize=8, framealpha=0.85)

    # ── Title ─────────────────────────────────────────────────────────────────
    n_complete = sum(1 for _, d in g.nodes(data=True) if d.get("status") == "complete")
    n_failed   = sum(1 for _, d in g.nodes(data=True) if d.get("status") == "failed")
    ax.set_title(
        f"Session {session_id}  ·  {n_nodes} nodes  "
        f"({n_complete} complete, {n_failed} failed)",
        fontsize=11, fontweight="bold", pad=14,
    )
    ax.axis("off")

    output_path = session_dir / "graph.png"
    plt.savefig(output_path, bbox_inches="tight", dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    print(f"Graph plot saved to:\n  {output_path.relative_to(Path(__file__).parent)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plot_graph.py <session_id>")
    else:
        plot_session_graph(sys.argv[1])
