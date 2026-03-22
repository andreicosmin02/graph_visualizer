#!/usr/bin/env python3
"""Graph Visualizer - Interactive directed graph visualization tool."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path

from core import Node, Position
from services import GraphService, FileService
from ui import ThemedFrame, ThemedEntry
from ui.components import Card, SectionHeader, Separator, DimLabel, HoverButton
from algorithms.generic_max_flow import run_generic_max_flow
from algorithms.ford_fulkerson import run_ford_fulkerson
from algorithms.edmonds_karp import run_edmonds_karp
from visualization.flow_visualizer import MaxFlowVisualizer

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import FancyArrowPatch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ── Palette ───────────────────────────────────────────────────────────────────
_BG       = '#131214'
_CARD_BG  = '#2E2A33'
_ACCENT   = '#F1C232'
_TEXT     = '#C5AD89'
_TEXT_DIM = '#82715B'
_BORDER   = '#524A45'


class GraphVisualizerApp:
    """Main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Graph Visualizer")
        self.root.geometry("1440x860")
        self.root.minsize(960, 620)
        self.root.config(bg=_BG)

        self.graph_service = GraphService()

        self.current_file: str | None  = None
        self.selected_node: str | None = None
        self.edge_source: str | None   = None
        self.node_counter = 1
        self.dragging_node: str | None = None
        self.edge_labels: dict         = {}

        self._build_ui()
        self._setup_canvas_events()
        self._update_display()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Top header bar
        header = tk.Frame(self.root, bg=_CARD_BG, height=46)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(header, text="Graph Visualizer",
                 bg=_CARD_BG, fg=_TEXT,
                 font=('Segoe UI', 13, 'bold'), padx=16).pack(side=tk.LEFT, pady=10)

        stats_frame = tk.Frame(header, bg=_CARD_BG)
        stats_frame.pack(side=tk.RIGHT, padx=16)
        self._nodes_stat = tk.Label(stats_frame, text="0 nodes",
                                    bg=_CARD_BG, fg=_TEXT_DIM, font=('Segoe UI', 9))
        self._nodes_stat.pack(side=tk.LEFT, padx=(0, 14))
        self._edges_stat = tk.Label(stats_frame, text="0 edges",
                                    bg=_CARD_BG, fg=_TEXT_DIM, font=('Segoe UI', 9))
        self._edges_stat.pack(side=tk.LEFT)

        Separator(self.root, color=_BORDER).pack(fill=tk.X)

        # Body
        body = ThemedFrame(self.root)
        body.pack(fill=tk.BOTH, expand=True)

        sidebar = ThemedFrame(body, width=210)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        Separator(body, color=_BORDER).pack(side=tk.LEFT, fill=tk.Y)

        canvas_frame = ThemedFrame(body)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar(sidebar)

        # Bottom status bar
        Separator(self.root, color=_BORDER).pack(fill=tk.X, side=tk.BOTTOM)
        status_bar = tk.Frame(self.root, bg=_CARD_BG, height=28)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        self.status_label = tk.Label(status_bar, text="Ready",
                                     bg=_CARD_BG, fg=_TEXT_DIM,
                                     font=('Segoe UI', 9), padx=12, anchor=tk.W)
        self.status_label.pack(fill=tk.BOTH, expand=True)

        # Matplotlib canvas
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(12, 7), dpi=100)
            self.figure.patch.set_facecolor(_BG)
            self.ax = self.figure.add_subplot(111)
            self.ax.set_facecolor(_BG)
            self.canvas = FigureCanvasTkAgg(self.figure, master=canvas_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            tk.Label(canvas_frame,
                     text="matplotlib not installed.\nRun: pip install matplotlib",
                     bg=_BG, fg=_TEXT_DIM, font=('Segoe UI', 12)).pack(expand=True)

        self.root.bind('<Escape>', lambda _e: self._deselect())

    def _build_sidebar(self, sidebar: ThemedFrame) -> None:
        pad = {'fill': tk.X, 'padx': 8, 'pady': (8, 0)}

        # File
        fc = Card(sidebar)
        fc.pack(**pad)
        SectionHeader(fc, text="File").pack(fill=tk.X)
        self._sdbtn(fc, "New Graph", self._new_graph)
        self._sdbtn(fc, "Open",      self._open_graph)
        self._sdbtn(fc, "Save",      self._save_graph)

        # Nodes
        nc = Card(sidebar)
        nc.pack(**pad)
        SectionHeader(nc, text="Nodes").pack(fill=tk.X)
        DimLabel(nc, text="Next Node ID:", bg=_CARD_BG).pack(
            anchor=tk.W, padx=10, pady=(2, 2))
        wrap = tk.Frame(nc, bg=_BORDER, padx=1, pady=1)
        wrap.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.next_node_id = ThemedEntry(wrap)
        self.next_node_id.pack(fill=tk.X, padx=2, pady=2)
        self.next_node_id.insert(0, "1")
        self._sdbtn(nc, "Delete Selected", self._delete_selected,
                    bg='#802525', hover_bg='#a02828')
        self._sdbtn(nc, "Clear All",       self._clear_graph,
                    bg='#802525', hover_bg='#a02828')

        # Algorithms
        ac = Card(sidebar)
        ac.pack(**pad)
        SectionHeader(ac, text="Algorithms").pack(fill=tk.X)
        self._sdbtn(ac, "Run Generic Max Flow", self._run_max_flow,
                    bg='#3A343F', hover_bg='#524A45', fg='#9BCB2F')
        self._sdbtn(ac, "Run Ford-Fulkerson", self._run_ford_fulkerson,
                    bg='#3A343F', hover_bg='#524A45', fg='#9BCB2F')
        self._sdbtn(ac, "Run Edmonds-Karp", self._run_edmonds_karp,
                    bg='#3A343F', hover_bg='#524A45', fg='#9BCB2F')

        # Instructions
        ic = Card(sidebar)
        ic.pack(fill=tk.X, padx=8, pady=(8, 0))
        SectionHeader(ic, text="How to use").pack(fill=tk.X)
        tk.Label(ic,
                 text=("Click canvas  — add node\n"
                       "Click node  — select\n"
                       "Select + click  — edge\n"
                       "Right-click node  — delete\n"
                       "Click label  — edit edge\n"
                       "Right-click label  — del edge\n"
                       "Drag  — move node\n"
                       "Esc  — deselect"),
                 bg=_CARD_BG, fg=_TEXT_DIM,
                 font=('Courier New', 8), justify=tk.LEFT,
                 padx=10, pady=6).pack(fill=tk.X)

    @staticmethod
    def _sdbtn(parent, text: str, command,
               bg: str = '#3A343F', hover_bg: str = '#524A45', **kwargs) -> HoverButton:
        btn = HoverButton(parent, text=text, command=command,
                          bg=bg, hover_bg=hover_bg, **kwargs)
        btn.pack(fill=tk.X, padx=10, pady=(0, 4))
        return btn

    # ── Canvas events ─────────────────────────────────────────────────────────

    def _setup_canvas_events(self) -> None:
        if not MATPLOTLIB_AVAILABLE:
            return
        self.canvas.mpl_connect('button_press_event',   self._on_canvas_click)
        self.canvas.mpl_connect('button_release_event', self._on_canvas_release)
        self.canvas.mpl_connect('motion_notify_event',  self._on_canvas_motion)

    def _on_canvas_click(self, event) -> None:
        if event.inaxes != self.ax or event.xdata is None:
            return

        x, y = event.xdata, event.ydata

        for _key, (lx, ly, edge) in self.edge_labels.items():
            if ((lx - x) ** 2 + (ly - y) ** 2) ** 0.5 < 0.2:
                if event.button == 1:
                    self._edit_edge(edge)
                elif event.button == 3:
                    self.graph_service.graph.remove_edge(edge.source, edge.target)
                    self._set_status(f"Deleted edge {edge.source} \u2192 {edge.target}")
                    self._update_display()
                return

        clicked = self._find_node_at(x, y)

        if event.button == 1:
            if clicked:
                if self.edge_source is None:
                    self.dragging_node = clicked
                elif self.edge_source == clicked:
                    self.edge_source = self.selected_node = self.dragging_node = None
                    self._set_status("Deselected")
                    self._update_display()
                else:
                    self._create_edge(self.edge_source, clicked)
                    self.edge_source = self.selected_node = self.dragging_node = None
                    self._update_display()
            else:
                self._add_node_at(x, y)

        elif event.button == 3:
            if clicked:
                self.graph_service.graph.remove_node(clicked)
                if self.selected_node == clicked:
                    self.selected_node = None
                if self.edge_source == clicked:
                    self.edge_source = None
                self._set_status(f"Deleted node '{clicked}'")
                self._update_display()

    def _on_canvas_release(self, event) -> None:
        if self.dragging_node and self.edge_source is None:
            if event.inaxes == self.ax and event.xdata is not None:
                node = next((n for n in self.graph_service.get_all_nodes()
                             if n.id == self.dragging_node), None)
                if node:
                    d = ((node.position.x - event.xdata) ** 2 +
                         (node.position.y - event.ydata) ** 2) ** 0.5
                    if d < 0.2:
                        self.edge_source = self.selected_node = self.dragging_node
                        self._set_status(
                            f"Source: {self.dragging_node}  —  click target node")
                        self._update_display()
        self.dragging_node = None

    def _on_canvas_motion(self, event) -> None:
        if not self.dragging_node or event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        for node in self.graph_service.get_all_nodes():
            if node.id == self.dragging_node:
                node.position.x = event.xdata
                node.position.y = event.ydata
                self._update_display()
                break

    def _find_node_at(self, x: float, y: float) -> str | None:
        for node in self.graph_service.get_all_nodes():
            if ((node.position.x - x) ** 2 + (node.position.y - y) ** 2) ** 0.5 < 0.35:
                return node.id
        return None

    # ── Graph editing ─────────────────────────────────────────────────────────

    def _add_node_at(self, x: float, y: float) -> None:
        node_id = self.next_node_id.get().strip()
        if not node_id:
            node_id = str(self.node_counter)
            self.node_counter += 1

        if node_id in {n.id for n in self.graph_service.get_all_nodes()}:
            messagebox.showwarning("Duplicate", f"Node '{node_id}' already exists")
            return

        self.graph_service.graph.add_node(
            Node(id=node_id, position=Position(x, y), label=node_id))
        self._set_status(f"Added node '{node_id}'")

        try:
            self.next_node_id.delete(0, tk.END)
            self.next_node_id.insert(0, str(int(node_id) + 1))
        except ValueError:
            self.next_node_id.delete(0, tk.END)

        self._update_display()

    def _create_edge(self, source_id: str, target_id: str) -> None:
        for edge in self.graph_service.get_all_edges():
            if edge.source == source_id and edge.target == target_id:
                messagebox.showwarning("Edge exists",
                                       f"Edge {source_id} \u2192 {target_id} already exists")
                return

        flux = simpledialog.askinteger(
            "Edge Flux", f"Flux for {source_id} \u2192 {target_id}:",
            initialvalue=0, minvalue=0)
        if flux is None:
            return

        capacity = simpledialog.askinteger(
            "Edge Capacity", f"Capacity for {source_id} \u2192 {target_id}:",
            initialvalue=10, minvalue=0)
        if capacity is None:
            return

        self.graph_service.graph.add_edge(source_id, target_id,
                                          flux=flux, capacity=capacity)
        self._set_status(f"Edge {source_id} \u2192 {target_id}  f={flux}  c={capacity}")
        self._update_display()

    def _edit_edge(self, edge) -> None:
        values = simpledialog.askstring(
            "Edit Edge",
            f"Edge {edge.source} \u2192 {edge.target}\n"
            "Format: flux, capacity  (e.g. 3, 10)",
            initialvalue=f"{edge.flux}, {edge.capacity}",
        )
        if not values:
            return
        try:
            parts = [p.strip() for p in values.split(',')]
            if len(parts) != 2:
                raise ValueError
            w, c = int(parts[0]), int(parts[1])
            if w < 0 or c < 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Invalid input",
                                 "Enter two non-negative integers: flux, capacity")
            return

        edge.flux, edge.capacity = w, c
        self._set_status(
            f"Updated {edge.source} \u2192 {edge.target}  w={w}  c={c}")
        self._update_display()

    def _delete_selected(self) -> None:
        if not self.selected_node:
            messagebox.showinfo("Info", "No node selected")
            return
        self.graph_service.graph.remove_node(self.selected_node)
        self.selected_node = self.edge_source = None
        self._set_status("Node deleted")
        self._update_display()

    def _deselect(self) -> None:
        self.selected_node = self.edge_source = None
        self._set_status("Deselected")
        self._update_display()

    # ── File operations ───────────────────────────────────────────────────────

    def _new_graph(self) -> None:
        if self.graph_service.get_all_nodes():
            if not messagebox.askyesno("Confirm", "Discard current graph?"):
                return
        self.graph_service = GraphService()
        self.selected_node = self.edge_source = None
        self.node_counter = 1
        self.current_file = None
        self._set_status("New graph")
        self._update_display()

    def _clear_graph(self) -> None:
        if not messagebox.askyesno("Confirm", "Delete all nodes and edges?"):
            return
        self.graph_service.clear()
        self.selected_node = self.edge_source = None
        self.node_counter = 1
        self._set_status("Graph cleared")
        self._update_display()

    def _save_graph(self) -> None:
        if not self.graph_service.get_all_nodes():
            messagebox.showwarning("Empty", "Nothing to save")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if filepath:
            try:
                FileService.save_graph(self.graph_service, filepath)
                self.current_file = filepath
                self._set_status(f"Saved  {Path(filepath).name}")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed: {e}")

    def _open_graph(self) -> None:
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if filepath:
            try:
                FileService.load_graph(self.graph_service, filepath)
                self.current_file = filepath
                self.selected_node = self.edge_source = None
                self._set_status(f"Opened  {Path(filepath).name}")
                self._update_display()
            except Exception as e:
                messagebox.showerror("Error", f"Load failed: {e}")

    # ── Algorithms ────────────────────────────────────────────────────────────

    def _run_max_flow(self) -> None:
        self._run_algorithm(run_generic_max_flow, "Generic Max Flow")

    def _run_ford_fulkerson(self) -> None:
        self._run_algorithm(run_ford_fulkerson, "Ford-Fulkerson (FFE)")

    def _run_edmonds_karp(self) -> None:
        self._run_algorithm(run_edmonds_karp, "Edmonds-Karp")

    def _run_algorithm(self, algorithm_fn, title: str) -> None:
        nodes = self.graph_service.get_all_nodes()
        if len(nodes) < 2:
            messagebox.showwarning("Not enough nodes", "Add at least 2 nodes first.")
            return

        node_ids = sorted(n.id for n in nodes)

        source = simpledialog.askstring(
            "Source node",
            f"Enter source node (s):\nAvailable: {', '.join(node_ids)}")
        if source is None:
            return
        source = source.strip()
        if source not in {n.id for n in nodes}:
            messagebox.showerror("Invalid node", f"Node '{source}' not found.")
            return

        sink = simpledialog.askstring(
            "Sink node",
            f"Enter sink node (t):\nAvailable: {', '.join(node_ids)}")
        if sink is None:
            return
        sink = sink.strip()
        if sink not in {n.id for n in nodes}:
            messagebox.showerror("Invalid node", f"Node '{sink}' not found.")
            return
        if sink == source:
            messagebox.showerror("Invalid input", "Source and sink must be different.")
            return

        zero_cap = [e for e in self.graph_service.get_all_edges()
                    if not e.capacity or e.capacity <= 0]
        if zero_cap:
            names = ", ".join(f"{e.source}\u2192{e.target}" for e in zero_cap)
            if not messagebox.askyesno(
                "Zero capacities",
                f"Some edges have zero capacity:\n{names}\n\nContinue?"):
                return

        MaxFlowVisualizer(self.root, self.graph_service.graph, source, sink,
                          algorithm_fn=algorithm_fn, title=title)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _set_status(self, text: str) -> None:
        self.status_label.config(text=text)

    def _update_display(self) -> None:
        n = len(self.graph_service.get_all_nodes())
        e = len(self.graph_service.get_all_edges())
        self._nodes_stat.config(text=f"{n} node{'s' if n != 1 else ''}")
        self._edges_stat.config(text=f"{e} edge{'s' if e != 1 else ''}")

        if not MATPLOTLIB_AVAILABLE:
            return

        self.ax.clear()
        self.ax.set_facecolor(_BG)

        nodes = self.graph_service.get_all_nodes()
        edges = self.graph_service.get_all_edges()

        if not nodes:
            self.ax.text(0, 0, "Click anywhere to add a node",
                         ha='center', va='center',
                         fontsize=13, color=_TEXT_DIM, style='italic')
            self.ax.set_xlim(-1, 1)
            self.ax.set_ylim(-1, 1)
            self.ax.axis('off')
            self.canvas.draw_idle()
            return

        xs = [nd.position.x for nd in nodes]
        ys = [nd.position.y for nd in nodes]
        margin = 1.2
        xlim = (min(xs) - margin, max(xs) + margin)
        ylim = (min(ys) - margin, max(ys) + margin)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)

        self.edge_labels = {}
        edge_groups: dict = {}
        for edge in edges:
            edge_groups.setdefault((edge.source, edge.target), []).append(edge)

        for edge in edges:
            src = next((nd for nd in nodes if nd.id == edge.source), None)
            tgt = next((nd for nd in nodes if nd.id == edge.target), None)
            if not src or not tgt:
                continue

            dx = tgt.position.x - src.position.x
            dy = tgt.position.y - src.position.y
            length = (dx * dx + dy * dy) ** 0.5
            if length < 1e-6:
                continue

            perp_x = -dy / length
            perp_y =  dx / length

            key   = (edge.source, edge.target)
            idx   = edge_groups[key].index(edge)
            n_par = len(edge_groups[key])
            rad   = 0.1 + 0.03 * (idx - (n_par - 1) / 2)

            label_x = (tgt.position.x - (dx / length) * 0.5
                       + perp_x * 0.12 * (idx - (n_par - 1) / 2))
            label_y = (tgt.position.y - (dy / length) * 0.5
                       + perp_y * 0.12 * (idx - (n_par - 1) / 2))

            self.ax.add_patch(FancyArrowPatch(
                (src.position.x, src.position.y),
                (tgt.position.x, tgt.position.y),
                arrowstyle='-|>', mutation_scale=20,
                color='#F1C232', linewidth=2, zorder=1,
                shrinkA=30, shrinkB=30,
                connectionstyle=f"arc3,rad={rad}",
            ))

            self.ax.text(label_x, label_y, f"{edge.flux}/{edge.capacity}",
                         ha='center', va='center', fontsize=9, color='#C5AD89',
                         bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1516',
                                   edgecolor='#524A45', alpha=0.95),
                         zorder=2)

            self.edge_labels[f"{edge.source}->{edge.target}#{idx}"] = (
                label_x, label_y, edge)

        for node in nodes:
            is_sel     = node.id in (self.selected_node, self.edge_source)
            node_color = '#F1C232' if is_sel else '#C5AD89'
            ring_color = '#D8C29C' if is_sel else '#82715B'

            self.ax.plot(node.position.x, node.position.y, 'o',
                         markersize=30, color=node_color,
                         markeredgecolor=ring_color,
                         markeredgewidth=3 if is_sel else 2, zorder=3)
            self.ax.text(node.position.x, node.position.y, node.label,
                         ha='center', va='center',
                         fontsize=12, weight='bold', color='#131214', zorder=4)

        fname = Path(self.current_file).name if self.current_file else "unsaved"
        self.ax.set_title(f"Directed Graph  —  {fname}",
                          color=_TEXT, fontsize=11, pad=10)
        self.ax.axis('off')
        self.canvas.draw_idle()


def main() -> None:
    root = tk.Tk()
    GraphVisualizerApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
