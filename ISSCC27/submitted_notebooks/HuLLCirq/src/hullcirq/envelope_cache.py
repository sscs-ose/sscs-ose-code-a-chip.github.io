"""Memoize manager read views for one project-envelope call only.

Context-local state is discarded on return or exception. Workers, mutation
actions and direct manager calls outside that scope never use this cache.
The store and individual source-record getters deliberately remain uncached.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_READ_CACHE: ContextVar[dict | None] = ContextVar("hullcirq_project_envelope_read_cache", default=None)
_MISSING = object()


@contextmanager
def read_scope():
    token = _READ_CACHE.set({})
    try:
        yield
    finally:
        _READ_CACHE.reset(token)


def envelope_read_scope(function):
    """Wrap the complete project view, never its enclosing request/action."""
    @wraps(function)
    def scoped(*args, **kwargs):
        with read_scope():
            return function(*args, **kwargs)
    return scoped


def memoized_envelope(function):
    """Share a no-argument manager envelope among its read-only consumers."""
    @wraps(function)
    def read(self):
        cache = _READ_CACHE.get()
        if cache is None:
            return function(self)
        key = (self, function)
        value = cache.get(key, _MISSING)
        if value is _MISSING:
            value = function(self)
            cache[key] = value
        return value
    return read
