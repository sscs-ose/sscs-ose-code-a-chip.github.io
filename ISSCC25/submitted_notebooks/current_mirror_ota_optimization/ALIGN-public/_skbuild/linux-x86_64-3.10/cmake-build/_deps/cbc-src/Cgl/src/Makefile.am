# Copyright (C) 2006 International Business Machines and others.
# All Rights Reserved.
# This file is distributed under the Eclipse Public License.

## $Id: Makefile.am 1159 2013-11-21 19:57:09Z stefan $

# Author:  Andreas Waechter           IBM    2006-04-13

AUTOMAKE_OPTIONS = foreign

# We need to recurse into all Cgl subproject subdirectories
SUBDIRS = $(CGL_SUBDIRS)

########################################################################
#                               libCgl                                 #
########################################################################

# Name of the library compiled in this directory.  We want it to be installed
# in the $libdir directory
lib_LTLIBRARIES = libCgl.la

# List all source files for this library, including headers
libCgl_la_SOURCES = \
	CglConfig.h \
	CglCutGenerator.cpp CglCutGenerator.hpp\
	CglMessage.cpp CglMessage.hpp \
	CglStored.cpp CglStored.hpp \
	CglParam.cpp CglParam.hpp \
	CglTreeInfo.cpp CglTreeInfo.hpp

# This is for libtool (on Windows)
libCgl_la_LDFLAGS = $(LT_LDFLAGS)

# We want to have all the sublibraries from the Cgl subprojects collected into
# this library
libCgl_la_LIBADD = $(CGL_SUBLIBS)
if DEPENDENCY_LINKING
libCgl_la_LIBADD += $(CGLLIB_LIBS)
endif

# Since automake is not doing this on its own, we need to declare the
# dependencies to the subdirectory libraries here
libCgl_la_DEPENDENCIES = $(CGL_SUBLIBS)

# Here list all include flags, relative to this "srcdir" directory.  This
# "cygpath" stuff is necessary to compile with native compilers on Windows.
AM_CPPFLAGS = $(COINUTILS_CFLAGS) $(OSI_CFLAGS)

# This line is necessary to allow VPATH compilation
DEFAULT_INCLUDES = -I. -I`$(CYGPATH_W) $(srcdir)`

########################################################################
#                Headers that need to be installed                     #
########################################################################

# Here list all the header files that are required by a user of the library,
# and that therefore should be installed in 'include/coin'
includecoindir = $(includedir)/coin
includecoin_HEADERS = \
	CglCutGenerator.hpp \
	CglMessage.hpp \
	CglStored.hpp \
	CglParam.hpp \
	CglTreeInfo.hpp

install-exec-local:
	$(install_sh_DATA) config_cgl.h $(DESTDIR)$(includecoindir)/CglConfig.h

uninstall-local:
	rm -f $(DESTDIR)$(includecoindir)/CglConfig.h
