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

## $Id: Makefile.am 387 2006-06-22 23:15:50Z menal $

AUTOMAKE_OPTIONS = foreign

##############################################################################
##############################################################################
# Global source files
##############################################################################
##############################################################################

SYMHEADERS = \
	../include/sym_constants.h \
	../include/sym_macros.h \
	../include/sym_types.h \
	../include/sym_cg.h \
	../include/sym_cg_params.h \
	../include/sym_cg_u.h \
	../include/sym_cp.h \
	../include/sym_cp_params.h \
	../include/sym_cp_u.h \
	../include/sym_dg.h \
	../include/sym_dg_params.h \
	../include/sym_dg_u.h \
	../include/sym_lp.h \
	../include/sym_lp_params.h \
	../include/sym_lp_solver.h \
	../include/sym_lp_u.h \
	../include/sym_master.h \
	../include/sym_master_params.h \
	../include/sym_master_u.h \
	../include/sym_messages.h \
	../include/sym_pack_array.h \
	../include/sym_pack_cut.h \
	../include/sym_proccomm.h \
	../include/sym_proto.h \
	../include/sym_qsort.h \
	../include/sym_return_values.h \
	../include/symphony.h \
	../include/symphony_api.h \
	../include/sym_timemeas.h \
	../include/sym_tm.h \
	../include/sym_tm_params.h \
	../include/sym_primal_heuristics.h \
	../include/sym_prep.h  \
	../include/sym_prep_params.h

if COIN_CXX_IS_CL
 SYMHEADERS += ../include/sym_win32_time.h
endif


#Add SymConfig.h
SYMINCFILES = ../include/SymConfig.h $(SYMHEADERS)

SYM_MASTER_SRC	= Master/master.c Master/master_wrapper.c Master/master_io.c \
	Master/master_func.c Master/master_prep.c Master/master_prep_base.c Master/master_prep_sr.c 

MASTER_SRC =$(SYM_MASTER_SRC)

MASTER_MAIN_SRC     = Master/main.c

DG_SRC		= DrawGraph/draw_graph.c

SYM_TM_SRC = TreeManager/tm_func.c TreeManager/tm_proccomm.c

if SYM_COMPILE_IN_TM
TM_SRC		= TreeManager/tm_func.c TreeManager/tm_proccomm.c
else
TM_SRC          = TreeManager/treemanager.c TreeManager/tm_func.c \
	TreeManager/tm_proccomm.c
endif

SYM_LP_SRC = LP/lp_solver.c LP/lp_varfunc.c LP/lp_rowfunc.c \
	LP/lp_genfunc.c LP/lp_proccomm.c LP/lp_wrapper.c LP/lp_free.c LP/lp_sp.c \
	LP/lp_heuristics.c
if PSEUDO_COSTS
SYM_LP_SRC += LP/lp_pseudo_branch.c
else
SYM_LP_SRC += LP/lp_branch.c
endif

SYM_CG_SRC = CutGen/cg_func.c CutGen/cg_wrapper.c
SYM_CP_SRC = CutPool/cp_proccomm.c CutPool/cp_func.c CutPool/cp_wrapper.c

if SYM_COMPILE_IN_LP
TM_SRC         += LP/lp_solver.c LP/lp_varfunc.c LP/lp_rowfunc.c \
	LP/lp_genfunc.c
TM_SRC         += LP/lp_proccomm.c LP/lp_wrapper.c LP/lp_free.c
if PSEUDO_COSTS
TM_SRC         += LP/lp_pseudo_branch.c
else
TM_SRC         += LP/lp_branch.c
endif
if SYM_COMPILE_IN_CG
TM_SRC         += CutGen/cg_func.c CutGen/cg_wrapper.c
endif
else
MASTER_SRC += LP/lp_solver.c
endif

if SYM_COMPILE_IN_CP
TM_SRC	       += CutPool/cp_proccomm.c CutPool/cp_func.c CutPool/cp_wrapper.c
endif
if SYM_COMPILE_IN_TM
MASTER_SRC     += $(TM_SRC)
endif

LP_SRC		= LP/lp_solver.c LP/lp_varfunc.c LP/lp_rowfunc.c \
	LP/lp_genfunc.c LP/lp_proccomm.c LP/lp_wrapper.c LP/lp.c LP/lp_free.c LP/lp_sp.c \
	LP/lp_heuristics.c
if PSEUDO_COSTS
LP_SRC         += LP/lp_pseudo_branch.c
else
LP_SRC         += LP/lp_branch.c
endif

if SYM_COMPILE_IN_CG
LP_SRC         += CutGen/cg_func.c CutGen/cg_wrapper.c
endif

CP_SRC		= CutPool/cut_pool.c CutPool/cp_proccomm.c CutPool/cp_func.c \
	CutPool/cp_wrapper.c

CG_SRC		= CutGen/cut_gen.c CutGen/cg_proccomm.c CutGen/cg_func.c \
	CutGen/cg_wrapper.c

QSORT_SRC	= Common/sym_qsort.c 
TIME_SRC	= Common/timemeas.c
PROCCOMM_SRC	= Common/proccomm.c
PACKCUT_SRC	= Common/pack_cut.c
PACKARRAY_SRC	= Common/pack_array.c

BB_SRC = $(MASTER_SRC) $(DG_SRC) $(TM_SRC) $(LP_SRC) $(CP_SRC) $(CG_SRC) \
	 $(QSORT_SRC) $(TIME_SRC) $(PROCCOMM_SRC) $(PACKCUT_SRC) \
	 $(PACKARRAY_SRC) 

ALL_SRC = $(BB_SRC)

ALL_SYM_MASTER = $(SYM_MASTER_SRC) $(SYM_TM_SRC) $(SYM_LP_SRC) $(SYM_CG_SRC) \
	$(SYM_CP_SRC) $(TIME_SRC) $(QSORT_SRC) $(PROCCOMM_SRC) $(PACKCUT_SRC) \
	$(PACKARRAY_SRC) 

ALL_MASTER	 = $(MASTER_SRC)
ALL_MASTER 	+= $(TIME_SRC)
ALL_MASTER 	+= $(QSORT_SRC)
ALL_MASTER 	+= $(PROCCOMM_SRC)
ALL_MASTER 	+= $(PACKCUT_SRC)
ALL_MASTER 	+= $(PACKARRAY_SRC)

ALL_LP	 = $(LP_SRC)
ALL_LP 	+= $(TIME_SRC)
ALL_LP 	+= $(QSORT_SRC)
ALL_LP 	+= $(PROCCOMM_SRC)
ALL_LP 	+= $(PACKCUT_SRC)
ALL_LP 	+= $(PACKARRAY_SRC)

ALL_TM	 = $(TM_SRC)
ALL_TM 	+= $(TIME_SRC)
ALL_TM 	+= $(PROCCOMM_SRC)
ALL_TM 	+= $(PACKCUT_SRC)
ALL_TM 	+= $(PACKARRAY_SRC)
if SYM_COMPILE_IN_LP
ALL_TM  += $(QSORT_SRC)
endif

ALL_CG	 = $(CG_SRC)
ALL_CG 	+= $(TIME_SRC)
ALL_CG 	+= $(QSORT_SRC)
ALL_CG 	+= $(PROCCOMM_SRC)
ALL_CG 	+= $(PACKCUT_SRC)

ALL_CP	 = $(CP_SRC)
ALL_CP 	+= $(TIME_SRC)
ALL_CP 	+= $(QSORT_SRC)
ALL_CP 	+= $(PROCCOMM_SRC)
ALL_CP 	+= $(PACKCUT_SRC)

MAIN_SRC = $(MASTER_MAIN_SRC)

USER_APPL_DIR = ../Applications/USER/src/

USER_APPL_STUBS_SRC = $(USER_APPL_DIR)/Master/user_master.c \
	$(USER_APPL_DIR)/LP/user_lp.c \
	$(USER_APPL_DIR)/LP/user_lp_branch.c \
	$(USER_APPL_DIR)/CutGen/user_cg.c \
	$(USER_APPL_DIR)/CutPool/user_cp.c \
	$(USER_APPL_DIR)/DrawGraph/user_dg.c

##############################################################################
#  Extensions and filenames for various configurations
##############################################################################

# if SYM_COMPILE_IN_CG
# LPEXT = _cg
# endif
# if SYM_COMPILE_IN_CP
# CPEXT = _cp
# endif
# if SYM_COMPILE_IN_LP
# TMEXT = _lp$(LPEXT)$(CPEXT)
# else
# TMEXT = $(CPEXT)
# endif
# if SYM_COMPILE_IN_TM
# MASTEREXT = _m_tm$(TMEXT)
# endif

# LIBNAME = Sym
# MASTERNAME = symphony

# if SYM_PARALLEL
# MASTERLIBNAME = $(LIBNAME)$(MASTEREXT)
# MASTERBIN = $(MASTERNAME)$(MASTEREXT)
# else
# MASTERLIBNAME = $(LIBNAME)
# MASTERBIN = $(MASTERNAME)
# endif

########################################################################
#                           Common Flags                               #
########################################################################

SYMCPPFLAGS =
PCPPFLAGS =
APPLCPPFLAGS =
APPLPCPPFLAGS =
ALLLDADD =
PLDADD =
LDADD = $(SYMPHONYLIB_LIBS)
DEPENDENCIES = $(SYMPHONYLIB_DEPENDENCIES)
AM_CPPFLAGS = $(SYMPHONYLIB_CFLAGS)

if CLP_LP_SOLVER
  AM_CPPFLAGS += -D__OSI_CLP__
endif

if CPLEX_LP_SOLVER
  AM_CPPFLAGS += -D__OSI_CPLEX__
endif

if GLPK_LP_SOLVER
  AM_CPPFLAGS += -D__OSI_GLPK__
else 
if USE_GMPL
  AM_CPPFLAGS += -DUSE_GLPMPL
endif
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

if COIN_HAS_READLINE
AM_CPPFLAGS += -DHAS_READLINE
endif

if SENSITIVITY_ANALYSIS
AM_CPPFLAGS += -DSENSITIVITY_ANALYSIS
endif

if USE_CGL_CUTS
AM_CPPFLAGS += -DUSE_CGL_CUTS
endif

if ROOT_NODE_ONLY
AM_CPPFLAGS += -DROOT_NODE_ONLY
endif

if COMPILE_FRAC_BRANCHING
AM_CPPFLAGS += -DCOMPILE_FRAC_BRANCHING
endif

if DO_TESTS
AM_CPPFLAGS += -DDO_TESTS
endif

if TM_BASIS_TESTS
AM_CPPFLAGS += -DTM_BASIS_TESTS
endif

if TRACE_PATH
AM_CPPFLAGS += -DTRACE_PATH
endif

if CHECK_CUT_VALIDITY
AM_CPPFLAGS += -DCHECK_CUT_VALIDITY
endif

if STATISTICS
AM_CPPFLAGS += -DSTATISTICS
endif

if PSEUDO_COSTS
AM_CPPFLAGS += -DPSEUDO_COSTS
endif

if DRAWGRAPH
AM_CPPFLAGS += 
endif

if SIGHANDLER
AM_CPPFLAGS += -DSIGHANDLER
endif

SYMCPPFLAGS += $(AM_CPPFLAGS) $(SYMDEFS)

if SYM_PARALLEL
PCPPFLAGS += $(AM_CPPFLAGS) $(SYMPDEFS) -I`$(CYGPATH_W) $(PVM_ROOT)/include`
PLDADD += $(LDADD) -lgpvm3 -lpvm3
APPLPCPPFLAGS += $(PCPPFLAGS) -DUSE_SYM_APPLICATION
endif

APPLCPPFLAGS += $(SYMCPPFLAGS) -DUSE_SYM_APPLICATION

DEFAULT_INCLUDES = -I. -I`$(CYGPATH_W) $(top_srcdir)/include` \
                   -I`$(CYGPATH_W) $(top_builddir)/include`

if DEPENDENCY_LINKING
DEFAULT_INCLUDES += -I`$(CYGPATH_W) $(top_srcdir)/Applications/USER/include`
endif

########################################################################
########################################################################

# Compile everything with g++
CC = $(CXX)
CCLD = $(CXX)

#Static link
STATIC_LINK =  $(LIBTOOL) --tag=CXX --mode=link $(CCLD) -all-static\
	$(AM_CFLAGS) $(CFLAGS) $(AM_LDFLAGS) $(LDFLAGS) -o $@

# Link with g++
LINK =
if STATICEXE
LINK +=  $(STATIC_LINK) 
else
LINK += $(LIBTOOL) --tag=CXX --mode=link $(CCLD) $(AM_CFLAGS) $(CFLAGS) \
	$(AM_LDFLAGS) $(LDFLAGS) -o $@ -rpath $(libdir)
# the rpath seem to be necessary to have a .lai file created, which is necessary for installing libraries
endif

SYMLINK =
if COIN_CXX_IS_CL
SYMLINK += cp -f main.$(OBJEXT) symphony-main.$(OBJEXT); $(LIBTOOL) \
	--tag=CXX --mode=link $(CCLD) $(AM_CFLAGS) $(CCLCFLAGS) \
	$(AM_LDFLAGS) $(LDFLAGS) -o $@
else
SYMLINK += $(LINK)
endif

########################################################################
#                               libSym                                 #
########################################################################

EXTRA_LTLIBRARIES = libSym.la libSym_cg.la libSym_lp.la libSym_lp_cg.la \
	libSym_tm.la libSym_tm_lp.la libSym_tm_cp.la libSym_tm_lp_cg.la \
	libSym_tm_lp_cg_cp.la libSym_m_tm.la libSym_m_tm_lp.la \
	libSym_m_tm_cp.la libSym_m_tm_lp_cg.la libSym_m_tm_lp_cg_cp.la \
	libSym_cp.la libSymAppl.la libSymAppl_cg.la libSymAppl_lp.la \
	libSymAppl_lp_cg.la libSymAppl_tm.la libSymAppl_tm_lp.la \
	libSymAppl_tm_cp.la libSymAppl_tm_lp_cg.la libSymAppl_tm_lp_cg_cp.la \
	libSymAppl_m_tm.la libSymAppl_m_tm_lp.la libSymAppl_m_tm_cp.la \
	libSymAppl_m_tm_lp_cg.la libSymAppl_m_tm_lp_cg_cp.la \
	libSymAppl_cp.la libSym_m.la libSymApplStubs.la libSymAppl_m.la 
#$(WHATTOMAKELIBS) $(WHATTOMAKEBINS)
#if !SYM_PARALLEL

# Name of the library compiled in this directory.  We want it to be installed
# in the 'lib' directory
lib_LTLIBRARIES = $(WHATTOINSTALLLIBS)

# List all source files for this library, including headers
libSym_la_SOURCES = $(SYMINCFILES) $(ALL_SYM_MASTER)
libSym_m_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSym_m_tm_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSym_m_tm_lp_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSym_m_tm_cp_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSym_m_tm_lp_cg_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSym_m_tm_lp_cg_cp_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSym_lp_la_SOURCES = $(SYMINCFILES) $(ALL_LP)
libSym_lp_cg_la_SOURCES = $(SYMINCFILES) $(ALL_LP)
libSym_cg_la_SOURCES = $(SYMINCFILES) $(ALL_CG)
libSym_cp_la_SOURCES = $(SYMINCFILES) $(ALL_CP)
libSym_tm_la_SOURCES = $(SYMINCFILES) $(ALL_TM)
libSym_tm_lp_la_SOURCES = $(SYMINCFILES) $(ALL_TM)
libSym_tm_lp_cg_la_SOURCES = $(SYMINCFILES) $(ALL_TM)
libSym_tm_lp_cg_cp_la_SOURCES = $(SYMINCFILES) $(ALL_TM)
libSym_tm_cp_la_SOURCES = $(SYMINCFILES) $(ALL_TM)

libSym_la_CPPFLAGS = $(SYMCPPFLAGS)
libSym_m_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_m_tm_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_m_tm_lp_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_m_tm_cp_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_m_tm_lp_cg_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_m_tm_lp_cg_cp_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_lp_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_lp_cg_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_cg_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_cp_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_tm_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_tm_lp_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_tm_lp_cg_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_tm_lp_cg_cp_la_CPPFLAGS = $(PCPPFLAGS) 
libSym_tm_cp_la_CPPFLAGS = $(PCPPFLAGS) 

libSym_lp_la_LINK = $(STATIC_LINK)
libSym_lp_cg_la_LINK = $(STATIC_LINK)
libSym_cg_la_LINK = $(STATIC_LINK)
libSym_cp_la_LINK = $(STATIC_LINK)
libSym_tm_la_LINK = $(STATIC_LINK)
libSym_tm_lp_la_LINK = $(STATIC_LINK)
libSym_tm_lp_cg_la_LINK = $(STATIC_LINK)
libSym_tm_lp_cg_cp_la_LINK = $(STATIC_LINK)
libSym_tm_cp_la_LINK = $(STATIC_LINK)

libSym_la_LDFLAGS = $(LT_LDFLAGS)
libSym_m_la_LDFLAGS = $(LT_LDFLAGS)
libSym_m_tm_la_LDFLAGS = $(LT_LDFLAGS)
libSym_m_tm_lp_la_LDFLAGS = $(LT_LDFLAGS)
libSym_m_tm_cp_la_LDFLAGS = $(LT_LDFLAGS)
libSym_m_tm_lp_cg_la_LDFLAGS = $(LT_LDFLAGS)
libSym_m_tm_lp_cg_cp_la_LDFLAGS = $(LT_LDFLAGS)
libSym_lp_la_LDFLAGS = $(LT_LDFLAGS)
libSym_lp_cg_la_LDFLAGS = $(LT_LDFLAGS)
libSym_cg_la_LDFLAGS = $(LT_LDFLAGS)
libSym_cp_la_LDFLAGS = $(LT_LDFLAGS)
libSym_tm_la_LDFLAGS = $(LT_LDFLAGS)
libSym_tm_lp_la_LDFLAGS = $(LT_LDFLAGS)
libSym_tm_lp_cg_la_LDFLAGS = $(LT_LDFLAGS)
libSym_tm_lp_cg_cp_la_LDFLAGS = $(LT_LDFLAGS)
libSym_tm_cp_la_LDFLAGS = $(LT_LDFLAGS)

# List all additionally required libraries
if DEPENDENCY_LINKING
libSym_la_LIBADD = $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
endif

########################################################################
#                        symphony program                              #
########################################################################

EXTRA_PROGRAMS = symphony symphony_m symphony_m_tm symphony_m_tm_lp \
	symphony_m_tm_cp \
	symphony_m_tm_lp_cg symphony_m_tm_lp_cg_cp symphony_cp symphony_lp \
	symphony_lp_cg symphony_lp_cg_cp symphony_tm symphony_tm_cp \
	symphony_tm_lp 	symphony_tm_lp_cg symphony_tm_lp_cg_cp 

# # # Name of the executable compiled in this directory.  We want it to be
# # # installed in the 'bin' directory

bin_PROGRAMS = $(WHATTOMAKEBINS)

symphony_SOURCES = $(MAIN_SRC) symphony.h
#symphony_DEPENDENCIES = $(SYMLDADD) libSym.la
symphony_CPPFLAGS = $(SYMCPPFLAGS)
symphony_LDADD = libSym.la $(LDADD) $(ADDLIBS)
symphony_DEPENDENCIES = libSym.la $(DEPENDENCIES)
symphony_LINK = $(SYMLINK)

symphony_m_SOURCES = $(MAIN_SRC) symphony.h
#symphony_m_DEPENDENCIES = $(LDADD) libSym$(MASTEREXT).la
symphony_m_CPPFLAGS = $(PCPPFLAGS)
symphony_m_LDADD = libSym$(MASTEREXT).la $(PLDADD)
symphony_m_DEPENDENCIES = libSym$(MASTEREXT).la $(DEPENDENCIES)

symphony_m_tm_SOURCES = $(MAIN_SRC) symphony.h
#symphony_m_tm_DEPENDENCIES = $(LDADD) libSym$(MASTEREXT).la
symphony_m_tm_CPPFLAGS = $(PCPPFLAGS)
symphony_m_tm_LDADD = libSym$(MASTEREXT).la $(PLDADD)
symphony_m_tm_DEPENDENCIES = libSym$(MASTEREXT).la $(DEPENDENCIES)

symphony_m_tm_lp_SOURCES = $(MAIN_SRC) symphony.h
#symphony_m_tm_lp_DEPENDENCIES = $(LDADD) libSym$(MASTEREXT).la
symphony_m_tm_lp_CPPFLAGS = $(PCPPFLAGS)
symphony_m_tm_lp_LDADD = libSym$(MASTEREXT).la libSym.la $(PLDADD)
symphony_m_tm_lp_DEPENDENCIES = libSym$(MASTEREXT).la libSym.la $(DEPENDENCIES)

symphony_m_tm_cp_SOURCES = $(MAIN_SRC) symphony.h
#symphony_m_tm_cp_DEPENDENCIES = $(LDADD) libSym$(MASTEREXT).la
symphony_m_tm_cp_CPPFLAGS = $(PCPPFLAGS)
symphony_m_tm_cp_LDADD = libSym$(MASTEREXT).la $(PLDADD)
symphony_m_tm_cp_DEPENDENCIES = libSym$(MASTEREXT).la $(DEPENDENCIES)

symphony_m_tm_lp_cg_SOURCES = $(MAIN_SRC) symphony.h
#symphony_m_tm_lp_cg_DEPENDENCIES = $(LDADD) libSym$(MASTEREXT).la
symphony_m_tm_lp_cg_CPPFLAGS = $(PCPPFLAGS)
symphony_m_tm_lp_cg_LDADD = libSym$(MASTEREXT).la libSym.la $(PLDADD)
symphony_m_tm_lp_cg_DEPENDENCIES = libSym$(MASTEREXT).la libSym.la $(DEPENDENCIES)

symphony_m_tm_lp_cg_cp_SOURCES = $(MAIN_SRC) symphony.h
#symphony_m_tm_lp_cg_cp_DEPENDENCIES = $(LDADD) libSym$(MASTEREXT).la
symphony_m_tm_lp_cg_cp_CPPFLAGS = $(PCPPFLAGS)
symphony_m_tm_lp_cg_cp_LDADD = libSym$(MASTEREXT).la libSym.la $(PLDADD)
symphony_m_tm_lp_cg_cp_DEPENDENCIES = libSym$(MASTEREXT).la libSym.la $(DEPENDENCIES)

symphony_tm_SOURCES =
#symphony_tm_DEPENDENCIES = $(LDADD) libSym_tm$(TMEXT).la
symphony_tm_CPPFLAGS = $(PCPPFLAGS)
symphony_tm_LDADD = libSym_tm$(TMEXT).la $(PLDADD)
symphony_tm_DEPENDENCIES = libSym_tm$(TMEXT).la $(DEPENDENCIES)

symphony_tm_lp_SOURCES =
#symphony_tm_lp_DEPENDENCIES = $(LDADD) libSym_tm$(TMEXT).la
symphony_tm_lp_CPPFLAGS = $(PCPPFLAGS)
symphony_tm_lp_LDADD = libSym_tm$(TMEXT).la libSym.la $(PLDADD)
symphony_tm_lp_DEPENDENCIES = libSym_tm$(TMEXT).la libSym.la $(DEPENDENCIES)

symphony_tm_cp_SOURCES =
#symphony_tm_cp_DEPENDENCIES = $(LDADD) libSym_tm$(TMEXT).la
symphony_tm_cp_CPPFLAGS = $(PCPPFLAGS)
symphony_tm_cp_LDADD = libSym_tm$(TMEXT).la $(PLDADD)
symphony_tm_cp_DEPENDENCIES = libSym_tm$(TMEXT).la $(DEPENDENCIES)

symphony_tm_lp_cg_SOURCES =
#symphony_tm_lp_cg_DEPENDENCIES = $(LDADD) libSym_tm$(TMEXT).la
symphony_tm_lp_cg_CPPFLAGS = $(PCPPFLAGS)
symphony_tm_lp_cg_LDADD = libSym_tm$(TMEXT).la libSym.la $(PLDADD)
symphony_tm_lp_cg_DEPENDENCIES = libSym_tm$(TMEXT).la libSym.la $(DEPENDENCIES)

symphony_tm_lp_cg_cp_SOURCES =
#symphony_tm_lp_cg_cp_DEPENDENCIES = $(LDADD) libSym_tm$(TMEXT).la
symphony_tm_lp_cg_cp_CPPFLAGS = $(PCPPFLAGS)
symphony_tm_lp_cg_cp_LDADD = libSym_tm$(TMEXT).la libSym.la $(PLDADD)
symphony_tm_lp_cg_cp_DEPENDENCIES = libSym_tm$(TMEXT).la libSym.la $(DEPENDENCIES)

symphony_cp_SOURCES =
#symphony_cp_DEPENDENCIES = $(LDADD) libSym_cp.la
symphony_cp_CPPFLAGS = $(PCPPFLAGS)
symphony_cp_LDADD = libSym_cp.la $(PLDADD)
symphony_cp_DEPENDENCIES = libSym_cp.la $(DEPENDENCIES)

symphony_lp_SOURCES =
#symphony_lp_DEPENDENCIES = $(LDADD) 
symphony_lp_CPPFLAGS = $(PCPPFLAGS)
symphony_lp_LDADD = libSym_lp$(LPEXT).la libSym.la $(PLDADD)
symphony_lp_DEPENDENCIES = libSym_lp$(LPEXT).la libSym.la $(DEPENDENCIES)

symphony_lp_cg_SOURCES =
#symphony_lp_cg_DEPENDENCIES = $(LDADD) libSym_lp$(LPEXT).la 
symphony_lp_cg__CPPFLAGS = $(PCPPFLAGS)
symphony_lp_cg_LDADD = libSym_lp$(LPEXT).la libSym.la $(PLDADD)
symphony_lp_cg_DEPENDENCIES = libSym_lp$(LPEXT).la libSym.la $(DEPENDENCIES)

symphony_lp_cg_cp_SOURCES =
#symphony_lp_cg_cp_DEPENDENCIES = $(LDADD) libSym_lp$(LPEXT).la
symphony_lp_cg_cp__CPPFLAGS = $(PCPPFLAGS)
symphony_lp_cg_cp_LDADD = libSym_lp$(LPEXT).la libSym.la $(PLDADD)
symphony_lp_cg_cp_DEPENDENCIES = libSym_lp$(LPEXT).la libSym.la $(DEPENDENCIES)

########################################################################
#                Application Library                                   #    
########################################################################

libSymAppl_la_SOURCES = $(SYMINCFILES) $(ALL_SYM_MASTER)
libSymAppl_m_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSymAppl_m_tm_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSymAppl_m_tm_lp_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSymAppl_m_tm_cp_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSymAppl_m_tm_lp_cg_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSymAppl_m_tm_lp_cg_cp_la_SOURCES = $(SYMINCFILES) $(ALL_MASTER)
libSymAppl_lp_la_SOURCES = $(SYMINCFILES) $(ALL_LP)
libSymAppl_lp_cg_la_SOURCES = $(SYMINCFILES) $(ALL_LP)
libSymAppl_cg_la_SOURCES = $(SYMINCFILES) $(ALL_CG)
libSymAppl_cp_la_SOURCES = $(SYMINCFILES) $(ALL_CP)
libSymAppl_tm_la_SOURCES = $(SYMINCFILES) $(ALL_TM)
libSymAppl_tm_lp_la_SOURCES = $(SYMINCFILES) $(ALL_TM)
libSymAppl_tm_lp_cg_la_SOURCES = $(SYMINCFILES) $(ALL_TM)
libSymAppl_tm_lp_cg_cp_la_SOURCES = $(SYMINCFILES) $(ALL_TM)
libSymAppl_tm_cp_la_SOURCES = $(SYMINCFILES) $(ALL_TM)

libSymAppl_lp_la_LINK = $(STATIC_LINK)
libSymAppl_lp_cg_la_LINK = $(STATIC_LINK)
libSymAppl_cg_la_LINK = $(STATIC_LINK)
libSymAppl_cp_la_LINK = $(STATIC_LINK)
libSymAppl_tm_la_LINK = $(STATIC_LINK)
libSymAppl_tm_lp_la_LINK = $(STATIC_LINK)
libSymAppl_tm_lp_cg_la_LINK = $(STATIC_LINK)
libSymAppl_tm_lp_cg_cp_la_LINK = $(STATIC_LINK)
libSymAppl_tm_cp_la_LINK = $(STATIC_LINK)

libSymAppl_la_LDFLAGS = $(LT_LDFLAGS) 
libSymAppl_m_la_LDFLAGS = $(LT_LDFLAGS) 
libSymAppl_m_tm_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_m_tm_lp_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_m_tm_cp_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_m_tm_lp_cg_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_m_tm_lp_cg_cp_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_lp_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_lp_cg_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_cg_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_cp_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_tm_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_tm_lp_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_tm_lp_cg_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_tm_lp_cg_cp_la_LDFLAGS = $(LT_LDFLAGS)
libSymAppl_tm_cp_la_LDFLAGS = $(LT_LDFLAGS)

libSymAppl_la_CPPFLAGS = $(APPLCPPFLAGS) 
libSymAppl_m_la_CPPFLAGS = $(APPLPCPPFLAGS) 
libSymAppl_m_tm_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_m_tm_lp_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_m_tm_cp_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_m_tm_lp_cg_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_m_tm_lp_cg_cp_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_lp_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_lp_cg_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_cg_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_cp_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_tm_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_tm_lp_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_tm_lp_cg_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_tm_lp_cg_cp_la_CPPFLAGS = $(APPLPCPPFLAGS)
libSymAppl_tm_cp_la_CPPFLAGS = $(APPLPCPPFLAGS)

# List all additionally required libraries
if DEPENDENCY_LINKING
libSymAppl_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_m_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_m_tm_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_m_tm_lp_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_m_tm_cp_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_m_tm_lp_cg_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_m_tm_lp_cg_cp_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_lp_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_lp_cg_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_cg_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_cp_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_tm_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_tm_lp_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_tm_lp_cg_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_tm_lp_cg_cp_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
libSymAppl_tm_cp_la_LIBADD = libSymApplStubs.la $(SYMPHONYLIB_LIBS) $(SYM_OPENMP_LIBS)
endif

########################################################################
#     A Dummy Library with Stubs for User Callbacks                    #
#       (We need this to do dependency linking)                        #
########################################################################

libSymApplStubs_la_SOURCES = $(SYMINCFILES) $(USER_APPL_DIR)/include/user.h \
	                     $(USER_APPL_STUBS_SRC)
libSymApplStubs_lp_la_LINK = $(STATIC_LINK)
libSymApplStubs_la_LDFLAGS = $(LT_LDFLAGS) 
libSymApplStubs_la_CPPFLAGS = $(APPLCPPFLAGS) 

########################################################################
#                Other stuff                                           #    
########################################################################

#COIN_WARNINGS = -pedantic-errors -Wimplicit -Wparentheses -Wreturn-type -Wcast-qual -Wall -Wpointer-arith -Wwrite-strings -Wconversion
# Get rid of warning flags
#FIXME-Try to have the following later
#CFLAGS := $(subst $(COIN_WARNINGS), ,$(CFLAGS))
#CXXFLAGS := $(subst $(COIN_WARNINGS), ,$(CXXFLAGS))

rename_obj:
	mv main.obj symphony-main.obj

########################################################################
#                Headers that need to be installed                     #
########################################################################

# Here list all the header files that are required by a user of the library,
# and that therefore should be installed in 'include/coin'
includecoindir = $(includedir)/coin
includecoin_HEADERS = ../include/symphony.h
#	$(SYMHEADERS)

########################################################################
#                     Installing manifest (MSVC++)                     #
########################################################################

if COIN_CXX_IS_CL
install-exec-hook:
	test -s symphony.exe.manifest && \
	mt -manifest symphony.exe.manifest -outputresource:symphony.exe;\
	cp symphony.exe $(bindir)/symphony.exe
endif

#######################################################################
# Create the Config.h file that has all public defines and install it #
#######################################################################

install-exec-local:
	$(install_sh_DATA) ../include/config_sym.h $(DESTDIR)$(includecoindir)/SymConfig.h

uninstall-local:
	rm -f $(DESTDIR)$(includecoindir)/SymConfig.h
