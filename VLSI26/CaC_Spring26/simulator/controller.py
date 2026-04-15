"""Controller models for DLL simulation.

All variants share the same RTL interface:
    Inputs:  clk_in (posedge), rst, up (1-bit), down (1-bit)
    Outputs: ctrl [CTRL_BITS-1:0]

The base class handles:
    - ctrl clamping and initialisation
    - Pipeline management (propagation-delay-aware output buffering)
    - Reset

Each subclass implements _step(up, down) — the one-cycle algorithm.
"""

from __future__ import annotations
from collections import deque


class Controller:
    """Base controller.  Subclasses implement ``_step(up, down)``."""

    def __init__(self, ctrl_bits: int = 6, init_ctrl: int = 32,
                 prop_delay_ps: float = 0.0):
        self.ctrl_bits = ctrl_bits
        self.init_ctrl = init_ctrl
        self.prop_delay_ps = prop_delay_ps
        self.max_ctrl = (1 << ctrl_bits) - 1

        self._ctrl: int = self._clamp(init_ctrl)
        self.ctrl: int = self._ctrl      # public — what the DCDL sees
        self._pipe: deque | None = None  # set by configure_pipeline

    # ---- clamping ----

    def _clamp(self, val: int) -> int:
        return max(0, min(val, self.max_ctrl))

    # ---- pipeline ----

    def configure_pipeline(self, upstream_delay_ps: float,
                           clk_period_ps: float) -> None:
        """Set up internal output pipeline.

        Call once before the simulation loop.  The combined delay
        (upstream PD delay + this controller's prop delay) determines
        how many extra cycles the ctrl output is stale.
        """
        pipeline_ps = upstream_delay_ps + self.prop_delay_ps
        extra = int(pipeline_ps / clk_period_ps)
        if extra > 0:
            self._pipe = deque([self._ctrl] * extra, maxlen=extra)
        else:
            self._pipe = None

    # ---- cycle update ----

    def update(self, up: int, down: int) -> None:
        """Advance one cycle.  Reads up/down, updates ``self.ctrl``."""
        # Algorithm operates on the true internal state
        self._step(up, down)

        if self._pipe is not None:
            self.ctrl = self._pipe[0]
            self._pipe.append(self._ctrl)
        else:
            self.ctrl = self._ctrl

    def _step(self, up: int, down: int) -> None:
        """Per-cycle algorithm — override in subclasses."""
        raise NotImplementedError

    # ---- reset ----

    def reset(self) -> None:
        """Reset ctrl and internal state to initial values."""
        self._ctrl = self._clamp(self.init_ctrl)
        self.ctrl = self._ctrl
        self._reset_state()
        # Re-init pipe if it was configured
        if self._pipe is not None:
            extra = self._pipe.maxlen
            self._pipe = deque([self._ctrl] * extra, maxlen=extra)

    def _reset_state(self) -> None:
        """Override in subclasses with extra state."""
        pass


class SaturateController(Controller):
    """Simple +/-1 saturating controller."""

    def __init__(self, ctrl_bits = 6, init_ctrl = 32, prop_delay_ps = 2593):
        super().__init__(ctrl_bits, init_ctrl, prop_delay_ps)

    def _step(self, up: int, down: int) -> None:
        if up and not down:
            if self._ctrl < self.max_ctrl:
                self._ctrl += 1
        elif down and not up:
            if self._ctrl > 0:
                self._ctrl -= 1


class FilteredController(Controller):
    """Requires FILTER_LEN consecutive same-direction requests."""

    def __init__(self, ctrl_bits: int = 6, init_ctrl: int = 32,
                 prop_delay_ps: float = 2786, filter_len: int = 4):
        super().__init__(ctrl_bits, init_ctrl, prop_delay_ps)
        self.filter_len = filter_len
        self._up_count = 0
        self._down_count = 0

    def _reset_state(self) -> None:
        self._up_count = 0
        self._down_count = 0

    def _step(self, up: int, down: int) -> None:
        fl = self.filter_len
        if up and not down:
            self._down_count = 0
            if self._up_count < fl:
                self._up_count += 1
            if self._up_count == fl:
                if self._ctrl < self.max_ctrl:
                    self._ctrl += 1
                self._up_count = 0
        elif down and not up:
            self._up_count = 0
            if self._down_count < fl:
                self._down_count += 1
            if self._down_count == fl:
                if self._ctrl > 0:
                    self._ctrl -= 1
                self._down_count = 0
        else:
            self._up_count = 0
            self._down_count = 0


class LockedController(Controller):
    """Acquire/track — large steps then small steps after quiet period."""

    def __init__(self, ctrl_bits: int = 6, init_ctrl: int = 32,
                 prop_delay_ps: float = 2578,
                 acquire_step: int = 4, track_step: int = 1,
                 quiet_cycles: int = 8):
        super().__init__(ctrl_bits, init_ctrl, prop_delay_ps)
        self.acquire_step = acquire_step
        self.track_step = track_step
        self.quiet_cycles = quiet_cycles
        self.mode: str = "acquire"
        self._quiet_count = 0

    def _reset_state(self) -> None:
        self.mode = "acquire"
        self._quiet_count = 0

    def _step(self, up: int, down: int) -> None:
        step = self.acquire_step if self.mode == "acquire" else self.track_step
        if up and not down:
            self._quiet_count = 0
            self._ctrl = min(self._ctrl + step, self.max_ctrl)
        elif down and not up:
            self._quiet_count = 0
            self._ctrl = max(self._ctrl - step, 0)
        else:
            if self._quiet_count < self.quiet_cycles:
                self._quiet_count += 1
        if self._quiet_count == self.quiet_cycles:
            self.mode = "track"


class VariableStepController(Controller):
    """Adaptive step size based on direction persistence."""

    def __init__(self, ctrl_bits: int = 6, init_ctrl: int = 32,
                 prop_delay_ps: float = 2652,
                 big_step: int = 4, med_step: int = 2,
                 big_thresh: int = 8, med_thresh: int = 4):
        super().__init__(ctrl_bits, init_ctrl, prop_delay_ps)
        self.big_step = big_step
        self.med_step = med_step
        self.big_thresh = big_thresh
        self.med_thresh = med_thresh
        self._same_dir_count = 0
        self._last_dir_up = False

    def _reset_state(self) -> None:
        self._same_dir_count = 0
        self._last_dir_up = False

    def _step(self, up: int, down: int) -> None:
        if up and not down:
            if self._last_dir_up:
                self._same_dir_count += 1
            else:
                self._same_dir_count = 1
                self._last_dir_up = True
            step = self._pick_step()
            self._ctrl = min(self._ctrl + step, self.max_ctrl)
        elif down and not up:
            if not self._last_dir_up:
                self._same_dir_count += 1
            else:
                self._same_dir_count = 1
                self._last_dir_up = False
            step = self._pick_step()
            self._ctrl = max(self._ctrl - step, 0)
        else:
            self._same_dir_count = 0

    def _pick_step(self) -> int:
        if self._same_dir_count >= self.big_thresh:
            return self.big_step
        if self._same_dir_count >= self.med_thresh:
            return self.med_step
        return 1
