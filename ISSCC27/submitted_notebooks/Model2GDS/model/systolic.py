"""A fixed 2x2, output-stationary, edge-by-edge token model.

All four PEs read old neighbor registers and update simultaneously. Completion
comes from final-token flags in the active PEs, never from a cycle formula.
There is no RTL, simulator-output, or physical-metric input to this model.
"""

from model.arithmetic import positive_dimension, validate_matrices, wrap_int32

Token = tuple[int, int, bool] | None  # (signed value, reduction index k, last)


def tiles(M: int, N: int) -> list[dict]:
    """Return nonempty output tiles, ordered by row and then column."""
    positive_dimension(M, "M")
    positive_dimension(N, "N")
    return [
        {"row": row, "col": col, "rows": min(2, M - row), "cols": min(2, N - col)}
        for row in range(0, M, 2)
        for col in range(0, N, 2)
    ]


def closed_form_cycles(M: int, N: int, K: int) -> int:
    """Secondary bubble-free schedule identity; never used by simulate()."""
    positive_dimension(K, "K")
    return sum(K + tile["rows"] + tile["cols"] - 1 for tile in tiles(M, N))


def _token_record(token: Token) -> dict:
    if token is None:
        return {"valid": False, "value": 0, "k": None, "last": False}
    value, k, last = token
    return {"valid": True, "value": value, "k": k, "last": last}


def simulate(A: list[list[int]], B: list[list[int]], trace: bool = False) -> dict:
    """Run sequential output tiles through four explicit PE register states.

    The optional trace has one record per counted edge, including clear edges.
    Each data record contains sampled tokens and the resulting registered state.
    Pipeline bubbles are invalid zero tokens. Each result is read after its
    final MAC edge; the next tile's clear is the next counted edge.
    """
    M, N, K = validate_matrices(A, B)
    C = [[0 for _ in range(N)] for _ in range(M)]
    completed_tiles = []
    edge_trace = []
    total_cycles = 0
    for tile_index, tile in enumerate(tiles(M, N)):
        row0, col0, r, c = (tile[name] for name in ("row", "col", "rows", "cols"))
        a_reg: list[list[Token]] = [[None, None], [None, None]]
        b_reg: list[list[Token]] = [[None, None], [None, None]]
        acc = [[0, 0], [0, 0]]
        result_valid = [[False, False], [False, False]]
        tile_cycles = 1  # The clear/setup edge is counted.
        active_mask = sum(1 << (2 * i + j) for i in range(r) for j in range(c))
        if trace:
            edge_trace.append({
                "cycle": total_cycles + 1, "tile_index": tile_index,
                "tile_cycle": 1, "phase": "clear", "data_edge": None,
                "active_mask": active_mask, "tile_done": False,
                "pe": [{"row": i, "col": j, "a": _token_record(None),
                        "b": _token_record(None), "acc": 0, "result_valid": False}
                       for i in range(2) for j in range(2)],
            })
        t = 0
        while True:
            left: list[Token] = [None, None]
            top: list[Token] = [None, None]
            for i in range(r):
                k = t - i
                if 0 <= k < K:
                    left[i] = (A[row0 + i][k], k, k == K - 1)
            for j in range(c):
                k = t - j
                if 0 <= k < K:
                    top[j] = (B[k][col0 + j], k, k == K - 1)
            next_a: list[list[Token]] = [[None, None], [None, None]]
            next_b: list[list[Token]] = [[None, None], [None, None]]
            for i in range(2):
                for j in range(2):
                    a = left[i] if j == 0 else a_reg[i][j - 1]
                    b = top[j] if i == 0 else b_reg[i - 1][j]
                    next_a[i][j], next_b[i][j] = a, b
                    if a is not None and b is not None:
                        if a[1] != b[1] or a[2] != b[2]:
                            raise AssertionError("Mismatched reduction tokens in the Python schedule")
                        if result_valid[i][j]:
                            raise AssertionError("Producer supplied another valid pair after last")
                        acc[i][j] = wrap_int32(acc[i][j] + a[0] * b[0])
                        if a[2] and b[2]:
                            result_valid[i][j] = True
            a_reg, b_reg = next_a, next_b
            tile_cycles += 1
            tile_done = all(result_valid[i][j] for i in range(r) for j in range(c))
            if trace:
                edge_trace.append({
                    "cycle": total_cycles + tile_cycles, "tile_index": tile_index,
                    "tile_cycle": tile_cycles, "phase": "data", "data_edge": t,
                    "active_mask": active_mask, "tile_done": tile_done,
                    "left": [_token_record(value) for value in left],
                    "top": [_token_record(value) for value in top],
                    "pe": [{"row": i, "col": j, "a": _token_record(a_reg[i][j]),
                            "b": _token_record(b_reg[i][j]), "acc": acc[i][j],
                            "result_valid": result_valid[i][j]}
                           for i in range(2) for j in range(2)],
                })
            if tile_done:
                break
            t += 1
            # Defensive failure bound only: observed final tokens determine done.
            if t > 16 * (K + 1):
                raise RuntimeError("Token model failed to complete within its safety bound")
        for i in range(r):
            for j in range(c):
                C[row0 + i][col0 + j] = acc[i][j]
        total_cycles += tile_cycles
        completed_tiles.append({**tile, "cycles": tile_cycles})
    result = {"M": M, "N": N, "K": K, "array_size": 2, "cycles": total_cycles,
              "C": C, "tiles": completed_tiles}
    if trace:
        result["trace"] = edge_trace
    return result
