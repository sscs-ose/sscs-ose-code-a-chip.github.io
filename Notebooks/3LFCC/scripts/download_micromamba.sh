#!/bin/bash

ARCH=$(uname -m)
OS=$(uname)

if [[ "$OS" == "Linux" ]]; then
	PLATFORM="linux"
	if [[ "$ARCH" == "aarch64" ]]; then
		ARCH="aarch64";
	elif [[ $ARCH == "ppc64le" ]]; then
		ARCH="ppc64le";
	else
		ARCH="64";
	fi		
fi

if [[ "$OS" == "Darwin" ]]; then
	PLATFORM="osx";
	if [[ "$ARCH" == "arm64" ]]; then
		ARCH="arm64";
	else
		ARCH="64"
	fi
fi

mkdir -p mm

curl -Ls https://micro.mamba.pm/api/micromamba/$PLATFORM-$ARCH/latest | tar -xvj -C ./mm --strip-components=1 bin/micromamba

# if [ -t 0 ] ; then
# 	printf "Init shell? [Y/n] "
# 	read YES
# 	printf "Prefix location? [~/micromamba] "
# 	read PREFIXLOCATION
# else
# 	YES="yes";
# 	PREFIXLOCATION="~/micromamba"
# fi

# if [[ "$PREFIXLOCATION" == "" ]]; then
# 	PREFIXLOCATION="~/micromamba"
# fi

# if [[ "$YES" == "" || "$YES" == "y" || "$YES" == "Y" || "$YES" == "yes" ]]; then
# 	~/.local/bin/micromamba shell init -p $PREFIXLOCATION
# fi