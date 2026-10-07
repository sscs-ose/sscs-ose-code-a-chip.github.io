"""Phase 2 token model for the three authorized output-stationary arrays.

The immutable Phase 1 implementation remains separate. This model advances
every physical PE from old neighbor registers and observes masked last tokens;
neither a closed-form cycle count nor a numerical GEMM controls completion.
"""
from model.arithmetic import positive_dimension, validate_matrices, wrap_int32

ARRAY_SIZES = (2, 4, 8)
Token = tuple[int, int, bool] | None


def validate_array_size(array_size):
    if type(array_size) is not int or array_size not in ARRAY_SIZES:
        raise ValueError("Phase 2 array_size must be exactly 2, 4, or 8")


def tiles(M, N, array_size):
    validate_array_size(array_size)
    positive_dimension(M, "M")
    positive_dimension(N, "N")
    return [{"row": row, "col": col, "rows": min(array_size, M-row),
             "cols": min(array_size, N-col)}
            for row in range(0, M, array_size) for col in range(0, N, array_size)]


def closed_form_cycles(M, N, K, array_size):
    """Secondary identity for the declared bubble-free schedule only."""
    positive_dimension(K, "K")
    return sum(K + tile["rows"] + tile["cols"] - 1 for tile in tiles(M, N, array_size))


def _record(token):
    return ({"valid": False, "value": 0, "k": None, "last": False} if token is None else
            {"valid": True, "value": token[0], "k": token[1], "last": token[2]})


def simulate(A, B, array_size, trace=False):
    """Return C and observed counted edges for sequential output tiles.

    One clear edge precedes each tile. Inactive PEs still register their tokens,
    but only active outputs determine completion. All arithmetic is signed INT8
    multiplication with explicit modulo-2**32 accumulator wrapping.
    """
    validate_array_size(array_size)
    M, N, K = validate_matrices(A, B)
    S = array_size
    C = [[0] * N for _ in range(M)]
    completed, edge_trace = [], []
    total = 0
    for tile_index, tile in enumerate(tiles(M, N, S)):
        row0, col0, r, c = (tile[key] for key in ("row", "col", "rows", "cols"))
        a_reg: list[list[Token]] = [[None] * S for _ in range(S)]
        b_reg: list[list[Token]] = [[None] * S for _ in range(S)]
        acc = [[0] * S for _ in range(S)]
        valid = [[False] * S for _ in range(S)]
        mask = sum(1 << (i*S+j) for i in range(r) for j in range(c))
        cycles = 1
        if trace:
            edge_trace.append({"cycle": total+1, "tile_index": tile_index, "tile_cycle": 1,
                               "phase": "clear", "data_edge": None, "active_mask": mask,
                               "tile_done": False,
                               "pe": [{"row": i, "col": j, "a": _record(None), "b": _record(None),
                                       "acc": 0, "result_valid": False}
                                      for i in range(S) for j in range(S)]})
        t = 0
        while True:
            left: list[Token] = [None] * S
            top: list[Token] = [None] * S
            for i in range(r):
                k = t-i
                if 0 <= k < K:
                    left[i] = (A[row0+i][k], k, k == K-1)
            for j in range(c):
                k = t-j
                if 0 <= k < K:
                    top[j] = (B[k][col0+j], k, k == K-1)
            next_a: list[list[Token]] = [[None] * S for _ in range(S)]
            next_b: list[list[Token]] = [[None] * S for _ in range(S)]
            for i in range(S):
                for j in range(S):
                    a = left[i] if j == 0 else a_reg[i][j-1]
                    b = top[j] if i == 0 else b_reg[i-1][j]
                    next_a[i][j], next_b[i][j] = a, b
                    if a is not None and b is not None:
                        if a[1:] != b[1:]:
                            raise AssertionError("Reduction token identity/last mismatch")
                        if valid[i][j]:
                            raise AssertionError("Valid pair supplied after final token")
                        acc[i][j] = wrap_int32(acc[i][j] + a[0]*b[0])
                        if a[2] and b[2]:
                            valid[i][j] = True
            a_reg, b_reg = next_a, next_b
            cycles += 1
            done = all(valid[i][j] for i in range(r) for j in range(c))
            if trace:
                edge_trace.append({"cycle": total+cycles, "tile_index": tile_index,
                                   "tile_cycle": cycles, "phase": "data", "data_edge": t,
                                   "active_mask": mask, "tile_done": done,
                                   "left": [_record(x) for x in left], "top": [_record(x) for x in top],
                                   "pe": [{"row": i, "col": j, "a": _record(a_reg[i][j]),
                                           "b": _record(b_reg[i][j]), "acc": acc[i][j],
                                           "result_valid": valid[i][j]}
                                          for i in range(S) for j in range(S)]})
            if done:
                break
            t += 1
            if t > 16 * (K + S + 1):
                raise RuntimeError("Token model exceeded defensive completion timeout")
        for i in range(r):
            for j in range(c):
                C[row0+i][col0+j] = acc[i][j]
        total += cycles
        completed.append({**tile, "cycles": cycles})
    result = {"M": M, "N": N, "K": K, "array_size": S,
              "C": C, "cycles": total, "tiles": completed}
    if trace:
        result["trace"] = edge_trace
    return result
