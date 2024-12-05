# Copyright (C) 2006 International Business Machines and others.
# All Rights Reserved.
# This file is distributed under the Eclipse Public License.

## $Id: Makefile.am 243 2006-06-01 20:11:02Z andreasw $

# Author:  Andreas Waechter           IBM    2006-04-13

AUTOMAKE_OPTIONS = foreign

########################################################################
#                           libCglLandP                                #
########################################################################

# Name of the library compiled in this directory.  We don't want it to be
# installed since it will be collected into the libCgl library
noinst_LTLIBRARIES = libCglLandP.la

# List all source files for this library, including headers
libCglLandP_la_SOURCES = \
	CglLandPTabRow.hpp \
	CglLandPUtils.cpp  CglLandPUtils.hpp
if COIN_HAS_OSICLP
libCglLandP_la_SOURCES += \
	CglLandP.cpp  CglLandP.hpp \
	CglLandPTabRow.cpp \
        CglLandPMessages.h CglLandPMessages.cpp \
        CglLandPSimplex.cpp CglLandPSimplex.hpp \
        CglLandPValidator.cpp CglLandPValidator.hpp \
        CglLandPTest.cpp
endif

# This is for libtool (on Windows)
libCglLandP_la_LDFLAGS = $(LT_LDFLAGS)

# Here list all include flags, relative to this "srcdir" directory.  This
# "cygpath" stuff is necessary to compile with native compilers on Windows.
AM_CPPFLAGS = \
	-I`$(CYGPATH_W) $(srcdir)/..` \
        -I`$(CYGPATH_W) $(srcdir)/../CglGomory` \
        $(COINUTILS_CFLAGS) $(OSI_CFLAGS)
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
if COIN_HAS_OSICLP
includecoin_HEADERS = CglLandP.hpp CglLandPValidator.hpp
endif
