# Copyright (C) 2006 International Business Machines.
# All Rights Reserved.
# This file is distributed under the Eclipse Public License.

## $Id: configure.ac 1532 2020-01-31 11:11:15Z stefan $

# Author:  Andreas Waechter            IBM    2006-04-13

#############################################################################
#                       Names and other basic things                        #
#############################################################################

AC_PREREQ(2.59)

AC_INIT([Cgl],[0.60.3],[cgl@list.coin-or.org])

AC_COPYRIGHT([
Copyright 2006 International Business Machines and others.
All Rights Reserved.
This file is part of the open source package Coin which is distributed
under the Eclipse Public License.])

# List one file in the package so that the configure script can test
# whether the package is actually there
AC_CONFIG_SRCDIR(src/CglMessage.hpp)

# Where should everything be installed by default?  Here, we want it
# to be installed directly in 'bin', 'lib', 'include' subdirectories
# of the directory where configure is run.  The default would be
# /usr/local.
AC_PREFIX_DEFAULT([`pwd`])

#############################################################################
#                         Standard build tool stuff                         #
#############################################################################

# Get the system type
AC_CANONICAL_BUILD

# If this project depends on external projects, the Externals file in
# the source root directory contains definition of where to find those
# externals.  The following macro ensures that those externals are
# retrieved by svn if they are not there yet.
AC_COIN_PROJECTDIR_INIT(Cgl,11:3:10)

# Check if user wants to produce debugging code
AC_COIN_DEBUG_COMPILE(Cgl)

# Get the name of the C++ compiler and appropriate compiler options
AC_COIN_PROG_CXX

# Initialize automake and libtool
AC_COIN_INIT_AUTO_TOOLS

#############################################################################
#                            COIN-OR components                             #
#############################################################################

AC_COIN_CHECK_PACKAGE(CoinUtils, [coinutils], [CglLib])
if test $coin_has_coinutils != yes ; then
  AC_MSG_ERROR([Required package CoinUtils not available.])
fi

AC_COIN_CHECK_PACKAGE(Osi, [osi], [CglLib])
if test $coin_has_osi != yes ; then
  AC_MSG_ERROR([Required package Osi not available.])
fi

AC_COIN_CHECK_PACKAGE(Sample, [coindatasample])

# Clp can be used by CglLandP
AC_COIN_CHECK_PACKAGE(OsiClp, [osi-clp], [CglLib])

#############################################################################
#                       Solvers for unittesting                             #
#############################################################################

# These are not really required for the compilation of Cgl, but we
# need to know which are available in order to compile the unitTest
# correctly.

AC_COIN_CHECK_PACKAGE(OsiCpx,  [osi-cplex])
AC_COIN_CHECK_PACKAGE(OsiGlpk, [osi-glpk])
#AC_COIN_CHECK_PACKAGE(OsiGrb,  [osi-gurobi])
AC_COIN_CHECK_PACKAGE(OsiMsk,  [osi-mosek])
AC_COIN_CHECK_PACKAGE(OsiXpr,  [osi-xpress])
AC_COIN_CHECK_PACKAGE(OsiVol,  [osi-vol])
AC_COIN_CHECK_PACKAGE(OsiDyLP, [osi-dylp])
#AC_COIN_CHECK_PACKAGE(OsiSpx,  [osi-soplex])

#############################################################################
#                  System header                                            #
#############################################################################

AC_COIN_CHECK_CXX_CHEADER(math)
AC_COIN_CHECK_CXX_CHEADER(float)
AC_COIN_CHECK_CXX_CHEADER(ieeefp)

#############################################################################
#                   Determine list of all Cgl subprojects                   #
#############################################################################

# In order to avoid that one has to update this configure.ac and the
# Makefile.am whenever a new cut generator is added, we automatically determine
# the list of all subdirectories of src with a Makefile.in (CGL_SUBDIRS),
# and also a list of all sublibraries relative to src (CGL_SUBLIBS) that
# can be used in the src/Makefile.am.  (It is still necessary to manually
# add an entry to write the Makefile in the AC_CONFIG_FILES list below.)

AC_SUBST(CGL_SUBDIRS)
AC_SUBST(CGL_SUBLIBS)

curr_dir=`pwd`
cd $srcdir/src
for file in `ls */Makefile.in`; do
  newdir=`echo $file | sed -e s%/Makefile.in%% | sed -e s%^./%% `
  CGL_SUBDIRS="$CGL_SUBDIRS $newdir"
  CGL_SUBLIBS="$CGL_SUBLIBS $newdir/lib${newdir}.la"
done
cd $curr_dir

#############################################################################
#                  Check for doxygen                                        #
#############################################################################

AC_COIN_DOXYGEN(CoinUtils)

##############################################################################
#                   Finishing up by writing all the output                   #
##############################################################################

# Install files for unitTest
AC_COIN_VPATH_LINK([test/CglTestData/capPlan1.mps test/CglTestData/l152lav.mps test/CglTestData/egout.mps test/CglTestData/lseu.mps])

# Here list all the files that configure should create (except for the
# configuration header file)
AC_CONFIG_FILES([Makefile
                 examples/Makefile
                 src/Makefile
                 src/CglAllDifferent/Makefile
                 src/CglClique/Makefile
                 src/CglDuplicateRow/Makefile
                 src/CglFlowCover/Makefile
                 src/CglGMI/Makefile
                 src/CglGomory/Makefile
                 src/CglKnapsackCover/Makefile
                 src/CglLandP/Makefile
                 src/CglLiftAndProject/Makefile
                 src/CglMixedIntegerRounding/Makefile
                 src/CglMixedIntegerRounding2/Makefile
                 src/CglOddHole/Makefile
                 src/CglPreProcess/Makefile
                 src/CglProbing/Makefile
                 src/CglRedSplit/Makefile
                 src/CglRedSplit2/Makefile
                 src/CglResidualCapacity/Makefile
                 src/CglSimpleRounding/Makefile
                 src/CglTwomir/Makefile
                 src/CglZeroHalf/Makefile
                 test/Makefile
                 cgl.pc
                 cgl-uninstalled.pc])
AC_CONFIG_FILES([doxydoc/doxygen.conf])

# Here put the location and name of the configuration header file
AC_CONFIG_HEADER([src/config.h src/config_cgl.h])

# Finally, we let configure write all the output...
AC_COIN_FINALIZE
