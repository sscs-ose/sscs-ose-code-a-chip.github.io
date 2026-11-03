"""Independent logical one-hot row decoder."""


class RowDecoder:
    """Select one of any positive number of rows, initially none.

    Addresses must be exact integers in [0, rows). For non-power-of-two
    sizes, unused encoded addresses are rejected rather than wrapped.
    Invalid inputs leave the previous selection unchanged.
    """

    def __init__(self, rows: int) -> None:
        if type(rows) is not int or rows <= 0:
            raise ValueError("rows must be a positive integer.")
        self._rows = rows
        self._selected_row: int | None = None

    @property
    def rows(self) -> int:
        """Number of decoder outputs."""
        return self._rows

    @property
    def selected_row(self) -> int | None:
        """Current row address, or None after reset."""
        return self._selected_row

    def decode(self, address: int) -> tuple[int, ...]:
        """Select a valid address and return an immutable one-hot output."""
        self._validate_address(address)
        self._selected_row = address
        return self.get_state()

    def is_selected(self, row: int) -> bool:
        """Return whether a valid row is currently selected."""
        self._validate_address(row)
        return row == self._selected_row

    def get_state(self) -> tuple[int, ...]:
        """Return one-hot outputs, or all zeros when no row is selected."""
        return tuple(int(row == self._selected_row) for row in range(self.rows))

    def reset(self) -> None:
        """Clear the selected address and deactivate all decoder outputs."""
        self._selected_row = None

    def _validate_address(self, address: int) -> None:
        """Reject out-of-range addresses and non-integer inputs."""
        if type(address) is not int or not 0 <= address < self.rows:
            raise ValueError(f"row address must be an integer from 0 through {self.rows - 1}.")
