#===========================================================================#
#                                                                           #
# This file is part of the SYMPHONY MILP Solver Framework.                  #
#                                                                           #
# SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         #
# Laci Ladanyi (ladanyi@us.ibm.com).                                        #
#                                                                           #
# The author of this file is Menal Guzelsoy                                 #
#                                                                           #
# (c) Copyright 2006-2019 Lehigh University. All Rights Reserved.           #
#                                                                           #
# This software is licensed under the Eclipse Public License. Please see    #
# accompanying file for terms.                                              #
#                                                                           #
#===========================================================================#

## $Id: configure.ac 2733 2019-02-24 15:00:41Z tkr $

#############################################################################
#                       Names and other basic things                        #
#############################################################################

AC_PREREQ(2.59)

AC_INIT([SYMPHONY],[5.6.17],[https://projects.coin-or.org/svn/SYMPHONY/newticket])

AC_COPYRIGHT([
/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* (c) Copyright 2000-2019 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Common Public License. Please see     */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/
])

AC_REVISION(0.9)

# List one file in the package so that the configure script can test
# whether the package is actually there
AC_CONFIG_SRCDIR(configure.ac)

# Where should everything be installed by default?  Here, we want it
# to be installed directly in 'bin', 'lib', 'include' subdirectories
# of the directory where configure is run.  The default would be
# /usr/local.
AC_PREFIX_DEFAULT([`pwd`])

#############################################################################
#     We only need automake to generate Makefiles for the distribution      #
#############################################################################

# Initialize automake
AC_COIN_CREATE_LIBTOOL

#############################################################################
#                  Check which subprojects are there                        #
#############################################################################

AC_COIN_MAIN_PACKAGEDIR(Blas,   ThirdParty,[daxpy.f])
AC_COIN_MAIN_PACKAGEDIR(Lapack, ThirdParty,[LAPACK/SRC/dlarf.f])
AC_COIN_MAIN_PACKAGEDIR(Glpk,   ThirdParty,[glpk/src/glplpx01.c])
AC_COIN_MAIN_PACKAGEDIR(Sample, Data)
AC_COIN_MAIN_PACKAGEDIR(miblib3,Data)
AC_COIN_MAIN_PACKAGEDIR(CoinUtils)
AC_COIN_MAIN_PACKAGEDIR(Osi)
AC_COIN_MAIN_PACKAGEDIR(Clp)
AC_COIN_MAIN_PACKAGEDIR(Cgl)
AC_COIN_MAIN_PACKAGEDIR(DyLP)
AC_COIN_MAIN_PACKAGEDIR(Vol)
AC_COIN_MAIN_PACKAGEDIR(SYMPHONY)

#############################################################################
#                      Check for the LP solver                              #
#############################################################################
AC_MSG_CHECKING(whether Clp is required)
AC_ARG_WITH([lp-solver],
[AC_HELP_STRING([--with-lp-solver],
                [specify the LP solver you want SYMPHONY to use in small
                letters(default=clp)])],
		[sym_lp_solver=$withval],[sym_lp_solver=clp])

if test $sym_lp_solver = clp; then
    AC_MSG_RESULT(yes)
else
    AC_MSG_RESULT(no)
fi

AM_CONDITIONAL(ADD_CLP, [test $sym_lp_solver = clp])

use_tp_glpk=false
for dir in $subdirs; do
    if test "$dir" = "ThirdParty/Glpk"; then
      use_tp_glpk=true
    fi
done


AM_CONDITIONAL(ADD_GLPK, [test $use_tp_glpk = true])

##############################################################################
#                   Finishing up by writing all the output                   #
##############################################################################

# Here list all the files that configure should create (except for the
# configuration header file)
AC_CONFIG_FILES([Makefile])

# Finally, we let configure write all the output...
AC_COIN_FINALIZE
