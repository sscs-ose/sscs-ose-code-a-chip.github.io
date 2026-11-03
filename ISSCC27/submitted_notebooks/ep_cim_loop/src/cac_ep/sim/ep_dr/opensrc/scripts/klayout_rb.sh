#!/bin/bash
# Ruby 가 있는 KLayout (공식 RPM 0.30.2 CentOS 8 판, ~/opt/klayout_dl 에 풀어 둠) 을 부른다. conda-forge klayout 0.30.12 는 Ruby 없이 빌드돼
# DRC 덱 (.drc = Ruby DSL) 을 못 돌린다 ("Can't run macro (no interpreter)"). 의존 RPM (Rocky 8: ruby-libs 2.5.9·rubygems·libgit2 0.26·qt5 multimedia/
# xmlpatterns/designer·pulseaudio-libs·libsndfile 등) 은 ~/opt/klayout_dl/deps 에 rpm2cpio 로 풀었다 (sudo 없음). 목록은 README.
K=${KLAYOUT_HOME:-$HOME/opt/klayout_dl}; D=$K/deps
export LD_LIBRARY_PATH=$K/usr/lib64/klayout:$D/usr/lib64:$D/usr/lib64/pulseaudio${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export RUBYLIB=$D/usr/share/rubygems:$D/usr/share/ruby:$D/usr/lib64/ruby
exec "$K/usr/bin/klayout" "$@"
