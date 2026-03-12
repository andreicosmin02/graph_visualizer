"""Step-by-step visualizer for the Generic Max Flow algorithm."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import List, Optional

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import FancyArrowPatch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from algorithms.generic_max_flow import FlowStep, run_generic_max_flow
from core.graph import Graph, Node
from ui.components import (
    Card, HoverButton, PhaseBadge, ProgressBar,
    SectionHeader, Separator, ThemedFrame,
)

# ── Palette ───────────────────────────────────────────────────────────────────
_BG       = '#131214'
_CARD_BG  = '#2E2A33'
_TEXT     = '#C5AD89'
_TEXT_DIM = '#82715B'
_BORDER   = '#524A45'
_BOX_FACE = '#1a1516'

# node colours
_NODE_DEFAULT = '#C5AD89'   # warm beige
_NODE_SOURCE  = '#9BCB2F'   # green indicator
_NODE_SINK    = '#802525'   # danger red
_NODE_PATH    = '#F1C232'   # yellow (on path)

# edge colours
_EDGE_RESIDUAL = '#82715B'  # bronze dim
_EDGE_PATH     = '#F1C232'  # bright yellow
_EDGE_FLOW     = '#9BCB2F'  # green (final flow view)



class GenericMaxFlowVisualizer:
    """Toplevel window that plays back the Generic Max Flow execution."""

    def __init__(self, parent: tk.Tk, graph: Graph,
                 source: str, sink: str) -> None:
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror(
                "Missing dependency",
                "matplotlib is required for the visualizer.")
            return

        self._parent = parent
        self._graph  = graph
        self._source = source
        self._sink   = sink
        self._steps: List[FlowStep] = []
        self._current = 0

        self._run_algorithm()
        self._build_window()

    # ── algorithm ─────────────────────────────────────────────────────────────

    def _run_algorithm(self) -> None:
        edges = [
            (e.source, e.target,
             e.capacity if e.capacity is not None else 0.0)
            for e in self._graph.edges
        ]
        self._steps = run_generic_max_flow(
            list(self._graph.nodes.keys()), edges,
            self._source, self._sink)

    # ── window ────────────────────────────────────────────────────────────────

    def _build_window(self) -> None:
        win = tk.Toplevel(self._parent)
        win.title("Generic Max Flow — Step-by-Step Visualizer")
        win.geometry("1300x780")
        win.minsize(900, 520)
        win.config(bg=_BG)
        self._win = win

        # top bar
        top = tk.Frame(win, bg=_CARD_BG, height=44)
        top.pack(fill=tk.X)
        top.pack_propagate(False)
        tk.Label(top, text="Generic Max Flow Visualizer",
                 bg=_CARD_BG, fg=_TEXT,
                 font=('Segoe UI', 12, 'bold'), padx=14).pack(side=tk.LEFT, pady=10)
        tk.Label(top, text=f"s = {self._source}     t = {self._sink}",
                 bg=_CARD_BG, fg=_TEXT_DIM,
                 font=('Segoe UI', 10), padx=14).pack(side=tk.RIGHT, pady=10)
        Separator(win, color=_BORDER).pack(fill=tk.X)

        # body
        body = ThemedFrame(win)
        body.pack(fill=tk.BOTH, expand=True)

        # left: matplotlib canvas
        canvas_frame = ThemedFrame(body)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._fig = Figure(figsize=(9, 6), dpi=100)
        self._fig.patch.set_facecolor(_BG)
        self._ax  = self._fig.add_subplot(111)
        self._mpl = FigureCanvasTkAgg(self._fig, master=canvas_frame)
        self._mpl.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        Separator(body, color=_BORDER).pack(side=tk.LEFT, fill=tk.Y)

        # right panel (fixed width, scrolling handled by layout order)
        panel = tk.Frame(body, bg=_BG, width=300)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)

        self._build_panel(panel)

        # keyboard shortcuts
        win.bind('<Left>',  lambda _e: self._prev())
        win.bind('<Right>', lambda _e: self._next())
        win.bind('<Home>',  lambda _e: self._goto(0))
        win.bind('<End>',   lambda _e: self._goto(len(self._steps) - 1))

        self._render()

    def _build_panel(self, panel: tk.Frame) -> None:
        # ── BOTTOM items packed first so they always stay visible ─────────────

        # keyboard hint (very bottom)
        tk.Label(panel, text="← → keys  |  Home / End",
                 bg=_CARD_BG, fg=_TEXT_DIM,
                 font=('Segoe UI', 8), pady=5).pack(
            side=tk.BOTTOM, fill=tk.X)

        # navigation buttons
        nav_card = Card(panel)
        nav_card.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 4))

        btn_row = tk.Frame(nav_card, bg=_CARD_BG)
        btn_row.pack(fill=tk.X, padx=6, pady=6)

        self._nav_buttons: List[HoverButton] = []
        for label, cmd in [
            ("|◀", lambda: self._goto(0)),
            ("◀",  self._prev),
            ("▶",  self._next),
            ("▶|", lambda: self._goto(len(self._steps) - 1)),
        ]:
            b = HoverButton(btn_row, text=label, command=cmd,
                            font=('Segoe UI', 12, 'bold'),
                            padx=8, pady=5)
            b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            self._nav_buttons.append(b)

        # legend
        leg_card = Card(panel)
        leg_card.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(4, 0))
        SectionHeader(leg_card, text="Legend").pack(fill=tk.X)
        for color, sym, label in [
            (_NODE_SOURCE,   '●', f'Source  ({self._source})'),
            (_NODE_SINK,     '●', f'Sink  ({self._sink})'),
            (_NODE_PATH,     '●', 'Node on path'),
            (_NODE_DEFAULT,  '●', 'Other node'),
            (_EDGE_PATH,     '→', 'Augmenting path arc'),
            (_EDGE_RESIDUAL, '→', 'Residual arc'),
            (_EDGE_FLOW,     '→', 'Flow arc  (final)'),
        ]:
            row = tk.Frame(leg_card, bg=_CARD_BG)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=sym, fg=color, bg=_CARD_BG,
                     font=('Segoe UI', 11, 'bold'), width=3).pack(side=tk.LEFT)
            tk.Label(row, text=label, fg=_TEXT_DIM, bg=_CARD_BG,
                     font=('Segoe UI', 8)).pack(side=tk.LEFT)

        # ── TOP items ─────────────────────────────────────────────────────────

        # phase badge
        self._phase_badge = PhaseBadge(panel)
        self._phase_badge.pack(fill=tk.X, padx=8, pady=(10, 4))

        # step counter + progress bar
        counter_card = Card(panel)
        counter_card.pack(fill=tk.X, padx=8)
        self._step_lbl = tk.Label(counter_card, text="",
                                   bg=_CARD_BG, fg=_TEXT,
                                   font=('Segoe UI', 10, 'bold'))
        self._step_lbl.pack(anchor=tk.W, padx=10, pady=(6, 3))
        self._progress = ProgressBar(counter_card, height=5)
        self._progress.pack(fill=tk.X, padx=10, pady=(0, 8))

        # ── MIDDLE: description fills remaining space ─────────────────────────
        desc_card = Card(panel)
        desc_card.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 0))
        SectionHeader(desc_card, text="Step Details").pack(fill=tk.X)

        txt_wrap = tk.Frame(desc_card, bg=_CARD_BG)
        txt_wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        sb = tk.Scrollbar(txt_wrap, bg=_CARD_BG, troughcolor=_BG,
                          activebackground=_BORDER)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._desc = tk.Text(
            txt_wrap,
            bg='#0e0d0f',
            fg=_TEXT,
            font=('Courier New', 10),
            wrap=tk.WORD,
            relief=tk.FLAT,
            state=tk.DISABLED,
            yscrollcommand=sb.set,
            padx=8, pady=6,
            spacing1=2, spacing3=2,
        )
        self._desc.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self._desc.yview)

    # ── navigation ────────────────────────────────────────────────────────────

    def _prev(self) -> None:
        if self._current > 0:
            self._current -= 1
            self._render()

    def _next(self) -> None:
        if self._current < len(self._steps) - 1:
            self._current += 1
            self._render()

    def _goto(self, idx: int) -> None:
        self._current = max(0, min(idx, len(self._steps) - 1))
        self._render()

    # ── render ────────────────────────────────────────────────────────────────

    def _render(self) -> None:
        step  = self._steps[self._current]
        total = len(self._steps)
        idx   = self._current

        self._phase_badge.set_phase(step.phase)
        self._step_lbl.config(text=f"Step {idx + 1} of {total}")
        self._progress.set(idx, total)

        self._desc.config(state=tk.NORMAL)
        self._desc.delete('1.0', tk.END)
        self._desc.insert(tk.END, step.description)
        self._desc.config(state=tk.DISABLED)
        self._desc.see('1.0')

        at_start = idx == 0
        at_end   = idx == total - 1
        for btn, disabled in zip(self._nav_buttons,
                                  [at_start, at_start, at_end, at_end]):
            btn.config(state=tk.DISABLED if disabled else tk.NORMAL)

        if step.phase == 'final':
            self._draw_flow_graph(step)
        else:
            self._draw_residual_graph(step)

    # ── graph drawing ─────────────────────────────────────────────────────────

    def _draw_residual_graph(self, step: FlowStep) -> None:
        ax = self._ax
        ax.clear()
        ax.set_facecolor(_BG)
        ax.axis('off')

        nodes = list(self._graph.nodes.values())
        if not nodes:
            self._mpl.draw_idle()
            return

        self._set_limits(ax, nodes)

        node_map = {n.id: n for n in nodes}

        path_arcs: set = set()
        path_nodes: set = set()
        if step.path:
            path_nodes = set(step.path)
            for i in range(len(step.path) - 1):
                path_arcs.add((step.path[i], step.path[i + 1]))

        active = set(step.residual.keys())

        for (u, v), res in step.residual.items():
            src = node_map.get(u)
            tgt = node_map.get(v)
            if src is None or tgt is None:
                continue
            is_path = (u, v) in path_arcs
            has_rev = (v, u) in active
            rad     = 0.25 if has_rev else 0.0
            color   = _EDGE_PATH     if is_path else _EDGE_RESIDUAL
            lw      = 2.5            if is_path else 1.5
            self._draw_arrow(ax, src, tgt, color, lw, rad)
            self._draw_label(ax, src, tgt, _fmt(res), rad, highlight=is_path)

        self._draw_nodes(ax, nodes, path_nodes)

        if step.path:
            path_str = " \u2192 ".join(step.path)
            title = (f"Residual Network  \u2014  "
                     f"D\u0303 = ({path_str}),  r = {_fmt(step.path_residual)}")
        else:
            title = "Residual Network  \u2014  Initial State"

        ax.set_title(title, color=_TEXT, fontsize=10, pad=10)
        self._mpl.draw_idle()

    def _draw_flow_graph(self, step: FlowStep) -> None:
        ax = self._ax
        ax.clear()
        ax.set_facecolor(_BG)
        ax.axis('off')

        nodes = list(self._graph.nodes.values())
        if not nodes:
            self._mpl.draw_idle()
            return

        self._set_limits(ax, nodes)

        node_map  = {n.id: n for n in nodes}
        orig_arcs = {(e.source, e.target) for e in self._graph.edges}

        for e in self._graph.edges:
            src = node_map.get(e.source)
            tgt = node_map.get(e.target)
            if src is None or tgt is None:
                continue
            flow = step.flow.get((e.source, e.target), 0.0)
            cap  = e.capacity if e.capacity is not None else 0.0
            rad  = 0.25 if (e.target, e.source) in orig_arcs else 0.0
            self._draw_arrow(ax, src, tgt, _EDGE_FLOW, 2.0, rad)
            self._draw_label(ax, src, tgt,
                             f"{_fmt(flow)}/{_fmt(cap)}", rad,
                             highlight=False, box_color=_EDGE_FLOW)

        self._draw_nodes(ax, nodes, set())
        ax.set_title(
            f"Original Network with Flows  \u2014  Max flow = {_fmt(step.total_flow)}",
            color=_TEXT, fontsize=10, pad=10)
        self._mpl.draw_idle()

    # ── primitives ────────────────────────────────────────────────────────────

    def _set_limits(self, ax, nodes: List[Node]):
        xs = [n.position.x for n in nodes]
        ys = [n.position.y for n in nodes]
        m  = 1.3
        xlim = (min(xs) - m, max(xs) + m)
        ylim = (min(ys) - m, max(ys) + m)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)

    def _draw_arrow(self, ax, src: Node, tgt: Node,
                    color: str, lw: float, rad: float) -> None:
        ax.add_patch(FancyArrowPatch(
            (src.position.x, src.position.y),
            (tgt.position.x, tgt.position.y),
            arrowstyle='-|>', mutation_scale=18,
            color=color, linewidth=lw, zorder=1,
            shrinkA=30, shrinkB=30,
            connectionstyle=f'arc3,rad={rad}',
        ))

    def _draw_label(self, ax, src: Node, tgt: Node,
                    text: str, rad: float,
                    highlight: bool = False,
                    box_color: Optional[str] = None) -> None:
        dx = tgt.position.x - src.position.x
        dy = tgt.position.y - src.position.y
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-6:
            return
        mx, my = (src.position.x + tgt.position.x) / 2, \
                 (src.position.y + tgt.position.y) / 2
        px, py = -dy / length, dx / length
        offset = 0.30 if abs(rad) > 0 else 0.18
        sign   = 1 if rad >= 0 else -1
        lx = mx + px * offset * sign
        ly = my + py * offset * sign
        edge_c = box_color or (_EDGE_PATH if highlight else _BORDER)
        txt_c  = _EDGE_PATH if highlight else _TEXT
        ax.text(lx, ly, text,
                ha='center', va='center', fontsize=9, color=txt_c,
                bbox=dict(boxstyle='round,pad=0.3', facecolor=_BOX_FACE,
                          edgecolor=edge_c, alpha=0.92),
                zorder=2)

    def _draw_nodes(self, ax, nodes: List[Node], path_nodes: set) -> None:
        for node in nodes:
            if node.id == self._source:
                color = _NODE_SOURCE
            elif node.id == self._sink:
                color = _NODE_SINK
            elif node.id in path_nodes:
                color = _NODE_PATH
            else:
                color = _NODE_DEFAULT

            on_path    = node.id in path_nodes
            ring_color = '#D8C29C' if on_path else '#524A45'
            ring_width = 3         if on_path else 2

            ax.plot(node.position.x, node.position.y, 'o',
                    markersize=30, color=color,
                    markeredgecolor=ring_color,
                    markeredgewidth=ring_width, zorder=3)

            txt_color = '#131214'
            ax.text(node.position.x, node.position.y, node.label,
                    ha='center', va='center',
                    fontsize=12, weight='bold', color=txt_color, zorder=4)


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return '?'
    return str(int(v)) if v == int(v) else str(round(v, 4))
