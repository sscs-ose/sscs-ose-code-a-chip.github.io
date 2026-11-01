"""Request-local source observations, without editing durable execution history.

GETs still evaluate live source/proof guards. Their derived input/adoption
epochs are isolated from the authoritative manager state and are discarded on
return, including error responses. Explicit actions and workers never enter
this scope and retain the existing durable observation path.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
from contextvars import ContextVar

from .domain import DomainError


_READ_OBSERVATIONS: ContextVar[dict | None] = ContextVar("hullcirq_read_observations", default=None)
_OBSERVED_FIELDS = frozenset(("source_key", "source_epoch", "source_transitions",
                              "node_inputs", "node_epochs", "current_design_hash"))


@contextmanager
def readonly_observation_scope():
    """Share one ephemeral observation graph through nested GET consumers."""
    if _READ_OBSERVATIONS.get() is not None:
        yield
        return
    token = _READ_OBSERVATIONS.set({})
    try:
        yield
    finally:
        _READ_OBSERVATIONS.reset(token)


def require_durable_write():
    """Fail closed if a non-observer persistence path is reached by a GET."""
    if _READ_OBSERVATIONS.get() is not None:
        raise DomainError("read_only_observation_violation",
                          "Viewing a saved result cannot write execution history.", 500)


def persist_observation(manager):
    """Only an explicit action/worker may durably checkpoint source epochs."""
    if _READ_OBSERVATIONS.get() is None:
        manager._persist()


class ObservedState:
    """Redirect source metadata only; never swap shared manager state.

    Histories are shared immutable inputs to GET guards. Only the small fields
    that observers can modify are copied, not prompts, RTL or tool evidence.
    Every durable writer is guarded separately, before modifying checksums.
    """
    @property
    def _state(self):
        observations = _READ_OBSERVATIONS.get()
        if observations is None:
            return self.__dict__["_durable_observation_state"]
        if self not in observations:
            with self.lock:
                durable = self.__dict__["_durable_observation_state"]
                projected = dict(durable)
                for field in _OBSERVED_FIELDS & durable.keys():
                    projected[field] = copy.deepcopy(durable[field])
                observations[self] = projected
        return observations[self]

    @_state.setter
    def _state(self, value):
        require_durable_write()
        self.__dict__["_durable_observation_state"] = value
