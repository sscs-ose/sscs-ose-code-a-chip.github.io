#!/usr/bin/env python3
"""Explain broker-only operations inside ordinary shell commands."""
import sys

print("capacity-check is available through the controlled tool broker. "
      "Run exactly one standalone command in a separate tool call: "
      "capacity-check status, capacity-check integration, capacity-check synth, "
      "or capacity-check physical. Do not combine it with cd, &&, pipes or other shell commands.",
      file=sys.stderr)
raise SystemExit(2)
