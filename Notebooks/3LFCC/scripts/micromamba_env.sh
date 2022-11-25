#!/bin/bash


# Set required enviroment variables
# #################################

export MAMBA_ROOT_PREFIX="$PWD/mm";
export MAMBA_EXE="$MAMBA_ROOT_PREFIX/micromamba";

if [ -f "$MAMBA_EXE" ]
then
	echo "micromamba existe";
else
	echo "micromamba no existe";
	./scripts/download_micromamba.sh
fi

__shell="$(basename $SHELL)"

eval "$($MAMBA_EXE shell hook --shell $__shell )"

micromamba activate
