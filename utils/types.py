"""Core type definitions and exceptions."""

from enum import Enum


class NodeType(Enum):
    """Node types for different use cases."""
    NORMAL = "normal"
    START = "start"
    END = "end"
    MARKED = "marked"


class GraphType(Enum):
    """Supported graph types."""
    DIRECTED = "directed"
    UNDIRECTED = "undirected"


class AlgorithmType(Enum):
    """Available algorithms."""
    DIJKSTRA = "dijkstra"
    BFS = "bfs"
    DFS = "dfs"
    PRIM = "prim"
    KRUSKAL = "kruskal"
    TOPOLOGICAL_SORT = "topological_sort"


class LayoutType(Enum):
    """Available layout algorithms."""
    FORCE_DIRECTED = "force_directed"
    CIRCULAR = "circular"
    HIERARCHICAL = "hierarchical"
    GRID = "grid"


class GraphException(Exception):
    """Base exception for graph operations."""
    pass


class NodeException(GraphException):
    """Exception for node operations."""
    pass


class EdgeException(GraphException):
    """Exception for edge operations."""
    pass


class AlgorithmException(GraphException):
    """Exception for algorithm operations."""
    pass


class LayoutException(GraphException):
    """Exception for layout operations."""
    pass
