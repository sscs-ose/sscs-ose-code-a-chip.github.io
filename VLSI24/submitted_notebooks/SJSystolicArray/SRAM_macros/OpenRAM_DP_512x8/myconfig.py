
"""
Dual port (1 read/write + 1 read only) 1 kbytes SRAM with byte write.
"""
word_size = 8

num_words = 512

human_byte_size = "{:.0f}kbytes".format((word_size * num_words)/1024/8)

# Allow byte writes
write_size = 8

# Dual port
num_rw_ports = 2
num_r_ports = 0
num_w_ports = 0
ports_human = '1rw1r'

import os
exec(open(os.path.join(os.path.dirname(__file__), 'sky130_sram_common.py')).read())
