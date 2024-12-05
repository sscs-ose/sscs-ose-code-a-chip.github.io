# Copyright (C) 2006 International Business Machines and others.
# All Rights Reserved.
# This file is distributed under the Eclipse Public License.

## $Id: Makefile.am 1105 2013-03-19 12:43:52Z forrest $

# Author:  Andreas Waechter           IBM    2006-04-13

AUTOMAKE_OPTIONS = foreign

########################################################################
#                           libCglTwomir                               #
########################################################################

# Name of the library compiled in this directory.  We don't want it to be
# installed since it will be collected into the libCgl library
noinst_LTLIBRARIES = libCglTwomir.la

# List all source files for this library, including headers
libCglTwomir_la_SOURCES = CglTwomir.cpp CglTwomir.hpp CglTwomirTest.cpp

# This is for libtool (on Windows)
libCglTwomir_la_LDFLAGS = $(LT_LDFLAGS)

# Here list all include flags, relative to this "srcdir" directory.  This
# "cygpath" stuff is necessary to compile with native compilers on Windows.
AM_CPPFLAGS = -I`$(CYGPATH_W) $(srcdir)/..` $(COINUTILS_CFLAGS) $(OSI_CFLAGS)

if COIN_HAS_OSICLP
AM_CPPFLAGS += $(OSICLP_CFLAGS)
endif

# This line is necessary to allow VPATH compilation
DEFAULT_INCLUDES = -I. -I`$(CYGPATH_W) $(srcdir)` -I..

########################################################################
#                Headers that need to be installed                     #
########################################################################

# Here list all the header files that are required by a user of the library,
# and that therefore should be installed in 'include/coin'
includecoindir = $(includedir)/coin
includecoin_HEADERS = CglTwomir.hpp
