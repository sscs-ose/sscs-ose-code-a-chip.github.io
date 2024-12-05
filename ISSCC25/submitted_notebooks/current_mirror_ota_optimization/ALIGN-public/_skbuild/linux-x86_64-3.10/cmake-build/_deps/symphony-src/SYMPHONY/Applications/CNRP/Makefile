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

MASTERNAME = cnrp

SYMAPPLNAME = CNRP

# CHANGEME: Additional sources
# - Names of your additional C/C++ source files without any extensions
ADDFILES =

# CHANGEME: Put any additional libraries here.
LIBS =

# CHANGEME: Additional flags for compilation (e.g., include flags)
CFLAGS = 

# CHANGEME: Additional options specific to CNRP

##############################################################################
#Whether to solve problem as a multi-criteria (fixed vs. variable cost)
#or single-criteria problem
##############################################################################

MULTI_CRITERIA = FALSE

##############################################################################
#Whether to use the model with two oppositely oriented copies of each 
#fixed-chrage variable (one for each direction) or just a single undirected 
#copy. 
##############################################################################

DIRECTED_X_VARS = TRUE

##############################################################################
#Whether to add the flow variables (these are needed to model the variable costs)
##############################################################################

ADD_FLOW_VARS = TRUE

##############################################################################
#Whether to add capacity cuts to the model 
##############################################################################

ADD_CAP_CUTS = FALSE

##############################################################################
#Whether to add "X" cuts to the model 
##############################################################################

ADD_X_CUTS = FALSE

##############################################################################
#Whether to save the global cut pool between iterations when using warm 
#starting 
##############################################################################

SAVE_CUT_POOL = TRUE

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
LIBS += -L${HOME}/lib -lconcorde -lqsopt
CFLAGS += -I${HOME}/include 
endif

##########################################################################
#  Usually, you don't have to change anything below this point.          #
##########################################################################

##############################################################################
# This section is for listing source file names
##############################################################################

USER_COMMON_FILES   = cnrp_macros compute_cost network cnrp_dg_functions

USER_MASTER_FILES   = cnrp_main cnrp_master cnrp_io cnrp_master_functions \
	              small_graph 

USER_TM_FILES 	   = 

USER_LP_FILES       = cnrp_lp_branch cnrp_lp 

USER_CG_FILES       = cnrp_cg biconnected shrink 
ifeq ($(DO_CONCORDE_CUTS),TRUE)
USER_CG_FILES      += tsp # $(TSP_FILES)
endif

USER_CP_FILES       = cnrp_cp 

USER_DG_FILES       = cnrp_dg cnrp_dg_network 

ifeq ($(MULTI_CRITERIA),TRUE)
CFLAGS += -DMULTI_CRITERIA
endif

ifeq ($(ADD_FLOW_VARS),TRUE)
CFLAGS += -DADD_FLOW_VARS
ifeq ($(ADD_CAP_CUTS),TRUE)
CFLAGS += -DADD_CAP_CUTS
endif
endif

ifeq ($(DIRECTED_X_VARS),TRUE)
CFLAGS += -DDIRECTED_X_VARS
ifeq ($(ADD_X_CUTS),TRUE)
CFLAGS += -DADD_X_CUTS
endif
endif

ifeq ($(SAVE_CUT_POOL),TRUE)
CFLAGS += -DSAVE_CUT_POOL
endif

ifeq ($(DO_CONCORDE_CUTS),TRUE)
CFLAGS += -DDO_TSP_CUTS
endif

include ../Makefile.Applications