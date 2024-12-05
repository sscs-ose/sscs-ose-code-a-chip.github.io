##############################################################################
##############################################################################
#                                                                            #
# This file is part of the SYMPHONY MILP Solver Framework.                   #
#                                                                            #
# SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and          #
# Laci Ladanyi (ladanyi@us.ibm.com).                                         #
#                                                                            #
# (c) Copyright 2005-2011,  Lehigh University. All Rights Reserved.          #
#                                                                            #
# This software is licensed under the Eclipse Public License. Please see     #
# accompanying file for terms.                                               #
#                                                                            #
# The author of this file is Menal Guzelsoy (megb@lehigh.edu)                #
#                                                                            #
##############################################################################
##############################################################################

CoinDir  := $(HOME)/COIN
SymDir  := $(CoinDir)/SYMPHONY
FlopcDir := $(CoinDir)/flopc
#LPSolverDir :=$(HOME)/OSL/osllib

CXX     =  g++

## Chose optimization level
CXXFLAGS += -O

##############################################################################
IncDir	:= $(FlopcDir)/include 
IncDir	+= $(CoinDir)/include 
IncDir	+= $(SymDir)/include 
#IncDir += $(LPSolverDir)/include

SHLINKPREFIX = -Wl,-rpath,

CXXFLAGS += $(addprefix -I,${IncDir})

LIBDIRS := $(CoinDir)/lib
LIBDIRS += $(FlopcDir)/lib
LIBDIRS += $(SymDir)/lib
#LIBDIRS += $(LPSolverDir)/lib

LDFLAGS := $(addprefix -L,$(LIBDIRS))
LDFLAGS += $(addprefix $(SHLINKPREFIX),$(LIBDIRS))

LIBS 	+= -lOsiSym
LIBS 	+= -lsym
LIBS	+= -lflopc
LIBS 	+= -lOsi
LIBS 	+= -lOsiClp
LIBS 	+= -lClp
#LIBS 	+= -lOsiOsl
#LIBS 	+= -losl
LIBS 	+= -lCoin
LIBS 	+= -lCgl
#LIBS 	+= -lgz

LDFLAGS	+= $(LIBS)

###############################################################################

.DELETE_ON_ERROR:

.PHONY: default

default: all

###############################################################################

all :	tap

clean:	
	@rm tap
###############################################################################
