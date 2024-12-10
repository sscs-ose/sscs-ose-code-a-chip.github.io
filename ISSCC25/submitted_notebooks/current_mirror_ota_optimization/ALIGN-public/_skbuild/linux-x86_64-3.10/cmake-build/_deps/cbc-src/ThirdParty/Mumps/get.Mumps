#!/bin/sh

# Set the following to the latest MUMPS version.
#  THERE MUST BE NO SPACE BEFORE AND AFTER THE EQUAL (=) OPERATOR.
mumps_ver=4.10.0

set -e

wgetcmd=wget
wgetcount=`which wget 2>/dev/null | wc -l`
if test ! $wgetcount = 1; then
  echo "Utility wget not found in your PATH."
  if test `uname` = Darwin; then
    wgetcmd="curl -L -O"
    echo "Using curl instead."
  elif test `uname` = FreeBSD; then
    wgetcmd=fetch
    echo "Using fetch instead."
  else
    exit -1
  fi
fi

echo " "
echo "Running script for downloading the source code for MUMPS"
echo " "

rm -f MUMPS*.tgz

echo "Downloading the source code from coin-or-tools.github.io..."
if $wgetcmd http://coin-or-tools.github.io/ThirdParty-Mumps/MUMPS_${mumps_ver}.tar.gz ;
then
  echo "Download finished."
else
  echo
  echo "Downloading from GitHub failed, trying mumps.enseeiht.fr..."
  if $wgetcmd http://mumps.enseeiht.fr/MUMPS_${mumps_ver}.tar.gz ;
  then
    echo "Download finished."
  else
    echo "Download failed...exiting"
  fi
fi

echo "Uncompressing the tarball..."
gunzip -f MUMPS_${mumps_ver}.tar.gz

echo "Unpacking the source code..."
tar xf MUMPS_${mumps_ver}.tar

echo "Deleting the tar file..."
rm MUMPS_${mumps_ver}.tar

rm -rf MUMPS
mv MUMPS_${mumps_ver} MUMPS

echo " "
echo "Done downloading the source code for MUMPS."
echo " "
echo "Apply a patch to work around a bug in MUMPS."
echo " "

patch -p0 < mumps.patch
patch -p0 < mumps_mpi.patch
mv MUMPS/libseq/mpi.h MUMPS/libseq/mumps_mpi.h

echo " "
echo "Verify that there are no error message in the output above."
