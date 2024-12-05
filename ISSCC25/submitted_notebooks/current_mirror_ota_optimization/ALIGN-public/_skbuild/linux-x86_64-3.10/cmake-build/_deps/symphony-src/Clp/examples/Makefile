# Copyright (C) 2006 International Business Machines and others.
# All Rights Reserved.
# This file is distributed under the Eclipse Public License.

# $Id: Makefile.in 726 2006-04-17 04:16:00Z andreasw $

##########################################################################
#    You can modify this example makefile to fit for your own program.   #
#    Usually, you only need to change the five CHANGEME entries below.   #
##########################################################################

# To compile other examples, either changed the following line, or
# add the argument DRIVER=problem_name to make
DRIVER = driver

# CHANGEME: This should be the name of your executable
EXE = $(DRIVER)

# CHANGEME: Here is the name of all object files corresponding to the source
#           code that you wrote in order to define the problem statement
OBJS =  $(DRIVER).o 

# CHANGEME: Additional libraries
ADDLIBS =

# CHANGEME: Additional flags for compilation (e.g., include flags)
ADDINCFLAGS =

# CHANGEME: Directory to the sources for the (example) problem definition
# files
SRCDIR = /home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-src/Clp/examples
VPATH = /home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-src/Clp/examples

##########################################################################
#  Usually, you don't have to change anything below.  Note that if you   #
#  change certain compiler options, you might have to recompile the      #
#  COIN package.                                                         #
##########################################################################

COIN_HAS_PKGCONFIG = TRUE
COIN_CXX_IS_CL = #TRUE
COIN_HAS_SAMPLE = TRUE
COIN_HAS_NETLIB = #TRUE

# C++ Compiler command
CXX = g++

# C++ Compiler options
CXXFLAGS = -O3 -pipe -DNDEBUG -Wparentheses -Wreturn-type -Wcast-qual -Wall -Wpointer-arith -Wwrite-strings -Wconversion -Wno-unknown-pragmas -Wno-long-long   -DCLP_BUILD

# additional C++ Compiler options for linking
CXXLINKFLAGS = 

# C Compiler command
CC = gcc

# C Compiler options
CFLAGS = -O3 -pipe -DNDEBUG -Wimplicit -Wparentheses -Wsequence-point -Wreturn-type -Wcast-qual -Wall -Wno-unknown-pragmas -Wno-long-long   -DCLP_BUILD

# Sample data directory
ifeq ($(COIN_HAS_SAMPLE), TRUE)
  ifeq ($(COIN_HAS_PKGCONFIG), TRUE)
    CXXFLAGS += -DSAMPLEDIR=\"`PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --variable=datadir coindatasample`\"
      CFLAGS += -DSAMPLEDIR=\"`PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --variable=datadir coindatasample`\"
  else
    CXXFLAGS += -DSAMPLEDIR=\"\"
      CFLAGS += -DSAMPLEDIR=\"\"
  endif
endif

# Netlib data directory
ifeq ($(COIN_HAS_NETLIB), TRUE)
  ifeq ($(COIN_HAS_PKGCONFIG), TRUE)
    CXXFLAGS += -DNETLIBDIR=\"`PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --variable=datadir coindatanetlib`\"
      CFLAGS += -DNETLIBDIR=\"`PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --variable=datadir coindatanetlib`\"
  else
    CXXFLAGS += -DNETLIBDIR=\"\"
      CFLAGS += -DNETLIBDIR=\"\"
  endif
endif

# Include directories (we use the CYGPATH_W variables to allow compilation with Windows compilers)
ifeq ($(COIN_HAS_PKGCONFIG), TRUE)
  INCL = `PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --cflags clp`
else
  INCL = 
endif
INCL += $(ADDINCFLAGS)

# Linker flags
ifeq ($(COIN_HAS_PKGCONFIG), TRUE)
  LIBS = `PKG_CONFIG_PATH=/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib64/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib/pkgconfig:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/share/pkgconfig: pkg-config --libs clp`
else
  ifeq ($(COIN_CXX_IS_CL), TRUE)
    LIBS = -link -libpath:`$(CYGPATH_W) /home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib` libClpSolver.lib libClp.lib 
  else
    LIBS = -L/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/symphony-build/lib -lClpSolver -lClp 
  endif
endif

# The following is necessary under cygwin, if native compilers are used
CYGPATH_W = echo

# Here we list all possible generated objects or executables to delete them
CLEANFILES = \
	addBits.o addBits \
	addColumns.o addColumns \
	addRows.o addRows \
	decomp2.o decomp2 \
	decomp3.o decomp3 \
	decompose.o decompose \
	defaults.o defaults \
	driver2.o driver2 \
	driver.o driver \
	driverC.o driverC \
	dualCuts.o dualCuts \
	ekk.o ekk \
	ekk_interface.o ekk_interface \
	hello.o hello \
	makeDual.o makeDual \
	minimum.o minimum \
	modify.o modify \
	network.o network \
	pdco.o pdco \
	piece.o piece \
	rowColumn.o rowColumn \
	sprint2.o sprint2 \
	sprint.o sprint \
	testBarrier.o testBarrier \
	testBasis.o testBasis \
	testGub2.o testGub2 \
	testGub.o testGub \
	testQP.o testQP \
	useVolume.o useVolume

all: $(EXE)

.SUFFIXES: .cpp .c .o .obj

$(EXE): $(OBJS)
	bla=;\
	for file in $(OBJS); do bla="$$bla `$(CYGPATH_W) $$file`"; done; \
	$(CXX) $(CXXLINKFLAGS) $(CXXFLAGS) -o $@ $$bla $(LIBS) $(ADDLIBS)

clean:
	rm -rf $(CLEANFILES)

.cpp.o:
	$(CXX) $(CXXFLAGS) $(INCL) -c -o $@ `test -f '$<' || echo '$(SRCDIR)/'`$<


.cpp.obj:
	$(CXX) $(CXXFLAGS) $(INCL) -c -o $@ `if test -f '$<'; then $(CYGPATH_W) '$<'; else $(CYGPATH_W) '$(SRCDIR)/$<'; fi`

.c.o:
	$(CC) $(CFLAGS) $(INCL) -c -o $@ `test -f '$<' || echo '$(SRCDIR)/'`$<


.c.obj:
	$(CC) $(CFLAGS) $(INCL) -c -o $@ `if test -f '$<'; then $(CYGPATH_W) '$<'; else $(CYGPATH_W) '$(SRCDIR)/$<'; fi`
