#!/bin/bash
# Olympus (RHEL 8.10, x86_64, sudo 없음) 에 오픈소스 signoff 도구를 사용자 공간에 까는 순서 — 10/28 에 실제로 친 명령을 모은 것.
# 이미 깔려 있으면 다시 돌릴 필요 없음. 걸린 시간: ① 192 s, ② 약 1 분 (내려받기 + 풀기), ③ 수 초.
set -eu

# ① conda 환경 ~/opt/oss_eda (3.3 GB): KLayout 0.30.12 (Python 전용, Ruby 없음 → DRC 덱 못 돌림), Yosys 0.69, Magic 8.3.678, Verilator 5.052
cd ~/cac && MAMBA_ROOT_PREFIX=~/cac/mamba ./bin/micromamba create -y -p ~/opt/oss_eda -c conda-forge \
  klayout=0.30.12 yosys=0.69 magic=8.3.678 verilator
#    Netgen (LVS) 은 이미 있던 ~/cac/env 의 litex-hub netgen 1.5.272 를 씀 (conda-forge 의 'netgen' 6.2 는 이름만 같은 mesh 생성기).
#    ngspice 47 은 ~/opt/ngspice-47 (10/25 직접 빌드), Icarus 13.0 은 ~/cac/env.

# ② Ruby 가 있는 KLayout: 공식 RPM klayout-0.30.2-0.x86_64.rpm (CentOS 8 판) 은 ~/opt/klayout_dl/usr 에 이미 풀려 있었다.
#    모자란 .so 를 Rocky 8 AppStream 에서 받아 rpm2cpio 로 ~/opt/klayout_dl/deps 에 푼다 (설치 아님).
D=~/opt/klayout_dl/deps; mkdir -p $D/rpm; cd $D/rpm
A=https://dl.rockylinux.org/pub/rocky/8/AppStream/x86_64/os/Packages
for p in r/ruby-libs-2.5.9-116.module%2Bel8.10.0%2B40366%2B397889f9.x86_64.rpm \
         r/rubygems-2.7.6.3-116.module%2Bel8.10.0%2B40366%2B397889f9.noarch.rpm \
         l/libgit2-0.26.8-3.el8.x86_64.rpm h/http-parser-2.8.0-9.el8.x86_64.rpm \
         q/qt5-qtmultimedia-5.15.3-1.el8.x86_64.rpm q/qt5-qtxmlpatterns-5.15.3-1.el8.x86_64.rpm \
         q/qt5-qttools-libs-designer-5.15.3-6.el8.x86_64.rpm \
         p/pulseaudio-libs-14.0-4.el8.x86_64.rpm p/pulseaudio-libs-glib2-14.0-4.el8.x86_64.rpm \
         l/libsndfile-1.0.28-17.el8_10.x86_64.rpm l/libasyncns-0.8-14.el8.x86_64.rpm l/libogg-1.3.2-10.el8.x86_64.rpm \
         l/libvorbis-1.3.6-2.el8.x86_64.rpm f/flac-libs-1.3.2-11.el8.x86_64.rpm g/gsm-1.0.17-5.el8.x86_64.rpm; do
  curl -sSfLO $A/$p
done
cd $D && for f in rpm/*.rpm; do rpm2cpio $f | cpio -idm --quiet; done
#    부르기: opensrc/scripts/klayout_rb.sh (LD_LIBRARY_PATH·RUBYLIB 를 맞춤).  확인: klayout_rb.sh -b -v → "KLayout 0.30.2"

# ③ open_pdks sky130A (volare c6d73a35) 의 libs.tech 중 magic·netgen·klayout(drc·lvs·tech) 만 로컬에서 올림 (12 MB)
#    로컬: rsync -a ~/pdk/volare/sky130A/libs.tech/{magic,netgen} olympus:work/ep_dr/opensrc/pdk/sky130A/libs.tech/
#          rsync -a ~/pdk/volare/sky130A/libs.tech/klayout/{drc,lvs,tech} olympus:work/ep_dr/opensrc/pdk/sky130A/libs.tech/klayout/
#    RRAM 추출 tech 사본: python3 scripts/make_magic_rram_tech.py ~/pdk/volare/sky130A/libs.tech/magic/sky130A.tech tech/sky130A_rram.tech
