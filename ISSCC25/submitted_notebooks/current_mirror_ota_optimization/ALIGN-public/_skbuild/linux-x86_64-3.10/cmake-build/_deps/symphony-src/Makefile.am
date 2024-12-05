#===========================================================================#
#                                                                           #
# This file is part of the SYMPHONY MILP Solver Framework.                  #
#                                                                           #
# SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         #
# Laci Ladanyi (ladanyi@us.ibm.com).                                        #
#                                                                           #
# The author of this file is Menal Guzelsoy                                 #
#                                                                           #
# (c) Copyright 2006-2015 Lehigh University. All Rights Reserved.           #
#                                                                           #
# This software is licensed under the Eclipse Public License. Please see    #
# accompanying file for terms.                                              #
#                                                                           #
#===========================================================================#

## $Id: Makefile.am 2431 2015-03-10 21:28:59Z tkr $

AUTOMAKE_OPTIONS = foreign

EXTRA_DIST = 

########################################################################
#                          Subdirectories                              #
########################################################################

# subdirs is set by configure as the list of all subdirectories to recurse
# into

SUBDIRS = $(subdirs)

########################################################################
#                           Extra Targets                              #
########################################################################

test: all
	cd SYMPHONY; $(MAKE) test

fulltest: all
	cd SYMPHONY; $(MAKE) fulltest

ptest: all
	cd SYMPHONY; $(MAKE) ptest

pfulltest: all
	cd SYMPHONY; $(MAKE) pfulltest

unitTest: test

punitTest: ptest

tests: all
	for dir in $(SUBDIRS); do \
	  if test -r $$dir/test/Makefile; then \
	    (cd $$dir; $(MAKE) test) \
	  fi; \
	done

unitTests: tests

.PHONY: test unitTest ptest punitTest tests unitTests fulltest pfulltest

########################################################################
#                         Maintainer Stuff                             #
########################################################################

# Files that are generated and should be cleaned with make distclean
DISTCLEANFILES = coin_subdirs.txt

include BuildTools/Makemain.inc
