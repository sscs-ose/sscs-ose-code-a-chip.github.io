"""Explicit two's-complement conversions; no dependency on RTL or EDA data."""


def int8(raw_byte: int) -> int:
    """Interpret an unsigned byte (0..255) as a signed INT8 value.

    This is a bit-pattern conversion, not a truncating cast. GEMM APIs instead
    accept already signed integers in -128..127 and reject out-of-range values.
    """
    if type(raw_byte) is not int or not 0 <= raw_byte <= 255:
        raise ValueError("INT8 bit pattern must be an integer in 0..255")
    return raw_byte if raw_byte < 128 else raw_byte - 256


def wrap_int32(value: int) -> int:
    """Return the signed representative after modulo-2**32 wrapping."""
    if type(value) is not int:
        raise ValueError("INT32 wrapping requires an integer")
    low_bits = value & 0xFFFFFFFF
    return low_bits if low_bits < 0x80000000 else low_bits - 0x100000000


def positive_dimension(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def validate_matrices(A: list[list[int]], B: list[list[int]]) -> tuple[int, int, int]:
    """Validate signed input values and return (M, N, K); do no arithmetic."""
    for name, matrix in (("A", A), ("B", B)):
        if not isinstance(matrix, (list, tuple)) or not matrix:
            raise ValueError(f"{name} must be a nonempty matrix")
        if not isinstance(matrix[0], (list, tuple)) or not matrix[0]:
            raise ValueError(f"{name} must have nonempty rows")
        columns = len(matrix[0])
        for row in matrix:
            if not isinstance(row, (list, tuple)) or len(row) != columns:
                raise ValueError(f"{name} must be rectangular")
            if any(type(value) is not int or not -128 <= value <= 127 for value in row):
                raise ValueError(f"{name} values must be signed INT8 integers in -128..127")
    if len(A[0]) != len(B):
        raise ValueError("A columns must equal B rows")
    return len(A), len(B[0]), len(B)
