"""Edmonds-Karp shortest augmenting path algorithm.

Identical to the Ford-Fulkerson labeling algorithm (FFE) but with one key
difference: the list of labeled-but-unanalyzed nodes Ṽ is organized as a
FIFO queue (BFS).  This guarantees that the augmenting path found is always
a shortest path from s to t in the residual network.

Complexity: O(m²n)  — polynomial, unlike FFE's O(mnc) pseudopolynomial.

Reference (from course):
    "Algoritmul Edmonds-Karp al drumului celui mai scurt se obține din
     algoritmul de etichetare Ford-Fulkerson printr-o minoră modificare:
     lista nodurilor etichetate și neanalizate Ṽ este organizată, sub
     aspectul unei structuri de date, ca o coadă."
"""

from __future__ import annotations

from collections import deque

from algorithms.generic_max_flow import FlowStep, _fmt, _residual_diff_text

ArcKey = tuple[str, str]


def run_edmonds_karp(
    node_ids: list[str],
    edges: list[tuple[str, str, float]],
    source: str,
    sink: str,
) -> list[FlowStep]:
    """Run the Edmonds-Karp (shortest path) algorithm and return every recorded step.

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

    # ---- Line 5: p̃(t) := s  (to enter the while loop) -----------------
    pred_t = source

    # ---- Line 6: WHILE p̃(t) ≠ 0 --------------------------------------
    while pred_t != 0:
        # Line 8: FOR y ∈ Ñ DO p̃(y) := 0  — reset all labels
        p: dict[str, str | int] = {y: 0 for y in node_ids}

        # Line 9: Ṽ := {s}; p̃(s) := t  — initialize as FIFO queue (BFS)
        V: deque[str] = deque([source])  # FIFO queue = BFS ordering
        p[source] = sink  # p̃(s) := t — mark source as labeled

        # ---- BFS labeling (lines 10-16) --------------------------------
        # Edmonds-Karp: nodes are analyzed in FIFO order (first labeled,
        # first analyzed) — this produces a shortest augmenting path.
        # Line 10: WHILE Ṽ ≠ ∅ and p̃(t) = 0
        while V and p[sink] == 0:
            # Line 12: extract node x from Ṽ  (FIFO: popleft = BFS)
            x = V.popleft()

            # Line 13-15: FOR (x,y) ∈ Ã: IF p̃(y)=0 THEN p̃(y):=x; Ṽ:=Ṽ∪{y}
            for (a, b), res in r.items():
                if a == x and res > 0 and p[b] == 0:
                    p[b] = x
                    V.append(b)

        pred_t = p[sink]

        # Line 17-18: IF p̃(t) ≠ 0 THEN MĂRIRE
        if pred_t != 0:
            iteration += 1

            # Reconstruct DMF D̃ from predecessor vector
            path: list[str] = []
            node = sink
            while node != source:
                path.append(node)
                node = p[node]
            path.append(source)
            path.reverse()

            # r(D̃) = min{r(x,y) | (x,y) ∈ D̃}
            path_r = min(r[(path[i], path[i + 1])] for i in range(len(path) - 1))

            path_str = " \u2192 ".join(path)
            caps_str = ", ".join(
                str(_fmt(r[(path[i], path[i + 1])]))
                for i in range(len(path) - 1)
            )

            pred_str = ", ".join(
                f"p\u0303({y})={p[y]}" for y in node_ids if p[y] != 0
            )

            # Step A: shortest path found via BFS labeling
            steps.append(FlowStep(
                index=len(steps),
                phase='found_path',
                description=(
                    f"Iteration {iteration}a \u2014 BFS labeling complete\n"
                    f"Predecessor: {pred_str}\n"
                    f"Shortest D\u0303 = ({path_str})\n\n"
                    f"r(D\u0303) = min{{{caps_str}}}\n"
                    f"      = {_fmt(path_r)}\n\n"
                    "The shortest path will be augmented by this amount."
                ),
                residual=active_residual(),
                path=list(path),
                path_residual=path_r,
                flow=compute_flow(),
                total_flow=current_total_flow(),
            ))

            # MĂRIRE: augment along D̃
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
                    f"Iteration {iteration}b \u2014 After augmentation (M\u0102RIRE)\n"
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

    # ---- Final step: p̃(t) = 0, no more DMF ---------------------------
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
            f"Final state \u2014 p\u0303(t) = 0, no augmenting path\n"
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
