"""Core graph data structures."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from utils.types import NodeType, NodeException


@dataclass
class Position:
    """Represents a 2D position."""
    x: float
    y: float
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance to another position."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {"x": self.x, "y": self.y}


@dataclass
class Node:
    """Represents a graph node."""
    id: str
    position: Position
    label: str = ""
    node_type: NodeType = NodeType.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize label if not provided."""
        if not self.label:
            self.label = str(self.id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "label": self.label,
            "node_type": self.node_type.value,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            position=Position(**data["position"]),
            label=data.get("label", data["id"]),
            node_type=NodeType(data.get("node_type", "normal")),
            metadata=data.get("metadata", {})
        )


@dataclass
class Edge:
    """Represents a directed edge between nodes."""
    source: str
    target: str
    weight: float = 1.0
    capacity: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "weight": self.weight,
            "capacity": self.capacity,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Edge':
        """Create from dictionary."""
        return cls(
            source=data["source"],
            target=data["target"],
            weight=data.get("weight", 1.0),
            capacity=data.get("capacity"),
            metadata=data.get("metadata", {})
        )


class Graph:
    """Core graph data structure."""
    
    def __init__(self, graph_id: str = "default", directed: bool = True):
        """Initialize graph."""
        self.graph_id = graph_id
        self.directed = directed
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._adjacency: Dict[str, List[str]] = {}  # node_id -> [target_ids]
    
    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        if node.id in self.nodes:
            raise NodeException(f"Node '{node.id}' already exists")
        self.nodes[node.id] = node
        self._adjacency[node.id] = []
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node and all connected edges."""
        if node_id not in self.nodes:
            raise NodeException(f"Node '{node_id}' not found")
        
        # Remove all edges connected to this node
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
        
        # Update adjacency
        for source_id in self._adjacency:
            self._adjacency[source_id] = [t for t in self._adjacency[source_id] if t != node_id]
        
        del self.nodes[node_id]
        del self._adjacency[node_id]
    
    def add_edge(self, source_id: str, target_id: str, weight: float = 1.0, capacity: Optional[float] = None) -> Edge:
        """Add an edge between two nodes."""
        if source_id not in self.nodes:
            raise NodeException(f"Source node '{source_id}' not found")
        if target_id not in self.nodes:
            raise NodeException(f"Target node '{target_id}' not found")
        
        # Check if edge already exists
        existing = self.get_edge(source_id, target_id)
        if existing:
            existing.weight = weight
            existing.capacity = capacity
            return existing
        
        edge = Edge(source_id, target_id, weight, capacity)
        self.edges.append(edge)
        self._adjacency[source_id].append(target_id)
        
        # For undirected graphs, add reverse edge
        if not self.directed:
            self._adjacency[target_id].append(source_id)
        
        return edge
    
    def remove_edge(self, source_id: str, target_id: str) -> None:
        """Remove an edge."""
        self.edges = [e for e in self.edges if not (e.source == source_id and e.target == target_id)]
        
        if target_id in self._adjacency[source_id]:
            self._adjacency[source_id].remove(target_id)
        
        if not self.directed and source_id in self._adjacency.get(target_id, []):
            self._adjacency[target_id].remove(source_id)
    
    def get_edge(self, source_id: str, target_id: str) -> Optional[Edge]:
        """Get edge between two nodes."""
        for edge in self.edges:
            if edge.source == source_id and edge.target == target_id:
                return edge
        return None
    
    def get_neighbors(self, node_id: str) -> List[str]:
        """Get all neighbor node IDs."""
        return self._adjacency.get(node_id, [])
    
    def has_edge(self, source_id: str, target_id: str) -> bool:
        """Check if edge exists."""
        return self.get_edge(source_id, target_id) is not None
    
    def has_reverse_edge(self, source_id: str, target_id: str) -> bool:
        """Check if reverse edge exists."""
        return self.get_edge(target_id, source_id) is not None
    
    def get_node_count(self) -> int:
        """Get number of nodes."""
        return len(self.nodes)
    
    def get_edge_count(self) -> int:
        """Get number of edges."""
        return len(self.edges)
    
    def clear(self) -> None:
        """Clear the graph."""
        self.nodes.clear()
        self.edges.clear()
        self._adjacency.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export graph as dictionary."""
        return {
            "graph_id": self.graph_id,
            "directed": self.directed,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Graph':
        """Import graph from dictionary."""
        graph = cls(
            graph_id=data.get("graph_id", "default"),
            directed=data.get("directed", True)
        )
        
        # Load nodes
        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            graph.add_node(node)
        
        # Load edges
        for edge_data in data.get("edges", []):
            graph.add_edge(
                edge_data["source"],
                edge_data["target"],
                edge_data.get("weight", 1.0),
                edge_data.get("capacity")
            )
        
        return graph
