"""Automated SPICE execution and receipt validation."""
from .parser import parse_measurements, validate_measurements
from .runner import run_stage4_manifest
__all__ = ["parse_measurements", "validate_measurements", "run_stage4_manifest"]