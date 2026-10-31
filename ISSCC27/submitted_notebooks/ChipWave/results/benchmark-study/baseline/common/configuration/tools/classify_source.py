#!/usr/bin/env python3
"""Classify the explicit case input; no generated RTL or experimental verdict."""
import json
print("NEBULA_OUTPUT: "+json.dumps({"analysis":{
    "document_kind":"detailed_design",
    "classification_summary":"Immutable CPU/NPU detailed design contains base ISA, interface, custom instruction, timing and physical boundaries."
}}))
