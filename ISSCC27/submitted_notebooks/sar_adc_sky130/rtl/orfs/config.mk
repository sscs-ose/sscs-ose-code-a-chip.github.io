# SPDX-License-Identifier: Apache-2.0
export DESIGN_NAME = sar_sequencer
export PLATFORM    = sky130hd

export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/sar_sequencer.v
export SDC_FILE      = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

# Sweep knobs. Defaults are deliberately unaggressive -- this is the baseline a
# design-space search starts FROM, not a tuned result.
export CORE_UTILIZATION  ?= 40
export PLACE_DENSITY     ?= 0.60
export TNS_END_PERCENT   ?= 100
