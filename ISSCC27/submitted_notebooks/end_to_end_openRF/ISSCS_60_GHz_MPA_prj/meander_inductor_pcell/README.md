# Meander Inductor PCell
This folder holds the files that define and integrate the meander inductor PCell into the IHP-Open-PDK.

The original polygon data generation was done with the script `meander_inductor_polygon_generator.md`. The actual integration is held in `snake_inductor_code.py`, which goes in the directory `ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/snake_inductor_code.py`. Also, to include the PCell into the library, the `__init__.py` in `ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/__init__.py` was modified accordingly.