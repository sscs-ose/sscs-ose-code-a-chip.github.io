# Copyright (C) 2006 International Business Machines and others.
# All Rights Reserved.
# This file is distributed under the Eclipse Public License.

## $Id: Makefile.am 2111 2017-11-07 03:40:06Z tkr $

AUTOMAKE_OPTIONS = foreign

########################################################################
#                             libOsiSpx                                #
########################################################################

# Name of the library compiled in this directory.
lib_LTLIBRARIES = libOsiSpx.la

# List all source files for this library, including headers
libOsiSpx_la_SOURCES = OsiSpxSolverInterface.cpp OsiSpxSolverInterface.hpp

# List all additionally required libraries
if DEPENDENCY_LINKING
libOsiSpx_la_LIBADD = $(OSILIB_LIBS) ../Osi/libOsi.la
endif

# This is for libtool
libOsiSpx_la_LDFLAGS = $(LT_LDFLAGS)

# Here list all include flags, relative to this "srcdir" directory.  This
# "cygpath" stuff is necessary to compile with native compilers on Windows.
AM_CPPFLAGS = -I`$(CYGPATH_W) $(srcdir)/../Osi` $(COINUTILS_CFLAGS) $(SOPLEX_CFLAGS)

# This line is necessary to allow VPATH compilation
DEFAULT_INCLUDES = -I. -I`$(CYGPATH_W) $(srcdir)` -I$(top_builddir)/src/Osi

########################################################################
#                Headers that need to be installed                     #
########################################################################

# Here list all the header files that are required by a user of the library,
# and that therefore should be installed in 'include/coin'
includecoindir = $(includedir)/coin
includecoin_HEADERS = OsiSpxSolverInterface.hpp
