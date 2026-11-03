"""Fixed Task topology and continuing Attempt execution kernel.

Artifact identifiers are immutable retrieval/audit references. Scheduling is
driven only by Task work, output-slot dependencies, release conditions and
human/engineering gates. Runtime feedback changes WorkItems and Attempts; it
never expands or rewrites the Task topology.
"""

from .artifacts import (
    ArtifactSchema, ArtifactSchemaRegistry, ArtifactValidationError,
    default_schema_registry, load_schema_file, load_schema_registry,
    schema_from_document,
)
from .domain import (
    Artifact, ArtifactContent, ArtifactProducer, Attempt, AttemptStatus,
    Delivery, Dependency, DomainError, GateSpec, InitialInput,
    JointAnalysisGroup, OutputSpec, PermissionGrant, RecoverableSite,
    ReleaseCondition, Role, Task, TaskBrief, TaskExecutor, TaskState, Workflow,
    WorkflowStatus, WorkItem, WorkItemKind, WorkItemStatus, WorkRequest,
)
from .static_recipe import (
    CompiledStaticRecipe, FeedbackRoute, PlannerConfig, StaticRecipeCompiler,
    StaticRecipeError, load_project_static_roles, load_static_recipe,
    load_static_role,
)
from .static_store import StateConflict, StaticTaskGraphStore
from .attempt_scheduler import AttemptScheduler
from .attempt_runtime import AttemptRuntime, AttemptRuntimeResult
from .attempt_workspace import AttemptWorkspaceFactory
from .context import AttemptContextAssembler
from .planner import PlanningError, TaskBriefPlanner, build_planning_prompt, parse_briefs
from .work_handler import StaticWorkHandler
from .gate_templates import (
    GateParameter, GateTemplate, GateTemplateError, GateTemplateRegistry,
    default_gate_template_registry,
)

# Canonical names intentionally omit "static": every Workflow has a fixed Task
# topology in the current model.
TaskGraphStore = StaticTaskGraphStore
RecipeCompiler = StaticRecipeCompiler
RecipeValidationError = StaticRecipeError
CompiledRecipe = CompiledStaticRecipe
WorkHandler = StaticWorkHandler
load_recipe = load_static_recipe
load_role = load_static_role
load_project_roles = load_project_static_roles

__all__ = [name for name in globals() if not name.startswith("_")]
