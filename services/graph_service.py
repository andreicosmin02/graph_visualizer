"""Business logic services."""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from core.graph import Graph, Node, Edge, Position
from utils.types import GraphException


class GraphService:
    """Service for graph operations."""
    
    def __init__(self):
        self.graph = Graph()
        self._next_node_id = 1
    
    def create_graph(self, graph_id: str = "default", directed: bool = True) -> None:
        """Create new graph."""
        self.graph = Graph(graph_id, directed)
        self._next_node_id = 1
    
    def add_node(self, x: float, y: float, label: str = "") -> Node:
        """Add node at position."""
        node_id = str(self._next_node_id)
        self._next_node_id += 1
        
        node = Node(
            id=node_id,
            position=Position(x, y),
            label=label or node_id
        )
        self.graph.add_node(node)
        return node
    
    def remove_node(self, node_id: str) -> None:
        """Remove node."""
        self.graph.remove_node(node_id)
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        return self.graph.nodes.get(node_id)
    
    def add_edge(self, source_id: str, target_id: str, weight: float = 1.0, capacity: Optional[float] = None) -> Edge:
        """Add edge between nodes."""
        return self.graph.add_edge(source_id, target_id, weight, capacity)
    
    def remove_edge(self, source_id: str, target_id: str) -> None:
        """Remove edge."""
        self.graph.remove_edge(source_id, target_id)
    
    def get_edge(self, source_id: str, target_id: str) -> Optional[Edge]:
        """Get edge."""
        return self.graph.get_edge(source_id, target_id)
    
    def get_all_nodes(self) -> List[Node]:
        """Get all nodes."""
        return list(self.graph.nodes.values())
    
    def get_all_edges(self) -> List[Edge]:
        """Get all edges."""
        return self.graph.edges
    
    def get_node_at_position(self, x: float, y: float, radius: float = 30.0) -> Optional[Node]:
        """Get node near position."""
        for node in self.get_all_nodes():
            distance = node.position.distance_to(Position(x, y))
            if distance <= radius:
                return node
        return None
    
    def get_next_node_id(self) -> str:
        """Get next node ID."""
        return str(self._next_node_id)
    
    def clear(self) -> None:
        """Clear graph."""
        self.graph.clear()
        self._next_node_id = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Export graph."""
        return self.graph.to_dict()
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Import graph."""
        self.graph = Graph.from_dict(data)
        # Update next_node_id
        if self.graph.nodes:
            max_id = max(int(node_id) for node_id in self.graph.nodes.keys() if node_id.isdigit())
            self._next_node_id = max_id + 1
        else:
            self._next_node_id = 1


class FileService:
    """Service for file operations."""
    
    @staticmethod
    def save_graph(graph_service: GraphService, filepath: str) -> None:
        """Save graph to file."""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            data = graph_service.to_dict()
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise GraphException(f"Failed to save graph: {e}")
    
    @staticmethod
    def load_graph(graph_service: GraphService, filepath: str) -> None:
        """Load graph from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            graph_service.from_dict(data)
        except FileNotFoundError:
            raise GraphException(f"File not found: {filepath}")
        except json.JSONDecodeError:
            raise GraphException(f"Invalid graph file: {filepath}")
        except Exception as e:
            raise GraphException(f"Failed to load graph: {e}")
    
    @staticmethod
    def file_exists(filepath: str) -> bool:
        """Check if file exists."""
        return Path(filepath).exists()
