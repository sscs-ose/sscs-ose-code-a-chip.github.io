"""Compare retained revisions without rebinding immutable circuit evidence.

Only graph-editor presentation and the display name are non-semantic. The
comparison deliberately uses the strict evidence hash, not revision_hashes'
numeric normalization: an integer and a float must remain distinct here.
"""
from .domain import DomainError, semantic_design
from .verification import object_hash


def same_source_design(store, source_revision_id, current=None):
    """Return the original snapshot only when it matches the current circuit.

    This does not grant adoption or revive an earlier source epoch. Callers
    still enforce their exact source IDs, latest reviews and adoption epochs.
    Missing snapshots fail closed through the store's existing lookup.
    """
    current = store.envelope() if current is None else current
    snapshot = store.snapshot(source_revision_id)
    if object_hash(semantic_design(snapshot)) != object_hash(semantic_design(current["design"])):
        raise DomainError("source_revision_conflict", "The original source revision does not match the current semantic design.")
    return snapshot


def same_revision_design(store, first_revision_id, second_revision_id):
    """Compare two retained snapshots; never substitutes the current design."""
    return object_hash(semantic_design(store.snapshot(first_revision_id))) == object_hash(
        semantic_design(store.snapshot(second_revision_id)))
