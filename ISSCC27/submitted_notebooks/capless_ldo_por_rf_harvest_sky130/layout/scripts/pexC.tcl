cd /w/mag/pexrun
load ldo_top
select top cell
extract do capacitance
extract do coupling
extract no resistance
extract all
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice format ngspice
ext2spice hierarchy on
ext2spice -o ldo_top_pexC.spice
quit -noprompt
