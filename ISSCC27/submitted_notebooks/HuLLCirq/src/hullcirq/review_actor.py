"""Versioned, self-declared review operator identity; never infer a human.

This is provenance, not authentication or authorization. Historical unversioned
human labels remain historical evidence and are never upgraded retrospectively.
Automatic policy decisions use their existing separately authorized proof.
"""
from .domain import DomainError

VERSION = "hullcirq.review-actor.v1"
MANUAL_ACTORS = ("human", "development_assistant", "unspecified")
REVIEW_ACTORS = (*MANUAL_ACTORS, "automation_policy")


def manual_review_fields(operator=None):
    if operator is None:
        actor = "unspecified"
    elif (type(operator) is dict and set(operator) == {"actor"}
          and type(operator["actor"]) is str
          and operator["actor"] in ("human", "development_assistant")):
        actor = operator["actor"]
    else:
        raise DomainError("invalid_review_operator", "Declare a human or development-assistant review operator. Automatic policy cannot be selected for an explicit review.")
    return {"actor": actor,
            "provenance": {"version": VERSION, "actor": actor,
                           "declaration": "not_declared" if actor == "unspecified" else "self_reported"}}


def validate_review_actor(record):
    """Validate new declarations while admitting original legacy records intact."""
    provenance = record.get("provenance")
    if type(provenance) is not dict or "version" not in provenance:
        if record.get("actor") not in ("human", "automation_policy"):
            raise DomainError("invalid_store", "Unversioned review operator provenance is invalid.")
        return
    actor = record.get("actor")
    expected = {"version": VERSION, "actor": actor, "declaration": "not_declared" if actor == "unspecified" else "self_reported"}
    if actor not in MANUAL_ACTORS or provenance != expected:
        raise DomainError("invalid_store", "Versioned review operator provenance is invalid.")
