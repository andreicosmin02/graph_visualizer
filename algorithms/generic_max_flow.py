"""Generic Max Flow algorithm (Ford-Fulkerson generic version).

Works on the residual graph. Finds augmenting paths via BFS with randomized
neighbour ordering so different runs may explore different paths (while still
reaching the same maximum flow value).

Terminology (from the pseudocode):
    c(x,y)  -- capacity of arc (x,y) in original network G
    f(x,y)  -- flow on arc (x,y)
    r(x,y)  -- residual capacity: c(x,y) - f(x,y) + f(y,x) [simplified as
               c(x,y) - f(x,y) for forward arcs, f(x,y) for backward arcs]
    G~(f)   -- residual network
    DMF     -- augmenting path (Drum de Marire a Fluxului)
"""

from __future__ import annotations

import random
from dataclasses import dataclass


ArcKey = tuple[str, str]


@dataclass
class FlowStep:
    """Snapshot of algorithm state at one point in execution."""
    index: int
    phase: str                              # 'init' | 'found_path' | 'augmented' | 'final'
    description: str
    residual: dict[ArcKey, float]           # r(x,y) for every arc with r > 0
    path: list[str] | None                  # node sequence of current DMF
    path_residual: float | None             # r(D~) = bottleneck
    flow: dict[ArcKey, float]               # f(x,y) on original arcs
    total_flow: float


def run_generic_max_flow(
    node_ids: list[str],
    edges: list[tuple[str, str, float]],    # (source, target, capacity)
    source: str,
    sink: str,
) -> list[FlowStep]:
    """Run the Generic Max Flow algorithm and return every recorded step."""
    # ---- Build original capacity table ---------------------------------
    cap: dict[ArcKey, float] = {}
    for u, v, c in edges:
        cap[(u, v)] = cap.get((u, v), 0.0) + max(0.0, c)

    # ---- Initial residual graph = forward arcs at full capacity --------
    r: dict[ArcKey, float] = {}
    for (u, v), c in cap.items():
        r[(u, v)] = r.get((u, v), 0.0) + c
        if (v, u) not in r:
            r[(v, u)] = 0.0

    # ---- Helpers -------------------------------------------------------
    def active_residual() -> dict[ArcKey, float]:
        return {arc: val for arc, val in r.items() if val > 0}

    def compute_flow() -> dict[ArcKey, float]:
        """f(x,y) = max(0, c(x,y) - r(x,y))"""
        return {arc: max(0.0, cap[arc] - r.get(arc, 0.0)) for arc in cap}

    def current_total_flow() -> float:
        f = compute_flow()
        return sum(f[(u, v)] for (u, v) in cap if u == source)

    steps: list[FlowStep] = []

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
        path = _find_path(r, source, sink)
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


def _find_path(r: dict[ArcKey, float], source: str, sink: str) -> list[str] | None:
    """Find a random s-t path in the residual graph.

    Uses random neighbor selection with backtracking,
    just 'identify a DMF' as the generic pseudocode requires.

    :param r: Residual capacity dictionary mapping (u, v) -> residual value.
    :param source: Source node ID (s).
    :param sink: Sink node ID (t).
    :return: List of node IDs forming the path, or None if no path exists.
    """
    visited: set[str] = {source}
    path: list[str] = [source]

    while path:
        u = path[-1]
        if u == sink:
            return list(path)

        neighbours = [b for (a, b), res in r.items()
                      if a == u and b not in visited and res > 0]
        if neighbours:
            b = random.choice(neighbours)
            visited.add(b)
            path.append(b)
        else:
            path.pop()

    return None


def _fmt(v: float) -> str:
    """Format a number: drop .0 suffix when integer-valued."""
    return str(int(v)) if v == int(v) else str(round(v, 4))


def _residual_diff_text(path: list[str], delta: float) -> str:
    lines = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        lines.append(f"  r({u},{v}) -= {_fmt(delta)}")
        lines.append(f"  r({v},{u}) += {_fmt(delta)}")
    return "\n".join(lines)
