"""DCDL (Digitally Controlled Delay Line) models for DLL simulation.

All variants share:
    - num_cells: number of selectable delay taps/stages
    - first_cell_delay_ps: propagation delay of the first cell (from SPICE)
    - remaining_cell_delay_ps: propagation delay of cells 2..N (from SPICE)

The total propagation delay is fully determined by cell delays plus
architecture-specific gate overhead (mux tree, NAND tree, etc.).
"""

from __future__ import annotations
import math


class DCDL:
    """Base DCDL.  Subclasses implement ``_delay(ctrl)``."""

    def __init__(self, num_cells: int,
                 first_cell_delay_ps: float,
                 remaining_cell_delay_ps: float):
        self.num_cells = num_cells
        self.first_cell_delay_ps = first_cell_delay_ps
        self.remaining_cell_delay_ps = remaining_cell_delay_ps

    def _cells_delay(self, n: int) -> float:
        """Cumulative delay through the first *n* cells."""
        if n <= 0:
            return 0.0
        if n == 1:
            return self.first_cell_delay_ps
        return self.first_cell_delay_ps + (n - 1) * self.remaining_cell_delay_ps

    def delay(self, ctrl: int) -> float:
        """Total propagation delay (ps) for the given control word."""
        return self._delay(ctrl)

    def _delay(self, ctrl: int) -> float:
        raise NotImplementedError


# ===================================================================
# 2. Inverter DCDL  (inv_dcdl.sv)
#    Binary mux tree selects tap.  ctrl in [0, num_cells-1].
#    Tap k routes through k+1 cells then ceil(log2(N)) mux levels.
# ===================================================================

class InverterDCDL(DCDL):
    """Inverter chain + binary mux tree.

    Extra parameter: mux_delay_ps (per mux level).
    Mux levels = ceil(log2(num_cells)).
    """

    def __init__(self, num_cells: int,
                 first_cell_delay_ps: float,
                 remaining_cell_delay_ps: float,
                 mux_delay_ps: float):
        super().__init__(num_cells, first_cell_delay_ps,
                         remaining_cell_delay_ps)
        self.mux_delay_ps = mux_delay_ps
        self.mux_levels = math.ceil(math.log2(num_cells)) if num_cells > 1 else 0

    def _delay(self, ctrl: int) -> float:
        tap = ctrl % self.num_cells
        return self._cells_delay(tap + 1) + self.mux_levels * self.mux_delay_ps


# ===================================================================
# 3. Conditional Inverter DCDL  (inv_dcdl_cond.sv)
#    Same as InverterDCDL but with XNOR gate at output.
# ===================================================================

class InverterCondDCDL(DCDL):
    """Inverter chain + mux tree + XNOR output.

    Extra parameters: mux_delay_ps, xnor_delay_ps.
    Mux levels = ceil(log2(num_cells)).
    """

    def __init__(self, num_cells: int,
                 first_cell_delay_ps: float,
                 remaining_cell_delay_ps: float,
                 mux_delay_ps: float,
                 xnor_delay_ps: float):
        super().__init__(num_cells, first_cell_delay_ps,
                         remaining_cell_delay_ps)
        self.mux_delay_ps = mux_delay_ps
        self.xnor_delay_ps = xnor_delay_ps
        self.mux_levels = math.ceil(math.log2(num_cells)) if num_cells > 1 else 0

    def _delay(self, ctrl: int) -> float:
        tap = ctrl % self.num_cells
        return (self._cells_delay(tap + 1)
                + self.mux_levels * self.mux_delay_ps
                + self.xnor_delay_ps)


# ===================================================================
# 4. Glitch-free Inverter DCDL  (inv_dcdl_glitch_free.sv)
#    One-hot registered select.  Tap k = k chain cells.
#    Output stage: 1 inversion inverter + 1 gating NAND +
#                  ceil(log2(N))-level NAND tree.
# ===================================================================

class InverterGlitchFreeDCDL(DCDL):
    """Glitch-free inverter chain + NAND gating tree.

    Extra parameter: nand_delay_ps (per NAND gate).
    NAND tree depth = ceil(log2(num_cells)).

    Signal path for tap k:
        k chain cells -> 1 inversion inv -> 1 gating NAND ->
        ceil(log2(N)) NAND tree levels

    tap 0 = direct input A (0 chain cells).
    The inversion inverter has the same delay as remaining_cell_delay_ps.
    """

    def __init__(self, num_cells: int,
                 first_cell_delay_ps: float,
                 remaining_cell_delay_ps: float,
                 nand_delay_ps: float):
        super().__init__(num_cells, first_cell_delay_ps,
                         remaining_cell_delay_ps)
        self.nand_delay_ps = nand_delay_ps
        self.nand_tree_depth = math.ceil(math.log2(num_cells)) if num_cells > 1 else 0

    def _delay(self, ctrl: int) -> float:
        tap = ctrl % self.num_cells
        chain_delay = self._cells_delay(tap)
        output_delay = (self.remaining_cell_delay_ps
                        + (1 + self.nand_tree_depth) * self.nand_delay_ps)
        return chain_delay + output_delay


class NandDCDL(DCDL):
    def __init__(self, num_cells=64, first_cell_delay_ps=106.67, remaining_cell_delay_ps=72.68):
        super().__init__(num_cells, first_cell_delay_ps, remaining_cell_delay_ps)

    def _delay(self, ctrl: int) -> float:
        total = 0.0
        for i in range(self.num_cells):
            if not (ctrl & (1 << i)):
                if i == 0:
                    total += self.first_cell_delay_ps
                else:
                    total += self.remaining_cell_delay_ps
        return total

