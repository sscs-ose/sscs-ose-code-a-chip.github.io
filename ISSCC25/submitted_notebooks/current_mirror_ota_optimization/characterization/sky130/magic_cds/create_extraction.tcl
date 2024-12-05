gds read ./extraction_custom/CURRENT_MIRROR_OTA_0.gds
load current_mirror_ota
extract all
select top cell
port makeall
ext2spice lvs
ext2spice cthresh 0.1 rthresh 0.1
ext2spice subcircuit on
ext2spice ngspice
ext2spice CURRENT_MIRROR_OTA_0.spice
