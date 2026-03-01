#!/usr/bin/env python3
"""Graph Visualizer - Interactive directed graph visualization tool."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path

from core import Graph, Node, Position
from services import GraphService, FileService
from ui import ThemedButton, ThemedLabel, ThemedFrame, ThemedEntry
from visualization import StyleConfig, DARK_THEME

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import FancyArrowPatch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class GraphVisualizerApp:
    """Main application window."""
    
    def __init__(self, root):
        """Initialize the app."""
        self.root = root
        self.root.title("Interactive Graph Visualizer")
        self.root.geometry("1400x800")
        self.root.minsize(900, 600)
        self.root.config(bg=DARK_THEME.background)
        
        # Services
        self.graph_service = GraphService()
        
        # State
        self.current_file = None
        self.selected_node = None
        self.edge_source = None
        self.node_counter = 1
        self.dragging_node = None
        # Store edge label positions for click detection: {unique_key: (x, y, edge_object)}
        self.edge_labels = {}
        
        # Build UI
        self._build_ui()
        self._setup_canvas_events()
        self._update_display()
    
    def _build_ui(self):
        """Build the UI layout."""
        # Main container
        main_frame = ThemedFrame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left sidebar
        sidebar = ThemedFrame(main_frame)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # Title
        title_label = ThemedLabel(sidebar, text="Graph Controls", font=("Arial", 12, "bold"))
        title_label.pack(pady=10)
        
        # File operations
        file_frame = ThemedFrame(sidebar)
        file_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ThemedLabel(file_frame, text="File Operations:", font=("Arial", 10, "bold")).pack()
        ThemedButton(file_frame, text="New Graph", command=self._new_graph).pack(fill=tk.X, pady=3)
        ThemedButton(file_frame, text="Open", command=self._open_graph).pack(fill=tk.X, pady=3)
        ThemedButton(file_frame, text="Save", command=self._save_graph).pack(fill=tk.X, pady=3)
        
        # Node operations
        node_frame = ThemedFrame(sidebar)
        node_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ThemedLabel(node_frame, text="Node Operations:", font=("Arial", 10, "bold")).pack()
        
        # Node ID input
        ThemedLabel(node_frame, text="Next Node ID:").pack(pady=(5, 2))
        self.next_node_id = ThemedEntry(node_frame, width=20)
        self.next_node_id.pack(fill=tk.X, pady=2)
        self.next_node_id.insert(0, "1")
        
        ThemedButton(node_frame, text="Delete Selected", command=self._delete_selected).pack(fill=tk.X, pady=3)
        ThemedButton(node_frame, text="Clear All", command=self._clear_graph).pack(fill=tk.X, pady=3)
        
        # Info/Instructions
        info_frame = ThemedFrame(sidebar)
        info_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ThemedLabel(info_frame, text="Instructions:", font=("Arial", 10, "bold")).pack()
        instructions_text = """• Click empty space: Add node

• Left click node: Select

• Click selected node + 
  click another node: 
  Create edge (enter 
  weight & capacity)

• Right click node: Delete

• Esc: Deselect"""
        instr_label = ThemedLabel(info_frame, text=instructions_text, justify=tk.LEFT, font=("Courier", 8))
        instr_label.pack(pady=5, padx=5)
        
        # Status
        status_frame = ThemedFrame(sidebar)
        status_frame.pack(fill=tk.X, padx=5, pady=10)
        self.status_label = ThemedLabel(status_frame, text="Ready", font=("Arial", 9))
        self.status_label.pack(fill=tk.X)
        
        # Right side - canvas
        canvas_frame = ThemedFrame(main_frame)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Canvas
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(12, 7), dpi=100)
            self.figure.patch.set_facecolor(DARK_THEME.background)
            self.ax = self.figure.add_subplot(111)
            self.ax.set_facecolor(DARK_THEME.background)
            
            self.canvas = FigureCanvasTkAgg(self.figure, master=canvas_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            label = ThemedLabel(canvas_frame, text="matplotlib not installed")
            label.pack(fill=tk.BOTH, expand=True)
        
        self.root.bind('<Escape>', lambda e: self._deselect())
    
    def _setup_canvas_events(self):
        """Connect canvas events."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        self.canvas.mpl_connect('button_press_event', self._on_canvas_click)
        self.canvas.mpl_connect('button_release_event', self._on_canvas_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_canvas_motion)
    
    def _on_canvas_click(self, event):
        """Handle canvas click."""
        if event.inaxes != self.ax or event.xdata is None:
            return
        
        x, y = event.xdata, event.ydata
        
        # Check if clicking on an edge label to edit or delete it
        for edge_key, (label_x, label_y, edge) in self.edge_labels.items():
            dist = ((label_x - x) ** 2 + (label_y - y) ** 2) ** 0.5
            # 🔧 FIXED: Smaller radius for precise click (was 0.4 → now 0.2)
            if dist < 0.2:  
                if event.button == 1:  # Left click on edge label - edit
                    self._edit_edge(edge)
                    return
                elif event.button == 3:  # Right click on edge label - delete
                    self.graph_service.graph.remove_edge(edge.source, edge.target)
                    self.status_label.config(text=f"Deleted edge {edge.source} → {edge.target}")
                    self._update_display()
                    return
        
        # Find if clicking on a node
        clicked_node = self._find_node_at(x, y)
        
        if event.button == 1:  # Left click
            if clicked_node:
                # Check if this is the first node for edge creation
                if self.edge_source is None:
                    # Mark as dragging
                    self.dragging_node = clicked_node
                elif self.edge_source == clicked_node:
                    # Deselect same node
                    self.edge_source = None
                    self.selected_node = None
                    self.dragging_node = None
                    self.status_label.config(text="Deselected")
                    self._update_display()
                else:
                    # Second click → create edge
                    target_node = clicked_node
                    self.dragging_node = None
                    self._create_edge(self.edge_source, target_node)
                    self.edge_source = None
                    self.selected_node = None
                    self._update_display()
            else:
                # Click empty space → add node
                self._add_node_at(x, y)
        
        elif event.button == 3:  # Right click → delete node
            if clicked_node:
                self.graph_service.graph.remove_node(clicked_node)
                if self.selected_node == clicked_node:
                    self.selected_node = None
                if self.edge_source == clicked_node:
                    self.edge_source = None
                self.status_label.config(text=f"Deleted node '{clicked_node}'")
                self._update_display()
    
    def _on_canvas_release(self, event):
        """Handle mouse release — detect edge source selection."""
        if self.dragging_node and self.edge_source is None:
            if event.inaxes == self.ax and event.xdata is not None:
                node = next((n for n in self.graph_service.get_all_nodes() 
                           if n.id == self.dragging_node), None)
                if node:
                    dist = ((node.position.x - event.xdata) ** 2 + 
                           (node.position.y - event.ydata) ** 2) ** 0.5
                    if dist < 0.2:  # Minimal movement = select as source
                        self.edge_source = self.dragging_node
                        self.selected_node = self.dragging_node
                        self.status_label.config(text=f"Source: {self.dragging_node}\nClick target node")
                        self._update_display()
        self.dragging_node = None
    
    def _on_canvas_motion(self, event):
        """Drag nodes."""
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
    
    def _find_node_at(self, x, y):
        """Find node within 0.35 distance."""
        for node in self.graph_service.get_all_nodes():
            dist = ((node.position.x - x) ** 2 + (node.position.y - y) ** 2) ** 0.5
            if dist < 0.35:
                return node.id
        return None
    
    def _add_node_at(self, x, y):
        """Add node at (x, y)."""
        # Get node ID from input field
        node_id = self.next_node_id.get().strip()
        if not node_id:
            node_id = str(self.node_counter)
            self.node_counter += 1
        
        # Check if node already exists
        if node_id in {n.id for n in self.graph_service.get_all_nodes()}:
            messagebox.showwarning("Duplicate", f"Node '{node_id}' already exists")
            return
        
        node = Node(id=node_id, position=Position(x, y), label=node_id)
        self.graph_service.graph.add_node(node)
        self.status_label.config(text=f"Added node '{node_id}'")
        
        # Auto-increment for next node
        try:
            next_id = int(node_id) + 1
            self.next_node_id.delete(0, tk.END)
            self.next_node_id.insert(0, str(next_id))
        except ValueError:
            # If node_id is not numeric, just clear the field
            self.next_node_id.delete(0, tk.END)
            self.next_node_id.insert(0, "")
        
        self._update_display()
    
    def _create_edge(self, source_id, target_id):
        """Create edge with weight/capacity."""
        for edge in self.graph_service.get_all_edges():
            if edge.source == source_id and edge.target == target_id:
                messagebox.showwarning("Edge Exists", f"Edge {source_id} → {target_id} already exists")
                return
        
        weight = simpledialog.askinteger(
            "Edge Weight",
            f"Enter weight for edge {source_id} → {target_id}:",
            initialvalue=1,
            minvalue=0
        )
        if weight is None:
            return
        
        capacity = simpledialog.askinteger(
            "Edge Capacity",
            f"Enter capacity for edge {source_id} → {target_id}:",
            initialvalue=10,
            minvalue=0
        )
        if capacity is None:
            return
        
        self.graph_service.graph.add_edge(source_id, target_id, weight=weight, capacity=capacity)
        self.status_label.config(text=f"Created edge {source_id} → {target_id} ({weight}, {capacity})")
        self._update_display()
    
    def _edit_edge(self, edge):
        """Edit edge: show dialog with comma-separated values only."""
        # Ask for new values (no prefixes)
        values = simpledialog.askstring(
            "Edit Edge",
            f"Edit values for edge {edge.source} → {edge.target}:\nFormat: weight, capacity\n(e.g., 3, 10)",
            initialvalue=f"{edge.weight}, {edge.capacity}"
        )
        if not values:
            return
        
        try:
            parts = [p.strip() for p in values.split(',')]
            if len(parts) != 2:
                raise ValueError("Expected exactly two values: weight, capacity")
            weight = int(parts[0])
            capacity = int(parts[1])
            if weight < 0 or capacity < 0:
                raise ValueError("Values must be non-negative")
        except Exception as e:
            messagebox.showerror("Invalid Input", f"Please enter two integers: weight, capacity\nError: {e}")
            return
        
        edge.weight = weight
        edge.capacity = capacity
        self.status_label.config(text=f"Updated edge {edge.source} → {edge.target} ({weight}, {capacity})")
        self._update_display()
    
    def _delete_selected(self):
        """Delete selected node."""
        if not self.selected_node:
            messagebox.showinfo("Info", "No node selected")
            return
        self.graph_service.graph.remove_node(self.selected_node)
        self.selected_node = None
        self.edge_source = None
        self.status_label.config(text="Node deleted")
        self._update_display()
    
    def _deselect(self):
        """Deselect all."""
        self.selected_node = None
        self.edge_source = None
        self.status_label.config(text="Deselected")
        self._update_display()
    
    def _new_graph(self):
        """Clear and reset."""
        if self.graph_service.get_all_nodes():
            if not messagebox.askyesno("Confirm", "Clear current graph?"):
                return
        self.graph_service = GraphService()
        self.selected_node = None
        self.edge_source = None
        self.node_counter = 1
        self.status_label.config(text="New graph created")
        self._update_display()
    
    def _clear_graph(self):
        """Clear everything."""
        if not messagebox.askyesno("Confirm", "Delete all nodes and edges?"):
            return
        self.graph_service.clear()
        self.selected_node = None
        self.edge_source = None
        self.node_counter = 1
        self.status_label.config(text="Graph cleared")
        self._update_display()
    
    def _save_graph(self):
        """Save to JSON."""
        if not self.graph_service.get_all_nodes():
            messagebox.showwarning("Empty", "No nodes to save")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            try:
                FileService.save_graph(self.graph_service, filepath)
                self.current_file = filepath
                self.status_label.config(text=f"Saved: {Path(filepath).name}")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed: {e}")
    
    def _open_graph(self):
        """Load from JSON."""
        filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if filepath:
            try:
                FileService.load_graph(self.graph_service, filepath)
                self.current_file = filepath
                self.selected_node = None
                self.edge_source = None
                self.status_label.config(text=f"Opened: {Path(filepath).name}")
                self._update_display()
            except Exception as e:
                messagebox.showerror("Error", f"Load failed: {e}")
    
    def _update_display(self):
        """Redraw the graph."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        self.ax.clear()
        self.ax.set_facecolor(DARK_THEME.background)
        
        nodes = self.graph_service.get_all_nodes()
        edges = self.graph_service.get_all_edges()
        
        if not nodes:
            self.ax.text(0, 0, "Click to add nodes", ha='center', va='center',
                        fontsize=14, color=DARK_THEME.text_secondary)
            self.ax.set_xlim(-1, 1)
            self.ax.set_ylim(-1, 1)
            self.ax.set_title("Directed Graph", color=DARK_THEME.text)
            self.ax.axis('off')
            self.canvas.draw_idle()
            return
        
        # Compute bounds
        positions = [(n.position.x, n.position.y) for n in nodes]
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        margin = 1.2
        self.ax.set_xlim(min(xs) - margin, max(xs) + margin)
        self.ax.set_ylim(min(ys) - margin, max(ys) + margin)
        
        # Reset edge labels
        self.edge_labels = {}
        
        # Group edges by (src, tgt) for parallel handling
        edge_groups = {}
        for edge in edges:
            key = (edge.source, edge.target)
            edge_groups.setdefault(key, []).append(edge)
        
        # Draw edges and labels
        for edge in edges:
            src_node = next((n for n in nodes if n.id == edge.source), None)
            tgt_node = next((n for n in nodes if n.id == edge.target), None)
            if not src_node or not tgt_node:
                continue
            
            # Vector from src to tgt
            dx = tgt_node.position.x - src_node.position.x
            dy = tgt_node.position.y - src_node.position.y
            length = (dx*dx + dy*dy)**0.5
            if length < 1e-6:
                continue
            
            # Unit perpendicular (CCW)
            perp_x = -dy / length
            perp_y = dx / length
            
            # Group index for parallel edges
            key = (edge.source, edge.target)
            edges_list = edge_groups[key]
            idx = edges_list.index(edge)
            n = len(edges_list)
            
            # 🔧 Label near target node (offset back along edge + perpendicular)
            offset_along = 0.5  # from target toward source
            label_x = tgt_node.position.x - (dx / length) * offset_along + perp_x * 0.12 * (idx - (n-1)/2)
            label_y = tgt_node.position.y - (dy / length) * offset_along + perp_y * 0.12 * (idx - (n-1)/2)
            
            # 🔧 NEW FORMAT: "weight, capacity" (no w:/c:)
            label_text = f"{edge.weight}, {edge.capacity}"
            
            # Draw arrow
            arrow = FancyArrowPatch(
                (src_node.position.x, src_node.position.y),
                (tgt_node.position.x, tgt_node.position.y),
                arrowstyle='-|>',
                mutation_scale=20,
                color=DARK_THEME.text_secondary,
                linewidth=2,
                zorder=1,
                shrinkA=30,
                shrinkB=30,
                connectionstyle=f"arc3,rad={0.1 + 0.03 * (idx - (n-1)/2)}"
            )
            self.ax.add_patch(arrow)
            
            # Draw label with high-contrast background
            self.ax.text(label_x, label_y, label_text,
                        ha='center', va='center',
                        fontsize=9, color=DARK_THEME.text,
                        bbox=dict(
                            boxstyle='round,pad=0.4',
                            facecolor='#2d2d2d',   # clean contrast
                            edgecolor=DARK_THEME.border,
                            alpha=0.95
                        ),
                        zorder=2)
            
            # Store for click detection (unique key)
            label_key = f"{edge.source}->{edge.target}#{idx}"
            self.edge_labels[label_key] = (label_x, label_y, edge)
        
        # Draw nodes
        for node in nodes:
            is_selected = node.id == self.selected_node or node.id == self.edge_source
            color = DARK_THEME.accent if is_selected else DARK_THEME.primary
            edge_color = DARK_THEME.accent if is_selected else DARK_THEME.border
            edge_width = 3 if is_selected else 2
            
            self.ax.plot(node.position.x, node.position.y, 'o',
                        markersize=30,
                        color=color,
                        markeredgecolor=edge_color,
                        markeredgewidth=edge_width,
                        zorder=3)
            
            self.ax.text(node.position.x, node.position.y, node.label,
                        ha='center', va='center',
                        fontsize=12, weight='bold',
                        color=DARK_THEME.text, zorder=4)
        
        self.ax.set_title("Directed Graph", color=DARK_THEME.text, fontsize=12)
        self.ax.axis('off')
        self.canvas.draw_idle()


def main():
    """Entry point."""
    root = tk.Tk()
    app = GraphVisualizerApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()