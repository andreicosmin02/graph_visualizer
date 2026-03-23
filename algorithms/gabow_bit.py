"""Gabow Bit Scaling algorithm.

Creates a sequence of scaled capacity matrices by repeatedly halving:
    c₀ = c,  c_{k+1} = ⌊c_k / 2⌋
until max capacity ≤ 1.

Then solves from the coarsest level back to the finest, using 2·f*_{k+1}
as the initial flow for level k.

Pseudocode reference:
    (1)  se construiesc c₁, c₂, ..., c_p (p = ⌊log₂ c_max⌋)
    (2)  f*_p := fluxul maxim in G cu capacitățile c_p
    (3)  FOR k := p-1, p-2, ..., 0 DO
    (4)    f₀_k := 2 · f*_{k+1}
    (5)    f*_k := fluxul maxim in G cu capacitățile c_k pornind de la f₀_k

Complexity: O(m² log c_max)
"""

from __future__ import annotations

import math
import random

from algorithms.generic_max_flow import FlowStep, _fmt, _residual_diff_text

ArcKey = tuple[str, str]


def _find_path(r: dict[ArcKey, float], source: str, sink: str) -> list[str] | None:
    """Find a random s-t path in the residual graph.

    Uses random neighbor selection with backtracking.

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


def run_gabow_bit(
    node_ids: list[str],
    edges: list[tuple[str, str, float]],
    source: str,
    sink: str,
) -> list[FlowStep]:
    """Run the Gabow Bit Scaling algorithm.

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

    # ---- Create scaled capacity levels ---------------------------------
    # c_0 = original, c_1 = ⌊c_0/2⌋, ..., c_p where max(c_p) ≤ 1
    cap_levels: list[dict[ArcKey, float]] = [dict(cap)]
    while True:
        prev = cap_levels[-1]
        max_cap = max(prev.values()) if prev else 0
        if max_cap <= 1:
            break
        halved = {arc: math.floor(c / 2) for arc, c in prev.items()}
        cap_levels.append(halved)

    p = len(cap_levels) - 1  # number of scaling levels (0..p)

    # ---- Helpers -------------------------------------------------------
    def build_residual(cap_k: dict[ArcKey, float], flow_k: dict[ArcKey, float]) -> dict[ArcKey, float]:
        """Build residual graph from capacity and flow at a given level.

        r(u,v) = c(u,v) - f(u,v)  (forward residual)
        r(v,u) += f(u,v)          (backward residual)
        """
        r: dict[ArcKey, float] = {}
        for (u, v) in cap_k:
            fwd = cap_k[(u, v)] - flow_k.get((u, v), 0.0)
            bwd = flow_k.get((u, v), 0.0)
            r[(u, v)] = r.get((u, v), 0.0) + fwd
            if (v, u) not in r:
                r[(v, u)] = 0.0
            r[(v, u)] = r.get((v, u), 0.0) + bwd
        return r

    def active_residual(r: dict[ArcKey, float]) -> dict[ArcKey, float]:
        return {arc: val for arc, val in r.items() if val > 0}

    def compute_flow_from_residual(cap_k: dict[ArcKey, float], r: dict[ArcKey, float]) -> dict[ArcKey, float]:
        return {arc: max(0.0, cap_k[arc] - r.get(arc, 0.0)) for arc in cap_k}

    def total_flow_value(flow: dict[ArcKey, float], cap_k: dict[ArcKey, float]) -> float:
        return sum(flow.get((u, v), 0.0) for (u, v) in cap_k if u == source)

    steps: list[FlowStep] = []

    # ---- Step 0: initial state -----------------------------------------
    level_caps_str = "\n".join(
        f"  Level {i}: c_max = {_fmt(max(lv.values()) if lv.values() else 0)}"
        for i, lv in enumerate(cap_levels)
    )

    steps.append(FlowStep(
        index=0,
        phase='init',
        description=(
            "Initial state (Step 0)\n"
            f"Number of scaling levels: {p + 1} (0..{p})\n\n"
            f"Capacity levels:\n{level_caps_str}\n\n"
            f"Starting from coarsest level {p}, working back to level 0."
        ),
        residual=active_residual({arc: cap[arc] for arc in cap}),
        path=None,
        path_residual=None,
        flow={arc: 0.0 for arc in cap},
        total_flow=0.0,
    ))

    iteration = 0

    # ---- Solve from coarsest (level p) to finest (level 0) -------------
    current_flow: dict[ArcKey, float] = {arc: 0.0 for arc in cap_levels[p]}

    for k in range(p, -1, -1):
        cap_k = cap_levels[k]

        if k < p:
            # f₀_k = 2 · f*_{k+1}  — double the flow from previous (coarser) level
            prev_flow = current_flow
            current_flow = {}
            for arc in cap_k:
                doubled = 2 * prev_flow.get(arc, 0.0)
                current_flow[arc] = min(doubled, cap_k[arc])

            steps.append(FlowStep(
                index=len(steps),
                phase='scaling',
                description=(
                    f"Level {k} \u2014 Initial flow = 2 \u00d7 f*_{k+1}\n"
                    f"Capacities at level {k}, doubled flow from level {k+1}.\n"
                    f"Total flow: {_fmt(total_flow_value(current_flow, cap_k))}"
                ),
                residual=active_residual(build_residual(cap_k, current_flow)),
                path=None,
                path_residual=None,
                flow={arc: current_flow.get(arc, 0.0) for arc in cap if arc in cap_k},
                total_flow=total_flow_value(current_flow, cap_k),
            ))

        # Build residual and find augmenting paths at this level
        r = build_residual(cap_k, current_flow)

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

            # Step A: path found
            steps.append(FlowStep(
                index=len(steps),
                phase='found_path',
                description=(
                    f"Iteration {iteration}a \u2014 Path found (level {k})\n"
                    f"D\u0303 = ({path_str})\n\n"
                    f"r(D\u0303) = min{{{caps_str}}}\n"
                    f"      = {_fmt(path_r)}\n\n"
                    "The path will be augmented by this amount."
                ),
                residual=active_residual(r),
                path=list(path),
                path_residual=path_r,
                flow=compute_flow_from_residual(cap_k, r),
                total_flow=total_flow_value(compute_flow_from_residual(cap_k, r), cap_k),
            ))

            # Augment
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                r[(u, v)] -= path_r
                r[(v, u)] = r.get((v, u), 0.0) + path_r

            current_flow = compute_flow_from_residual(cap_k, r)
            new_total = total_flow_value(current_flow, cap_k)

            # Step B: after augmentation
            steps.append(FlowStep(
                index=len(steps),
                phase='augmented',
                description=(
                    f"Iteration {iteration}b \u2014 After augmentation (level {k})\n"
                    f"Sent {_fmt(path_r)} units along\n"
                    f"D\u0303 = ({path_str})\n\n"
                    "Residual network updated:\n"
                    + _residual_diff_text(path, path_r)
                    + f"\n\nTotal flow at level {k}: {_fmt(new_total)}"
                ),
                residual=active_residual(r),
                path=list(path),
                path_residual=path_r,
                flow=compute_flow_from_residual(cap_k, r),
                total_flow=new_total,
            ))

        # Update current_flow for this level
        current_flow = compute_flow_from_residual(cap_k, r)

    # ---- Final step ----------------------------------------------------
    # At level 0, cap_levels[0] == original cap
    final_r = build_residual(cap, current_flow)
    final_flow = compute_flow_from_residual(cap, final_r)
    tv = total_flow_value(final_flow, cap)

    flow_lines = "\n".join(
        f"  f({u},{v}) = {_fmt(final_flow.get((u,v), 0.0))}"
        for (u, v) in sorted(cap.keys())
    )

    steps.append(FlowStep(
        index=len(steps),
        phase='final',
        description=(
            f"Final state \u2014 all levels processed\n"
            f"Maximum flow value = {_fmt(tv)}\n\n"
            "Arc flows:\n"
            + flow_lines
        ),
        residual=active_residual(final_r),
        path=None,
        path_residual=None,
        flow=final_flow,
        total_flow=tv,
    ))

    return steps
