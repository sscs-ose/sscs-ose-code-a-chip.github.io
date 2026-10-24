"""Numerical reference: mathematical dot products followed by INT32 wrapping.

No systolic scheduling or cycle estimate appears here. Wrapping the exact dot
product once is equivalent to modulo wrapping after every MAC, allowing this
reference to differ structurally from the token model and hardware.
"""

from model.arithmetic import int8, validate_matrices, wrap_int32

__all__ = ["gemm", "int8", "wrap_int32"]


def gemm(A: list[list[int]], B: list[list[int]]) -> list[list[int]]:
    """Compute A[M,K] @ B[K,N], with signed INT8 input and wrapped INT32 C."""
    M, N, K = validate_matrices(A, B)
    return [
        [wrap_int32(sum(A[i][k] * B[k][j] for k in range(K))) for j in range(N)]
        for i in range(M)
    ]
