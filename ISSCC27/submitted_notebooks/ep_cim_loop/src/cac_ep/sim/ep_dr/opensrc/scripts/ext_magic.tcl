# Magic 추출 (LVS 용 SPICE) — 블록 하나. lvs_netgen.sh 가 부른다 (환경 GDS·TOP·OUT).
set gds $::env(GDS); set top $::env(TOP); set out $::env(OUT)
gds read $gds
load $top
select top cell
port makeall
extract path [file dirname $out]
extract do local
extract all
ext2spice lvs
ext2spice -o $out $top
quit -noprompt
