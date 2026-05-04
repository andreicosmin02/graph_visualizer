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
    """Find a random s-t path in the residual graph using positive residual arcs."""
    visited: set[str] = {source}
    path: list[str] = [source]

    while path:
        u = path[-1]
        if u == sink:
            return list(path)

        neighbours = [
            b for (a, b), res in r.items()
            if a == u and b not in visited and res > 0
        ]
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

    Notes:
        - This implementation assumes integer capacities.
        - Input capacities are floored to non-negative integers.
        - The visualization is organized by scaling levels.

    :param node_ids: All node IDs in the network.
    :param edges: List of (source, target, capacity) tuples for the original arcs.
    :param source: Source node ID (s).
    :param sink: Sink node ID (t).
    :return: Ordered list of FlowStep objects from initial state to termination.
    """

    # ---- Build original capacity table ---------------------------------
    # Gabow bit scaling is stated for integer capacities, so we floor inputs.
    cap: dict[ArcKey, float] = {}
    for u, v, c in edges:
        cap[(u, v)] = cap.get((u, v), 0.0) + float(max(0, math.floor(c)))

    # ---- Create scaled capacity levels ---------------------------------
    # c_0 = original, c_{k+1} = floor(c_k / 2), until max(c_p) <= 1
    cap_levels: list[dict[ArcKey, float]] = [dict(cap)]
    while True:
        prev = cap_levels[-1]
        max_cap = max(prev.values()) if prev else 0
        if max_cap <= 1:
            break
        cap_levels.append({arc: float(math.floor(val / 2)) for arc, val in prev.items()})

    p = len(cap_levels) - 1  # levels are 0..p, with p the coarsest

    # ---- Helpers -------------------------------------------------------
    def build_residual(cap_k: dict[ArcKey, float], flow_k: dict[ArcKey, float]) -> dict[ArcKey, float]:
        """Build the residual graph for level k.

        For every original arc (u,v):
            forward residual  = c_k(u,v) - f_k(u,v)
            backward residual = f_k(u,v)
        """
        r: dict[ArcKey, float] = {}
        for (u, v), c_uv in cap_k.items():
            f_uv = flow_k.get((u, v), 0.0)

            # Forward residual
            r[(u, v)] = r.get((u, v), 0.0) + (c_uv - f_uv)

            # Backward residual
            if (v, u) not in r:
                r[(v, u)] = 0.0
            r[(v, u)] = r.get((v, u), 0.0) + f_uv

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
        f"  Level {i}: c_max = {_fmt(max(lv.values()) if lv else 0)}"
        for i, lv in enumerate(cap_levels)
    )

    steps.append(FlowStep(
        index=0,
        phase='init',
        description=(
            "Initial state (Step 0)\n"
            "Gabow Bit Scaling with integer capacities.\n"
            f"Number of scaling levels: {p + 1} (0..{p})\n\n"
            f"Capacity levels:\n{level_caps_str}\n\n"
            f"Start from coarsest level {p}, then lift solutions back to level 0."
        ),
        residual={arc: val for arc, val in cap.items() if val > 0},
        path=None,
        path_residual=None,
        flow={arc: 0.0 for arc in cap},
        total_flow=0.0,
    ))

    iteration = 0

    # ---- Solve coarsest level first ------------------------------------
    current_flow: dict[ArcKey, float] = {arc: 0.0 for arc in cap_levels[p]}

    for k in range(p, -1, -1):
        cap_k = cap_levels[k]

        if k < p:
            # Lift the solution from level k+1 to level k:
            #     f^0_k = 2 * f*_{k+1}
            #
            # For integer capacities and ck+1 = floor(ck/2), this is feasible:
            #     2 f*_{k+1}(u,v) <= 2 c_{k+1}(u,v) <= c_k(u,v)
            prev_flow = current_flow
            current_flow = {
                arc: 2.0 * prev_flow.get(arc, 0.0)
                for arc in cap_k
            }

            lifted_total = total_flow_value(current_flow, cap_k)
            steps.append(FlowStep(
                index=len(steps),
                phase='scaling',
                description=(
                    f"Level {k} — lifted initial flow from level {k + 1}\n"
                    f"Set f₀_{k} = 2 × f*_{k + 1}.\n"
                    "By the bit-scaling theorem, this is a feasible starting flow.\n"
                    "The remaining corrections are completed in the residual network.\n\n"
                    f"Initial lifted flow value at level {k}: {_fmt(lifted_total)}"
                ),
                residual=active_residual(build_residual(cap_k, current_flow)),
                path=None,
                path_residual=None,
                flow=dict(current_flow),
                total_flow=lifted_total,
            ))

        # Build residual graph for the current level and finish max flow there.
        r = build_residual(cap_k, current_flow)

        while True:
            path = _find_path(r, source, sink)
            if path is None:
                break

            iteration += 1

            # In the exact theorem setting, after lifting from level k+1,
            # augmenting paths in the residual network have residual capacity 1.
            # We still compute the bottleneck for display/validation.
            path_bottleneck = min(r[(path[i], path[i + 1])] for i in range(len(path) - 1))
            delta = min(1.0, path_bottleneck)

            path_str = " → ".join(path)
            caps_str = ", ".join(
                str(_fmt(r[(path[i], path[i + 1])]))
                for i in range(len(path) - 1)
            )

            steps.append(FlowStep(
                index=len(steps),
                phase='found_path',
                description=(
                    f"Iteration {iteration}a — Path found (level {k})\n"
                    f"D̃ = ({path_str})\n\n"
                    f"Residuals on path: {{{caps_str}}}\n"
                    f"bottleneck = {_fmt(path_bottleneck)}\n"
                    f"augmentation used = {_fmt(delta)}\n\n"
                    "For Gabow bit scaling with integer capacities, this is expected "
                    "to be a unit augmentation after lifting."
                ),
                residual=active_residual(r),
                path=list(path),
                path_residual=delta,
                flow=compute_flow_from_residual(cap_k, r),
                total_flow=total_flow_value(compute_flow_from_residual(cap_k, r), cap_k),
            ))

            # Unit augmentation on this level
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                r[(u, v)] -= delta
                r[(v, u)] = r.get((v, u), 0.0) + delta

            current_flow = compute_flow_from_residual(cap_k, r)
            new_total = total_flow_value(current_flow, cap_k)

            steps.append(FlowStep(
                index=len(steps),
                phase='augmented',
                description=(
                    f"Iteration {iteration}b — After augmentation (level {k})\n"
                    f"Sent {_fmt(delta)} unit(s) along\n"
                    f"D̃ = ({path_str})\n\n"
                    "Residual network updated:\n"
                    + _residual_diff_text(path, delta)
                    + f"\n\nTotal flow at level {k}: {_fmt(new_total)}"
                ),
                residual=active_residual(r),
                path=list(path),
                path_residual=delta,
                flow=compute_flow_from_residual(cap_k, r),
                total_flow=new_total,
            ))

        current_flow = compute_flow_from_residual(cap_k, r)

        steps.append(FlowStep(
            index=len(steps),
            phase='scaling',
            description=(
                f"Level {k} complete\n"
                f"A maximum flow has been obtained for capacity level {k}.\n"
                f"Flow value at this level: {_fmt(total_flow_value(current_flow, cap_k))}"
            ),
            residual=active_residual(r),
            path=None,
            path_residual=None,
            flow=dict(current_flow),
            total_flow=total_flow_value(current_flow, cap_k),
        ))

    # ---- Final step ----------------------------------------------------
    final_r = build_residual(cap, current_flow)
    final_flow = compute_flow_from_residual(cap, final_r)
    tv = total_flow_value(final_flow, cap)

    flow_lines = "\n".join(
        f"  f({u},{v}) = {_fmt(final_flow.get((u, v), 0.0))}"
        for (u, v) in sorted(cap.keys())
    )

    steps.append(FlowStep(
        index=len(steps),
        phase='final',
        description=(
            "Final state — all levels processed\n"
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