#!/usr/bin/env bash

set -e

mkdir -p results/build

iverilog -g2012 -s cpu_tb -o results/build/simv rtl/*.sv tb/top_tb.sv

vvp results/build/simv