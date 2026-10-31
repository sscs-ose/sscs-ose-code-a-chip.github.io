# SKY130 MOS models

This archive contains unchanged model files from the public SkyWater primitive
device library at commit `f62031a1be9aefe902d6d54cddd6f59b57627436`.
The source repository is https://github.com/google/skywater-pdk-libs-sky130_fd_pr.

The four device families are the standard and low threshold 1.8 V NFET and PFET.
TT, SS, FF, SF and FS corner data are included. The source manifest records the
original path, URL and SHA256 of every file. The original Apache License 2.0
and copyright notices are retained.

The simulation runner checks and extracts the archive into its work directory,
then writes a library wrapper using local absolute paths. It does not change the
electrical parameters. Width and length are expressed in micrometers with
`scale=1e-6`. This subset supplies transistor models for circuit simulation.
It does not contain layout rules or extraction technology files.
