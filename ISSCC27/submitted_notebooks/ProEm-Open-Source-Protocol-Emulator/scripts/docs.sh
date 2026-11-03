#!/bin/bash
# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: scripts/docs.sh
# Type: Script: build every PDF in docs/ from its LaTeX source in docs/latex/
# Author: Paul Vincent Bezzina
# Language: Bash
# Description:
# =============================================================================
set -e
cd "$(dirname "$0")/../docs/latex"
OUT=../../build/docs
mkdir -p $OUT
for f in ${@:-*.tex}; do
  name=$(basename "${f%.tex}")
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory $OUT $name.tex > /dev/null
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory $OUT $name.tex > /dev/null
  cp $OUT/$name.pdf ../$name.pdf
  echo "built docs/$name.pdf"
done
