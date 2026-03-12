"""Generic Max Flow algorithm (Ford-Fulkerson generic version).

Works on the residual graph. Finds augmenting paths via BFS (Edmonds-Karp
variant for determinism). Records every sub-step so the visualizer can
replay the execution interactively.

Terminology (from the pseudocode):
    c(x,y)  -- capacity of arc (x,y) in original network G
    f(x,y)  -- flow on arc (x,y)
    r(x,y)  -- residual capacity: c(x,y) - f(x,y) + f(y,x) [simplified as
               c(x,y) - f(x,y) for forward arcs, f(x,y) for backward arcs]
    G~(f)   -- residual network
    DMF     -- augmenting path (Drum de Marire a Fluxului)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

ArcKey = Tuple[str, str]


@dataclass
class FlowStep:
    """Snapshot of algorithm state at one point in execution."""
    index: int
    phase: str                              # 'init' | 'found_path' | 'augmented' | 'final'
    description: str
    residual: Dict[ArcKey, float]           # r(x,y) for every arc with r > 0
    path: Optional[List[str]]              # node sequence of current DMF
    path_residual: Optional[float]         # r(D~) = bottleneck
    flow: Dict[ArcKey, float]              # f(x,y) on original arcs
    total_flow: float


# ---------------------------------------------------------------------------
# Main algorithm
# ---------------------------------------------------------------------------

def run_generic_max_flow(
    node_ids: List[str],
    edges: List[Tuple[str, str, float]],    # (source, target, capacity)
    source: str,
    sink: str,
) -> List[FlowStep]:
    """Run the Generic Max Flow algorithm and return every recorded step.

    Args:
        node_ids: All node IDs in the network.
        edges:    List of (u, v, capacity) tuples for the original arcs.
        source:   Source node ID (s).
        sink:     Sink node ID (t).

    Returns:
        Ordered list of FlowStep objects from initial state to termination.
    """
    # ---- Build original capacity table ---------------------------------
    cap: Dict[ArcKey, float] = {}
    for u, v, c in edges:
        cap[(u, v)] = cap.get((u, v), 0.0) + max(0.0, c)

    # ---- Initial residual graph = forward arcs at full capacity --------
    r: Dict[ArcKey, float] = {}
    for (u, v), c in cap.items():
        r[(u, v)] = r.get((u, v), 0.0) + c
        if (v, u) not in r:
            r[(v, u)] = 0.0

    # ---- Helpers -------------------------------------------------------
    def active_residual() -> Dict[ArcKey, float]:
        return {arc: val for arc, val in r.items() if val > 0}

    def compute_flow() -> Dict[ArcKey, float]:
        """f(x,y) = max(0, c(x,y) - r(x,y))"""
        return {arc: max(0.0, cap[arc] - r.get(arc, 0.0)) for arc in cap}

    def current_total_flow() -> float:
        f = compute_flow()
        return sum(f[(u, v)] for (u, v) in cap if u == source)

    steps: List[FlowStep] = []

    # ---- Step 0: initial state -----------------------------------------
    steps.append(FlowStep(
        index=0,
        phase='init',
        description=(
            "Initial state (Step 0)\n"
            "f\u2080 = 0 on all arcs.\n"
            "The residual network G\u0303(f) equals the original network G\n"
            "with r(x,y) = c(x,y) for every arc (x,y)."
        ),
        residual=active_residual(),
        path=None,
        path_residual=None,
        flow=compute_flow(),
        total_flow=0.0,
    ))

    iteration = 0

    # ---- Main loop -----------------------------------------------------
    while True:
        path = _bfs(r, source, sink)
        if path is None:
            break

        iteration += 1

        # Bottleneck
        path_r = min(r[(path[i], path[i + 1])] for i in range(len(path) - 1))

        path_str = " \u2192 ".join(path)
        caps_str = ", ".join(
            str(_fmt(r[(path[i], path[i + 1])]))
            for i in range(len(path) - 1)
        )

        # Step A: path found, before augmentation
        steps.append(FlowStep(
            index=len(steps),
            phase='found_path',
            description=(
                f"Iteration {iteration}a \u2014 Augmenting path found\n"
                f"D\u0303 = ({path_str})\n\n"
                f"r(D\u0303) = min{{{caps_str}}}\n"
                f"      = {_fmt(path_r)}\n\n"
                "The path will be augmented by this amount."
            ),
            residual=active_residual(),
            path=list(path),
            path_residual=path_r,
            flow=compute_flow(),
            total_flow=current_total_flow(),
        ))

        # Augment along path
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            r[(u, v)] -= path_r
            r[(v, u)] = r.get((v, u), 0.0) + path_r

        new_total = current_total_flow()

        # Step B: after augmentation
        steps.append(FlowStep(
            index=len(steps),
            phase='augmented',
            description=(
                f"Iteration {iteration}b \u2014 After augmentation\n"
                f"Sent {_fmt(path_r)} units along\n"
                f"D\u0303 = ({path_str})\n\n"
                "Residual network updated:\n"
                + _residual_diff_text(path, path_r)
                + f"\n\nTotal flow so far: {_fmt(new_total)}"
            ),
            residual=active_residual(),
            path=list(path),
            path_residual=path_r,
            flow=compute_flow(),
            total_flow=new_total,
        ))

    # ---- Final step ----------------------------------------------------
    final_flow = compute_flow()
    tv = current_total_flow()

    flow_lines = "\n".join(
        f"  f({u},{v}) = max(0, {_fmt(cap[(u,v)])} \u2212 {_fmt(r.get((u,v),0))}) "
        f"= {_fmt(final_flow[(u,v)])}"
        for (u, v) in sorted(cap.keys())
    )

    steps.append(FlowStep(
        index=len(steps),
        phase='final',
        description=(
            f"Final state \u2014 no more augmenting paths\n"
            f"Maximum flow value = {_fmt(tv)}\n\n"
            "Arc flows  f(x,y) = max(0, c(x,y) \u2212 r(x,y)):\n"
            + flow_lines
        ),
        residual=active_residual(),
        path=None,
        path_residual=None,
        flow=final_flow,
        total_flow=tv,
    ))

    return steps


# ---------------------------------------------------------------------------
# BFS for shortest augmenting path
# ---------------------------------------------------------------------------

def _bfs(r: Dict[ArcKey, float], source: str, sink: str) -> Optional[List[str]]:
    """Return a shortest s-t path in the residual graph, or None."""
    parent: Dict[str, Optional[str]] = {source: None}
    queue: deque[str] = deque([source])

    while queue:
        u = queue.popleft()
        if u == sink:
            path: List[str] = []
            node: Optional[str] = sink
            while node is not None:
                path.append(node)
                node = parent[node]
            return list(reversed(path))

        for (a, b), res in r.items():
            if a == u and b not in parent and res > 0:
                parent[b] = u
                queue.append(b)

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(v: float) -> str:
    """Format a number: drop .0 suffix when integer-valued."""
    return str(int(v)) if v == int(v) else str(round(v, 4))


def _residual_diff_text(path: List[str], delta: float) -> str:
    lines = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        lines.append(f"  r({u},{v}) -= {_fmt(delta)}")
        lines.append(f"  r({v},{u}) += {_fmt(delta)}")
    return "\n".join(lines)
