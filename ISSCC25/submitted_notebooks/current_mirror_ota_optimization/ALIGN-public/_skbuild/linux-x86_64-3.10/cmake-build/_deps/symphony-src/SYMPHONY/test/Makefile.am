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

## $Id: Makefile.am 372 2006-06-15 14:18:02Z andreasw $

AUTOMAKE_OPTIONS = foreign

########################################################################
#                         unitTest for Symphony                        #
########################################################################

AM_CPPFLAGS = $(OSITESTS_CFLAGS) $(SYMPHONYLIB_CFLAGS)
SYMCPPFLAGS =
SYMPCPPFLAGS =
APPLCPPFLAGS =
SYMPALLLDADD =
LDADD = $(OSITESTS_LIBS) $(SYMPHONYLIB_LIBS)
DEPENDENCIES = $(OSITESTS_DEPENDENCIES) $(SYMPHONYLIB_DEPENDENCIES)
ALLLDADD =

LIBS =
SYMLIB = 
SYMPLIB = 

# Add include files
AM_CPPFLAGS += -DCOIN_HAS_SYMPHONY

# List all additionally required solver and Osi libraries

if CLP_LP_SOLVER
  AM_CPPFLAGS += -D__OSI_CLP__
endif

if CPLEX_LP_SOLVER
  AM_CPPFLAGS += -D__OSI_CPLEX__
endif

if GLPK_LP_SOLVER
  AM_CPPFLAGS += -D__OSI_GLPK__
endif 

if SOPLEX_LP_SOLVER
  AM_CPPFLAGS += -D__OSI_SOPLEX__
endif

if XPRESS_LP_SOLVER
  AM_CPPFLAGS += -D__OSI_XPRESS__
endif

########################################################################
#                            Additional Definitions                    #
########################################################################

ALLLDADD += $(LDADD)
SYMCPPFLAGS += $(AM_CPPFLAGS) $(SYMDEFS)
SYMLIB += ../src/libSym.la ../src/OsiSym/libOsiSym.la

SYMPCPPFLAGS += $(AM_CPPFLAGS) $(SYMPDEFS)
SYMPALLLDADD += $(ALLLDADD)

if SYM_PARALLEL
SYMPCPPFLAGS += -I`$(CYGPATH_W) $(PVM_ROOT)/include`
SYMPALLLDADD += -L`$(CYGPATH_W) $(PVM_ROOT)/lib/$(ARCH)` \
	-lgpvm3 -lpvm3
SYMPLIB += ../src/libSym$(MASTEREXT).la ../src/OsiSym/libOsiSym.la
else
SYMPLIB += $(SYMLIB)
endif

DEFAULT_INCLUDES = -I. -I`$(CYGPATH_W) $(top_srcdir)/include` \
		   -I`$(CYGPATH_W) $(top_builddir)/include` \
		   -I`$(CYGPATH_W) $(top_srcdir)/src/OsiSym`

TestLDADD = $(LDADD)
TestLINK = 
if COIN_CXX_IS_CL
TestLINK += cp -f OsiColCutTest.$(OBJEXT) unitTest-OsiColCutTest.$(OBJEXT); \
	cp -f OsiCutsTest.$(OBJEXT)  unitTest-OsiCutsTest.$(OBJEXT); \
	cp -f OsiRowCutDebuggerTest.$(OBJEXT) unitTest-OsiRowCutDebuggerTest.$(OBJEXT); \
	cp -f OsiRowCutTest.$(OBJEXT) unitTest-OsiRowCutTest.$(OBJEXT); \
	cp -f OsiSymSolverInterfaceTest.$(OBJEXT) unitTest-OsiSymSolverInterfaceTest.$(OBJEXT); \
	cp -f unitTestSym.$(OBJEXT) unitTest-unitTestSym.$(OBJEXT); \
	$(LIBTOOL) \
	--tag=CXX --mode=link $(CXX) $(AM_CFLAGS) $(CCLCFLAGS) \
	$(AM_LDFLAGS) $(LDFLAGS) -o $@
TestLDADD += OsiColCutTest.$(OBJEXT) OsiCutsTest.$(OBJEXT) \
	OsiRowCutDebuggerTest.$(OBJEXT) OsiRowCutTest.$(OBJEXT) \
	OsiSymSolverInterfaceTest.$(OBJEXT) unitTestSym.$(OBJEXT)
else 
TestLINK += $(CXXLINK)
endif

noinst_PROGRAMS = unitTest punitTest

unitTest_SOURCES = \
	OsiSymSolverInterfaceTest.cpp \
	unitTestSym.cpp

punitTest_SOURCES = \
	OsiSymSolverInterfaceTest.cpp \
	unitTestSym.cpp

unitTest_CPPFLAGS = $(SYMCPPFLAGS) $(OSIUNITTEST_CFLAGS)
unitTest_LDADD = $(SYMLIB) $(ALLLDADD) $(OSIUNITTEST_LIBS)
unitTest_DEPENDENCIES = $(SYMLIB) $(DEPENDENCIES)
unitTest_LINK = $(TestLINK)

punitTest_CPPFLAGS = $(SYMPCPPFLAGS) $(OSIUNITTEST_CFLAGS)
punitTest_LDADD = $(SYMPLIB) $(SYMPALLLDADD) $(OSIUNITTEST_LIBS)
punitTest_DEPENDENCIES = $(SYMPLIB) $(DEPENDENCIES)


if COIN_HAS_MIPLIB3
  MIPLIBDIR = -miplib3Dir=`$(CYGPATH_W) $(MIPLIB3_DATA)`
check_files:
	  echo "using MIPLIB3 directory $(MIPLIB3_DATA)"

else
  MIPLIBDIR = -miplib3Dir=`$(CYGPATH_W) $(top_srcdir)/miplib3`
  
check_files:
	if test -r $(top_srcdir)/miplib3; then \
	  echo "MIBLIB3 directory found..."; \
	else \
	  echo "Downloading required test files to $(top_srcdir)/miplib3"; \
	  mkdir $(top_srcdir)/miplib3; \
	  for file in $(testFILES); do \
	    (echo $$file; svn cat https://projects.coin-or.org/svn/Data/miplib3/stable/1.2/$$file.gz >> $(top_srcdir)/miplib3/$$file.gz) \
	  done; \
	  fi; \
	  echo "Uncompressing files"; \
	  cd $(top_srcdir)/miplib3; \
	  for file in $(testFILES); do \
	    if test -r $$file.gz; then \
	      (gzip -d $$file.gz) \
	    fi \
	  done
endif

unittestflags =
if COIN_HAS_NETLIB
  unittestflags += -netlibDir=`$(CYGPATH_W) $(NETLIB_DATA)` -testOsiSolverInterface
endif
if COIN_HAS_SAMPLE
  unittestflags += -mpsDir=`$(CYGPATH_W) $(SAMPLE_DATA)`
endif

testFILES = air03 air04 air05 bell3a blend2 cap6000 dcmulti dsbmip \
     egout enigma fiber fixnet6 flugpl gen gesa2 gesa2_o \
     gesa3 gesa3_o gt2 khb05250 l152lav lseu misc03 misc06 \
     misc07 mitre mod008 mod010 mod011 nw04 p0033 p0201 \
     p0282 p0548 p2756 pp08a pp08aCUTS qnet1 qnet1_o rentacar \
     rgn stein27 stein45 vpm1 vpm2

# by passing -miplib3Dir= we can overwrite using a default miplib3 path which would trigger the MIPLIB tests
test: unitTest$(EXEEXT)
	./unitTest$(EXEEXT) -miplib3Dir= $(unittestflags)

fulltest: check_files unitTest$(EXEEXT)
	./unitTest$(EXEEXT) $(MIPLIBDIR) $(unittestflags)

ptest: punitTest$(EXEEXT)
	./punitTest$(EXEEXT) -miplib3Dir= $(unittestflags)

pfulltest: check_files punitTest$(EXEEXT)
	./punitTest$(EXEEXT) $(MIPLIBDIR) $(unittestflags)

.PHONY: test ptest fulltest pfulltest check_files

########################################################################
#                          Cleaning stuff                              #
########################################################################

# Here we list everything that is not generated by the compiler, e.g.,
# output files of a program

DISTCLEANFILES = *.mps *.mps.gz *.lp test2out *.out.gz *.out
