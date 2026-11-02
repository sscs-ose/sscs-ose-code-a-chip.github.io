#!/bin/sh
# Full flow: device cells -> placement/routing -> DRC/LVS -> C extraction -> post-layout and bandgap simulations.
cd "$(dirname "$0")"
RC=/opt/pdk/sky130A/libs.tech/magic/sky130A.magicrc
rm -f mag/sky130*.mag mag/gencells.mag
sh run.sh python layout.py gen
sh run.sh bash -c "cd /w/mag && magic -dnull -noconsole -rcfile $RC gencells.tcl > gencells.log 2>&1"
sh run.sh python layout.py place | grep -E "self-check|rows"
sh verify.sh | tee verify.log
rm -rf mag/pexrun_prev; [ -d mag/pexrun ] && mv mag/pexrun mag/pexrun_prev
mkdir -p mag/pexrun && cp mag/pexC.tcl mag/pexrun/
for f in mag/*.mag; do case $(basename $f) in iso_*|t_*|gencells.mag) ;; *) cp "$f" mag/pexrun/;; esac; done
sh run.sh bash -c "cd /w/mag/pexrun && magic -dnull -noconsole -rcfile $RC pexC.tcl > pexC.log 2>&1"
echo "PEX capacitors: $(grep -c '^C' mag/pexrun/ldo_top_pexC.spice)"
sh run.sh bash -c '
python postlayout.py pex pvt 16 > pl_pex_pvt.log 2>&1
python por_check.py pex 15 > pl_por_pex.log 2>&1
python postlayout.py pex tt > pl_pex_tt.log 2>&1
python bgr_slow.py > bgr_slow.log 2>&1
python bgr_pvt.py > bgr_pvt.log 2>&1
python bgr_mc.py 200 > bgr_mc.log 2>&1
python bgr_trim_mc.py 100 > bgr_trim_mc.log 2>&1
python bgr_psrr.py > bgr_psrr.log 2>&1'
tail -1 pl_pex_pvt.log; tail -1 pl_por_pex.log; cat pl_pex_tt.log bgr_slow.log; tail -1 bgr_pvt.log; tail -1 bgr_mc.log; tail -1 bgr_trim_mc.log; cat bgr_psrr.log
