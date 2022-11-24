#!/bin/bash

set -ex


# Get the binaries if they aren't downloaded
# ##########################################

if [ ! -f "./mm/micromamba" ];
then
  ./scripts/download_micromamba.sh;
fi

# Initialize Python Environment
# #############################

source scripts/micromamba_env.sh


# Download all the dependencies
###############################

export OPENFASOC_ROOT="${PWD}/OpenFASOC"
export PDK_ROOT="${MAMBA_ROOT_PREFIX}/share/pdk"

micromamba install -y -f dependencies/deps_0.yml
micromamba install -y -f dependencies/deps_1.yml
micromamba install -y -f dependencies/deps_2.yml


#dependencies/deps_klayout.sh
#dependencies/deps_openfasoc.sh

jupyter-notebook --no-browser
