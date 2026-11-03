#!/bin/bash
# MNIST 원자료 (idx) 를 공개 사본에서 받는다. 쓰임: bash get_mnist.sh <폴더>   → <폴더>/{train,t10k}-{images-idx3,labels-idx1}-ubyte
set -eu
D=$(mkdir -p "$1" && cd "$1" && pwd)
U=https://ossci-datasets.s3.amazonaws.com/mnist        # torchvision 이 쓰는 사본
for f in train-images-idx3-ubyte train-labels-idx1-ubyte t10k-images-idx3-ubyte t10k-labels-idx1-ubyte; do
  [ -s "$D/$f" ] || { curl -fsSL "$U/$f.gz" | gunzip > "$D/$f"; }
done
md5sum "$D"/* 2>/dev/null || ls -la "$D"
