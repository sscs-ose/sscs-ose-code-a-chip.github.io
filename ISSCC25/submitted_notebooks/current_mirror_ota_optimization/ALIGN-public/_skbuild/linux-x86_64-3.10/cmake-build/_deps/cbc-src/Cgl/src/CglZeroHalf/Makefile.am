# Copyright (C) 2006 International Business Machines and others.
# All Rights Reserved.
# This file is distributed under the Eclipse Public License.

## $Id: Makefile.am 1165 2013-12-11 09:18:38Z stefan $

# Author:  Andreas Waechter           IBM    2006-04-13

AUTOMAKE_OPTIONS = foreign

########################################################################
#                       libCglZeroHalf                           #
########################################################################

# Name of the library compiled in this directory.  We don't want it to be
# installed since it will be collected into the libCgl library
noinst_LTLIBRARIES = libCglZeroHalf.la

# List all source files for this library, including headers
libCglZeroHalf_la_SOURCES = \
	CglZeroHalf.cpp  CglZeroHalf.hpp \
	Cgl012cut.cpp  Cgl012cut.hpp \
	CglZeroHalfTest.cpp

# This is for libtool
libCglZeroHalf_la_LDFLAGS = $(LT_LDFLAGS)

# Here list all include flags, relative to this "srcdir" directory.  This
# "cygpath" stuff is necessary to compile with native compilers on Windows.
# "top_srcdir" refers to the basic directory for the main package that is
# being compiled.
AM_CPPFLAGS = -I`$(CYGPATH_W) $(srcdir)/..` $(COINUTILS_CFLAGS) $(OSI_CFLAGS)

# This line is necessary to allow VPATH compilation
DEFAULT_INCLUDES = -I. -I`$(CYGPATH_W) $(srcdir)`

########################################################################
#                Headers that need to be installed                     #
########################################################################

# Here list all the header files that are required by a user of the library,
# and that therefore should be installed in 'include/coin'
includecoindir = $(includedir)/coin
includecoin_HEADERS = CglZeroHalf.hpp Cgl012cut.hpp
