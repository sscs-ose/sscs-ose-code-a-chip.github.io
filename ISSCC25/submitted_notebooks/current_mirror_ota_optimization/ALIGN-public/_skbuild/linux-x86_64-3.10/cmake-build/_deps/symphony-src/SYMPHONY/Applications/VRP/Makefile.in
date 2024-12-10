#===========================================================================#
#                                                                           #
# This file is part of the SYMPHONY MILP Solver Framework.                  #
#                                                                           #
# SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         #
# Laci Ladanyi (ladanyi@us.ibm.com).                                        #
#                                                                           #
# The author of this file is Menal Guzelsoy                                 #
#                                                                           #
# (c) Copyright 2000-2015 Lehigh University. All Rights Reserved.           #
#                                                                           #
# This software is licensed under the Eclipse Public License. Please see    #
# accompanying file for terms.                                              #
#                                                                           #
#===========================================================================#

# $Id: Makefile.in 726 2006-04-17 04:16:00Z andreasw $

MASTERNAME = vrp

SYMAPPLNAME = VRP

# CHANGEME: Additional sources
# - Names of your additional C/C++ source files without any extensions
ADDFILES =

# CHANGEME: Put any additional libraries here.
LIBS =

# CHANGEME: Additional flags for compilation (e.g., include flags)
CFLAGS = 

# CHANGEME: Additional options specific to VRP

##############################################################################
# This section is for CONCORDE
##############################################################################

##############################################################################
# This solver can use separation routines from CONCORDE, the
# TSP solver of Applegate, Bixby, Chvatal, and Cook. To enable this option:
# 1. set the variables DO_CONCORDE_CUTS to TRUE. 
# 2. Download the source code for CONCORDE and the qsopt LP solver from 
#    http://www.tsp.gatech.edu.
# 3. Put qsopt.a and qsopt.h in ~/lib (make the directory if it doesn't exist).
# 4. Put a copy of qsopt.h in ~/include (make this directory if it doesn't 
#    exist).
#.5. Rename qsopt.a libqsopt.a (so it is detected as a library).
# 6. Build concorde with qsopt as the LP solver (configure --with-qsopt=~/lib).
# 7. Move the resulting library concorde.a to ~/lib and rename it 
#    libconcorde.a (or create a soft link).
# 8. Put a copy of concorde.h in ~/include (or create a soft link).
# 9. Make the CNRP application as usual.
##############################################################################

DO_CONCORDE_CUTS = FALSE

ifeq ($(DO_CONCORDE_CUTS),TRUE)
ADDLIBS += -L${HOME}/lib -lconcorde -lqsopt
ADDINCFLAGS += -I${HOME}/include 
endif
##############################################################################
#  Usually, you don't have to change anything below this point.          
##############################################################################

##############################################################################
# This section is for listing source file names
##############################################################################

USER_COMMON_FILES   = vrp_macros compute_cost network vrp_dg_functions

USER_MASTER_FILES   = vrp_main vrp_master vrp_io vrp_master_functions \
	              small_graph 

USER_TM_FILES 	   = 

USER_LP_FILES       = vrp_lp_branch vrp_lp 

USER_CG_FILES       = vrp_cg biconnected shrink 
ifeq ($(DO_CONCORDE_CUTS),TRUE)
USER_CG_FILES      += tsp # $(TSP_FILES)
endif

USER_CP_FILES       = vrp_cp 

USER_DG_FILES       = vrp_dg vrp_dg_network 

ifeq ($(DO_CONCORDE_CUTS),TRUE)
ADDINCFLAGS += -DDO_TSP_CUTS
endif

include ../Makefile.Applications
