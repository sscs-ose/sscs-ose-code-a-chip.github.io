"""Minimal SKY130 OpenRAM macro used to qualify the local A2 toolchain."""

import os

word_size = int(os.environ.get("A2_OPENRAM_WORD_SIZE", "8"))
num_words = int(os.environ.get("A2_OPENRAM_NUM_WORDS", "16"))
# The default is a whole-word write. A2 may set this to 2 only for the
# differential run against OpenRAM's upstream tiny SKY130 configuration.
write_size = int(os.environ.get("A2_OPENRAM_WRITE_SIZE", "8"))

num_rw_ports = int(os.environ.get("A2_OPENRAM_NUM_RW_PORTS", "1"))
num_r_ports = int(os.environ.get("A2_OPENRAM_NUM_R_PORTS", "0"))
num_w_ports = int(os.environ.get("A2_OPENRAM_NUM_W_PORTS", "0"))

if os.environ.get("A2_OPENRAM_WORDS_PER_ROW"):
    words_per_row = int(os.environ["A2_OPENRAM_WORDS_PER_ROW"])

# SKY130's 1-port array requires an even physical column count once the
# replica bitline is included. One spare column makes 8 + 1 + 1 columns.
num_spare_cols = 1
num_spare_rows = 1

tech_name = "sky130"
# OpenRAM dev's custom-cell SKY130 path replaces the Cypress SRAM leaf cells
# that reproduce upstream issue #220 under the stable technology view.
tech_file = "tech_custom_cell"
nominal_corner_only = True

route_supplies = "ring"
# Verification is mandatory by default. A2 may set this to 0 only to emit
# artifacts for an independent backend check after a verifier failure.
check_lvsdrc = os.environ.get("A2_OPENRAM_VERIFY", "1") != "0"
uniquify = True

# A2 installs the open-source verification tools directly in WSL.
use_nix = False
drc_name = "magic"
lvs_name = "netgen"
pex_name = "magic"

output_name = os.environ.get("A2_OPENRAM_OUTPUT_NAME", "sky130_sram_1rw_8x16")
output_path = os.environ.get(
    "A2_OPENRAM_OUTPUT",
    "/opt/eda/openram-smoke/sky130_sram_1rw_8x16",
)
netlist_only = True
