#!/bin/sh

set -e

wgetcmd="wget"
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

coinasl=solvers-20180528

echo " "
echo "Running script for downloading the source code for the ASL"
echo " "

rm -f $coinasl

echo "Downloading the source code from www.coin-or.org..."
if $wgetcmd https://www.coin-or.org/BuildTools/ASL/${coinasl}.tgz ;
then
  echo "Download finished."
else
  echo
  echo "Downloading from COIN-OR failed, trying ampl.com..."
  if $wgetcmd https://ampl.com/netlib/ampl/solvers.tgz ;
  then
    echo "Download finished."
    mv solvers.tgz ${coinasl}.tgz
  else
    echo "Download failed...exiting"
  fi
fi

rm -rf solvers

echo "Unpacking the source code..."
gunzip -f ${coinasl}.tgz
tar xf $coinasl.tar

echo "Adding No_dtoa to CFLAGS..."
cd solvers
mv makefile.u makefile.u.orig
sed -e 's/CFLAGS = /CFLAGS = -DNo_dtoa /g' makefile.u.orig > makefile.u 
cd ..

echo "Applying path for MinGW"
patch -p0 <mingw.patch

echo "Deleting the tar file..."
rm $coinasl.tar

echo " "
echo "Done downloading the source code for ASL."
echo " "

