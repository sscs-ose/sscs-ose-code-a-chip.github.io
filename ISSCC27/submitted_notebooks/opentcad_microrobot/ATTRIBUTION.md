# Attribution, licensing and disclosed IP

SPDX-License-Identifier: Apache-2.0

Original OpenTCAD code and notebook text are licensed under the repository's
Apache-2.0 license. This project is a functional reimplementation and educational
research workflow, not a reproduction of the authors' proprietary X-FAB layout,
process models or measured performance. No prior team's notebook was reused.

The historical repository samples in `data/s2e_digitized.csv` were digitized from Fig. S2E
of the supplementary materials to Reynolds et al., *Microscopic robots with
onboard digital control*, Science Robotics 7, eabq2296 (2022),
https://doi.org/10.1126/scirobotics.abq2296. The supplement's checksum, raster
coordinates and extraction assumptions are in `data/s2e_calibration.json` and
`data/README.md`. These are approximate figure-derived samples, not original
raw measurement files. Attribution and the project's code license do not grant
rights in the paper or its figures. Source PDFs and rendered paper images are
not included in the submission bundle. The curated front-notebook export also
omits the figure-derived CSV and does not use a published-data fit; its PV
input is the project's conceptual drift-diffusion calculation.

On 2026-10-30 the project author supplied six measurement CSVs in a local
`Reynolds-2022-data` directory and identified them as the Zenodo data for
Reynolds et al. The download URL, repository metadata and data license were
not included, so the claimed Zenodo provenance has not been independently
verified. Exact supplied-file hashes and figure mappings are recorded in
[the dataset audit](data/reynolds2022_AUDIT.md) and
[inventory](data/reynolds2022_inventory.json). These measurement files
are distinct from my figure digitization and from my simulations. They
remain outside the checkout and are not redistributed in the submission
export. The repository's Apache-2.0 code license is not a license declaration
for these external data. The application records its own unit conversions,
processing choices and comparison results separately; the original files
are preserved unchanged.

The paper's Competing Interests section (p. 10) discloses applications
PCT/US2021/021419, 63/267,190 and 63/368,751 relating to actuators and/or
microrobot control electronics. This is a record of the publication's disclosure,
not an assessment of current patent status, claim scope, validity or freedom to
operate. This project makes no representation that an open-source code license
clears third-party patent rights. It is not a fabrication authorization.

Credit for microrobot architectures and actuator physics belongs to Reynolds
et al., Miskin et al., and the other cited authors; see `references.md`. The
additional Xu ISSCC 2022 reference is a separate architecture. Semiconductor
models and software remain attributed to the DEVSIM, Gmsh, NumPy/SciPy, PyVista,
SKY130/open_pdks, ngspice, Magic, Netgen, Icarus Verilog and Yosys projects.
Their licenses are separate. Imported SKY130 standard-cell SPICE includes its
upstream attribution; the PDK itself is not bundled.
