# Magic 기생 추출 (C coupling + extresist R 망) → 평면 SPICE. 환경 GDS·TOP·OUTD.
set gds $::env(GDS); set top $::env(TOP); set outd $::env(OUTD)
gds read $gds
load $top
select top cell
port makeall
extract path $outd
extract do local
extract do capacitance
extract do coupling
extract do resistance
extract do adjust
extract all
puts "PEX_STAGE ext_done [clock seconds]"
ext2sim labels on
ext2sim -p $outd
extresist tolerance 10
extresist all
puts "PEX_STAGE extresist_done [clock seconds]"
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice extresist on
ext2spice -p $outd -o $outd/$top.magic_pex.spice $top
puts "PEX_STAGE ext2spice_done [clock seconds]"
quit -noprompt
