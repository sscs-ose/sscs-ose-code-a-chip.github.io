# Copyright (C) 2006 International Business Machines and others.
# All Rights Reserved.
# This file is distributed under the Eclipse Public License.

# $Id: Makefile.in 1881 2013-01-28 00:05:47Z stefan $

##########################################################################
#    You can modify this example makefile to fit for your own program.   #
#    Usually, you only need to change CHANGEME entries below.            #
##########################################################################

# CHANGEME
# To compile other examples, either change the following line, or add the
# argument DRIVER=filename_without_extension to make, e.g.,
# `make DRIVER=parameters'

DRIVER = basic

# CHANGME
# This should be the name of your executable; change if you want a name
# that's different from the file name.

EXE = $(DRIVER)

# CHANGEME
# OBJS should include all object files necessary to build your program. For
# the examples, only one file is needed for each example. You will probably
# have more as your code grows.

OBJS =  $(DRIVER).o

# CHANGEME
# Additional libraries. The examples require only the COIN libraries specified
# as LIBS below. You may need more.

ADDLIBS =

# CHANGEME
# Additional flags for compilation (e.g., include flags). As for libraries,
# the examples require only COIN include files, specified as part of CXXFLAGS
# below.

ADDINCFLAGS =

# CHANGEME
# Directory to the sources for the (example) problem definition files. VPATH
# is used if you are building in a different directory than the source. This
# can be handy for various reasons; if none occur to you, don't worry about
# it.

SRCDIR = /home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-src/Osi/examples
VPATH = /home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-src/Osi/examples

##########################################################################
#  Usually, you don't have to change anything below.  Note that if you   #
#  change certain compiler options, you might have to recompile the      #
#  package.                                                              #
##########################################################################

COIN_HAS_PKGCONFIG = TRUE
COIN_CXX_IS_CL = #TRUE
COIN_HAS_SAMPLE = TRUE
COIN_HAS_NETLIB = #TRUE

# C++ Compiler command
CXX = g++

# C++ Compiler options
CXXFLAGS = -O3 -pipe -DNDEBUG -Wparentheses -Wreturn-type -Wcast-qual -Wall -Wpointer-arith -Wwrite-strings -Wconversion -Wno-unknown-pragmas -Wno-long-long   -DOSI_BUILD  \
  -DOSIXXXhpp=\".hpp\" -DOSIXXX=

# Sample data directory
ifeq ($(COIN_HAS_SAMPLE), TRUE)
  ifeq ($(COIN_HAS_PKGCONFIG), TRUE)
    CXXFLAGS += -DSAMPLEDIR=\"`PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --variable=datadir coindatasample`\"
  else
    CXXFLAGS += -DSAMPLEDIR=\"\"
  endif
endif

# Netlib data directory
ifeq ($(COIN_HAS_NETLIB), TRUE)
  ifeq ($(COIN_HAS_PKGCONFIG), TRUE)
    CXXFLAGS += -DNETLIBDIR=\"`PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --variable=datadir coindatanetlib`\"
  else
    CXXFLAGS += -DNETLIBDIR=\"\"
  endif
endif

# additional C++ Compiler options for linking
CXXLINKFLAGS = 

# Include directories (we use the CYGPATH_W variables to allow compilation with Windows compilers)
ifeq ($(COIN_HAS_PKGCONFIG), TRUE)
  INCL = `PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --cflags  osi`
else
  INCL = 
endif
INCL += $(ADDINCFLAGS)

# Linker flags
ifeq ($(COIN_HAS_PKGCONFIG), TRUE)
  LIBS = `PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --libs  osi`
else
  ifeq ($(COIN_CXX_IS_CL), TRUE)
    LIBS = -link -libpath:`$(CYGPATH_W) /home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib` libOsi.lib  
  else
    LIBS = -L/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib -lOsi  
  endif
endif

# The following is necessary under cygwin, if native compilers are used
CYGPATH_W = echo

all: $(EXE)

.SUFFIXES: .cpp .c .o .obj

$(EXE): $(OBJS)
	bla=;\
	for file in $(OBJS); do bla="$$bla `$(CYGPATH_W) $$file`"; done; \
	$(CXX) $(CXXLINKFLAGS) $(CXXFLAGS) -o $@ $$bla $(LIBS) $(ADDLIBS)

clean:
	rm -rf $(EXE) $(OBJS)

.cpp.o:
	$(CXX) $(CXXFLAGS) $(INCL) -c -o $@ `test -f '$<' || echo '$(SRCDIR)/'`$<


.cpp.obj:
	$(CXX) $(CXXFLAGS) $(INCL) -c -o $@ `if test -f '$<'; then $(CYGPATH_W) '$<'; else $(CYGPATH_W) '$(SRCDIR)/$<'; fi`

.c.o:
	$(CC) $(CFLAGS) $(INCL) -c -o $@ `test -f '$<' || echo '$(SRCDIR)/'`$<


.c.obj:
	$(CC) $(CFLAGS) $(INCL) -c -o $@ `if test -f '$<'; then $(CYGPATH_W) '$<'; else $(CYGPATH_W) '$(SRCDIR)/$<'; fi`
