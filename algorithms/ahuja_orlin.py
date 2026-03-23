"""Ahuja-Orlin Maximum Capacity Scaling algorithm.

Scales the residual threshold r = 2^⌊log₂ c_max⌋ down to 1, only considering
arcs with residual capacity ≥ r when searching for augmenting paths.
At each scaling phase, finds all augmenting paths using arcs ≥ r, then halves r.

Pseudocode reference:
    (1)  f := 0;
    (2)  r := 2^⌊log₂ c_max⌋;
    (3)  WHILE r ≥ 1 DO
    (4)  BEGIN
    (5)    se determina un DMF D̃ in G̃(f, r);
    (6)    WHILE D̃ ≠ ∅ DO
    (7)    BEGIN
    (8)      MĂRIRE;
    (9)      se determina un DMF D̃ in G̃(f, r);
    (10)   END;
    (11)   r := r / 2;
    (12) END;

Complexity: O(m² log c_max)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from algorithms.generic_max_flow import FlowStep, _fmt, _residual_diff_text

ArcKey = tuple[str, str]


def _find_path_with_threshold(
    r: dict[ArcKey, float],
    source: str,
    sink: str,
    threshold: float,
) -> list[str] | None:
    """Find a random s-t path using only arcs with residual ≥ threshold.

    Uses random neighbor selection with backtracking (same as generic).

    :param r: Residual capacity dictionary mapping (u, v) -> residual value.
    :param source: Source node ID (s).
    :param sink: Sink node ID (t).
    :param threshold: Minimum residual capacity for an arc to be considered.
    :return: List of node IDs forming the path, or None if no path exists.
    """
    visited: set[str] = {source}
    path: list[str] = [source]

    while path:
        u = path[-1]
        if u == sink:
            return list(path)

        neighbours = [b for (a, b), res in r.items()
                      if a == u and b not in visited and res >= threshold]
        if neighbours:
            b = random.choice(neighbours)
            visited.add(b)
            path.append(b)
        else:
            path.pop()

    return None


def run_ahuja_orlin(
    node_ids: list[str],
    edges: list[tuple[str, str, float]],
    source: str,
    sink: str,
) -> list[FlowStep]:
    """Run the Ahuja-Orlin Maximum Capacity Scaling algorithm.

    :param node_ids: All node IDs in the network.
    :param edges: List of (source, target, capacity) tuples for the original arcs.
    :param source: Source node ID (s).
    :param sink: Sink node ID (t).
    :return: Ordered list of FlowStep objects from initial state to termination.
    """

    # ---- Build original capacity table ---------------------------------
    cap: dict[ArcKey, float] = {}
    for u, v, c in edges:
        cap[(u, v)] = cap.get((u, v), 0.0) + max(0.0, c)

    # ---- Initial residual graph ----------------------------------------
    r: dict[ArcKey, float] = {}
    for (u, v), c in cap.items():
        r[(u, v)] = r.get((u, v), 0.0) + c
        if (v, u) not in r:
            r[(v, u)] = 0.0

    # ---- Helpers -------------------------------------------------------
    def active_residual() -> dict[ArcKey, float]:
        return {arc: val for arc, val in r.items() if val > 0}

    def compute_flow() -> dict[ArcKey, float]:
        return {arc: max(0.0, cap[arc] - r.get(arc, 0.0)) for arc in cap}

    def current_total_flow() -> float:
        f = compute_flow()
        return sum(f[(u, v)] for (u, v) in cap if u == source)

    steps: list[FlowStep] = []

    # ---- Compute initial threshold: r = 2^⌊log₂ c_max⌋ ----------------
    c_max = max(cap.values()) if cap else 0
    if c_max <= 0:
        threshold = 1.0
    else:
        threshold = float(2 ** math.floor(math.log2(c_max)))

    # ---- Step 0: initial state -----------------------------------------
    steps.append(FlowStep(
        index=0,
        phase='init',
        description=(
            "Initial state (Step 0)\n"
            "f\u2080 = 0 on all arcs.\n"
            f"c_max = {_fmt(c_max)}\n"
            f"Initial threshold r = 2^⌊log\u2082({_fmt(c_max)})⌋ = {_fmt(threshold)}\n\n"
            "Only arcs with residual \u2265 r will be used for path finding."
        ),
        residual=active_residual(),
        path=None,
        path_residual=None,
        flow=compute_flow(),
        total_flow=0.0,
    ))

    iteration = 0

    # ---- Line 3: WHILE r ≥ 1 ------------------------------------------
    while threshold >= 1:
        # Try to find augmenting paths at current threshold
        path = _find_path_with_threshold(r, source, sink, threshold)

        if path is None:
            # No more paths at this threshold — record scaling step
            steps.append(FlowStep(
                index=len(steps),
                phase='scaling',
                description=(
                    f"Scaling phase \u2014 no augmenting path with r \u2265 {_fmt(threshold)}\n"
                    f"Halving threshold: {_fmt(threshold)} \u2192 {_fmt(threshold / 2)}\n"
                    f"Total flow so far: {_fmt(current_total_flow())}"
                ),
                residual=active_residual(),
                path=None,
                path_residual=None,
                flow=compute_flow(),
                total_flow=current_total_flow(),
            ))
            threshold /= 2
            continue

        iteration += 1

        # Bottleneck
        path_r = min(r[(path[i], path[i + 1])] for i in range(len(path) - 1))

        path_str = " \u2192 ".join(path)
        caps_str = ", ".join(
            str(_fmt(r[(path[i], path[i + 1])]))
            for i in range(len(path) - 1)
        )

        # Step A: path found
        steps.append(FlowStep(
            index=len(steps),
            phase='found_path',
            description=(
                f"Iteration {iteration}a \u2014 Path found (threshold r \u2265 {_fmt(threshold)})\n"
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

        # MĂRIRE: augment along path
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
                f"Iteration {iteration}b \u2014 After augmentation (threshold r \u2265 {_fmt(threshold)})\n"
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
            f"Final state \u2014 threshold < 1, algorithm complete\n"
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
