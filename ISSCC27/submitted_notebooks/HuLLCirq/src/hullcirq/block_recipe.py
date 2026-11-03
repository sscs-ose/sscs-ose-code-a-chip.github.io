"""Exact execution-recipe dispatch, independent of the saved placement schema.

Fresh explicit block plans select the latest recipe. Historical validation and
downloads always select from the run's unchanged saved profile, never latest.
The v1 standalone runtime, launcher, profile and hashes remain immutable.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import json
from pathlib import Path

from .block_layout import (BLOCK_ARTIFACTS, VERSION, OPENROAD_COMMIT,
                           effective_configuration as v1_effective_configuration)
from .domain import DomainError


@dataclass(frozen=True)
class BlockRecipe:
    profile_version: str
    profile_file: str
    flow: str
    launcher: str
    runtime_module: str
    runtime_file: str
    flow_sha256: str
    runtime_sha256: str
    profile_sha256: str


V1 = BlockRecipe(
    "hullcirq-sky130-block-regions-v1", "physical_profile_sky130_block_regions_v1.json",
    "HuLLCirqBlockRegionsV1", "block_region_flow_v1.py", "block_layout", "block_layout.py",
    "b7685078c3860e3cbb160b43160f9268ef433959db0806e71a841123795d1c26",
    "cbf41fb6e4de3fc93a1076a258a309160da542f82f785b860a999c9702418208",
    "58fe80733ebc552f56244f0e20e52c4ceef9e0118959d79c57913f630edcafed")
V2 = BlockRecipe(
    "hullcirq-sky130-block-regions-v2", "physical_profile_sky130_block_regions_v2.json",
    "HuLLCirqBlockRegionsV2", "block_region_flow_v2.py", "block_layout_v2", "block_layout_v2.py",
    "7d61360fa6e6792f3d5c1939333946d97b1dc3676da2f934fb90573ceade2fda",
    "fe0f7c8e77f7b6c96ca4a401487a849d55f204978bb01959433807648b379632",
    "ba70063a272300aa5b0f0a502786086da3e905854789448d0ef1d1fd51bda2d9")
LATEST = V2
_RECIPES = {recipe.profile_version: recipe for recipe in (V1, V2)}


def recipe_for(configuration, required=False):
    """Resolve an allowlisted *saved* profile; unknown block recipes fail closed."""
    profile = configuration.get("profile") if type(configuration) is dict else None
    version = profile.get("profile_version") if type(profile) is dict else None
    recipe = _RECIPES.get(version) if type(version) is str else None
    if recipe is None and (required or type(version) is str and version.startswith("hullcirq-sky130-block-regions-")):
        raise DomainError("block_region_recipe_unsupported", "Use a supported, unchanged saved block-placement execution profile.")
    return recipe


def is_block_configuration(configuration):
    return recipe_for(configuration) is not None


def runtime_for(configuration):
    recipe = recipe_for(configuration, required=True)
    runtime = import_module("." + recipe.runtime_module, __package__)
    if (runtime.PROFILE_VERSION, runtime.FLOW, runtime.LAUNCHER, runtime.VERSION) != (
            recipe.profile_version, recipe.flow, recipe.launcher, VERSION):
        raise DomainError("block_region_recipe_changed", "The selected block-placement runtime does not match its fixed execution recipe.")
    return runtime


def source_input(configuration, manifest, top):
    return runtime_for(configuration).source_input(configuration, manifest, top)


def effective_configuration(configuration, design, root=None):
    """Project a current design for a NEW run, never reconstruct a saved run."""
    recipe_for(configuration)  # Do not silently relabel an unknown saved recipe.
    result = v1_effective_configuration(configuration, design, root)
    plan = design.get("physical_design")
    if result is not None and type(plan) is dict and plan.get("version") == VERSION:
        root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        result["profile"] = json.loads((root / "configs" / LATEST.profile_file).read_text(encoding="utf-8"))
    return result
