cd /w/mag
load ldo_top
select top cell
extract do local
extract no capacitance
extract no coupling
extract all
ext2spice lvs
ext2spice -o ldo_top_lvs.spice
quit -noprompt
