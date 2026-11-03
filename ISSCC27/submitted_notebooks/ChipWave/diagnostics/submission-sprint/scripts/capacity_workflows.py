"""Frozen phase and context assignments, consumed by the existing dispatcher."""
from capacity_protocol import WORKFLOWS

PHASES = ("implementation", "verification", "integration_ppa", "revision")
CHECKLISTS = dict(
    implementation="Implement the frozen workload and interface, including reset, cancel/flush and backpressure.",
    verification="Check arithmetic/data integrity, ordering, bounds, fairness and progress; record reproducible failures.",
    integration_ppa="Run integration checks; inspect synthesis and physical reports; diagnose timing, power and routing.",
    revision="Repair evidence-backed defects without weakening contracts; select and explicitly submit matching artifacts.")


def configuration(workflow):
    if workflow not in WORKFLOWS:
        raise ValueError("Unknown workflow")
    if workflow in ("C0", "C1"):
        sequence = [("autonomous", "engineer")]
    elif workflow == "C2":
        sequence = [(phase, "engineer") for phase in PHASES]
    elif workflow == "C3":
        sequence = list(zip(PHASES, ("rtl", "verification", "integration_ppa", "rtl")))
    else:
        sequence = [("architecture", "architecture"), ("implementation", "rtl"),
                    ("verification", "verification"), ("integration", "integration"),
                    ("timing", "timing"), ("power", "power"), ("revision", "rtl")]
    return dict(workflow=workflow, orchestration="native" if workflow == "C0" else "chipnebula",
                phases=[dict(phase=phase, context=role) for phase, role in sequence],
                context_policy="resume same context for same role; never share across trials",
                repair_context="engineer" if workflow in ("C0", "C1", "C2") else "rtl",
                expert_materials=CHECKLISTS, role_calls_parallel=False,
                physical_feedback="same raw reports for every workflow; at most two attempts",
                status="declaration; runtime execution still requires qualification")


def repair_context(workflow, physical_attempts):
    if type(physical_attempts) is not int or physical_attempts not in (0, 1, 2):
        raise ValueError("Invalid physical attempt count")
    # A second physical result never authorizes a third physical launch.
    return dict(context=configuration(workflow)["repair_context"],
                physical_retry_allowed=physical_attempts < 2)
