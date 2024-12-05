##############################################################################
##############################################################################
#                                                                            #
# This file is part of the SYMPHONY Branch, Cut, and Price Library.          #
#                                                                            #
# SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and          #
# Laci Ladanyi (ladanyi@us.ibm.com).                                         #
#                                                                            #
# (c) Copyright 2005-2006 Ted Ralphs. All Rights Reserved.                   #
#                                                                            #
# This software is licensed under the Eclipse Public License. Please see     #
# accompanying file for terms.                                               #
#                                                                            #
##############################################################################
##############################################################################

##############################################################################
##############################################################################
#
# This makefile is for Microsoft Visual C++ usage only! In order to compile 
# this application, simply type the following command:
#
# nmake /f sym.mak 
#
# The executable "symphony.exe" for this application will be created in 
# .\Debug directory. By default, SYMPHONY is set up to use the CLP
# optimization solver via COIN_OSI's CLP interface and to use the CGL cuts. 
# However, you are free to  specify your own settings for the executable via 
# the following variables.
# (you can download nmake.exe from  "http://download.microsoft.com/download/
# vc15/Patch/1.52/W95/EN-US/Nmake15.exe" if you need that.)
# Note that the options here are for the compiler that comes with MSVC++
# Version 8. They may not work with earlier versions.
##############################################################################

##############################################################################
# The SYMPHONYROOT environment variable specifies the root directory for the 
# source code. If this file is not in the SYMPHONY root directory, change this
# variable to the correct path.
##############################################################################

SYMPHONYROOT=..\

##############################################################################
# COINROOT is the path to the root directory of the COIN libraries. Many of
# the new features of COIN require the COIN libraries to be installed.
##############################################################################

COINROOT = ..\..\

##############################################################################
# OUTDIR variable specifies where to create the executable file, 
# "symphony.exe", the corresponding objects and the dependencies.  
##############################################################################

OUTDIR=.\Debug

##############################################################################
##############################################################################
# LP solver dependent definitions
##############################################################################
##############################################################################

##############################################################################
##############################################################################
#You must define an LP solver in order to use the software. By default, this 
# option is set to OsI_CLP. See the corresponding "LPINCDIR" and "LPLIB" 
# variables used to put the lp solver include files and the libraries on path
# and make the necessary changes if you require.
##############################################################################
##############################################################################

##############################################################################
# CPLEX definitions
##############################################################################

# Uncomment the line below if you want to use CPLEX and specify the 
# corresponding paths to the solver files and libraries. 

#LP_SOLVER = CPLEX
!IF "$(LP_SOLVER)" == "CPLEX"
LPINCDIR = "C:\ILOG\cplex81\include\ilcplex"
LPLIB = "C:\ILOG\cplex81\lib\msvc6\stat_sta\cplex81.lib"
!ENDIF

##############################################################################
# OSL definitions
##############################################################################

# Uncomment the line below if you want to use OSL and specify the 
# corresponding paths to the solver files and libraries. 

#LP_SOLVER = OSL
!IF "$(LP_SOLVER)" == "OSL"
LPINCDIR = "C:\Program Files\IbmOslV3Lib\osllib\include"
LPLIB = "C:\Program Files\IbmOslV3Lib\osllib\lib\oslmd6030.lib"
!ENDIF

##############################################################################
# OSI definitions
##############################################################################

# Uncomment the line below if you want to use OSI interface and specify the 
# corresponding paths to the solver files and libraries. 

LP_SOLVER = OSI
OSI_INTERFACE = CLP

!IF "$(LP_SOLVER)" == "OSI"
LPINCDIR = \
	"$(COINROOT)\CoinUtils\src" /I\
	"$(COINROOT)\Osi\src"
LPLIB = \
	"$(COINROOT)\CoinUtils\MSVisualStudio\v8\libCoinUtils\Debug\libCoinUtils.lib" \
	"$(COINROOT)\Osi\MSVisualStudio\v8\libOsi\Debug\libOsi.lib"
!ENDIF


!IF "$(OSI_INTERFACE)" == "CPLEX"
LPINCDIR = $(LPINCDIR) /I\
	"C:\ILOG\cplex81\include\ilcplex" /I\
	"$(COINROOT)\Osi\src\OsiCpx"
LPLIB = $(LPLIB) \
	"C:\ILOG\cplex81\lib\msvc6\stat_sta\cplex81.lib" \
	"$(COINROOT)\Osi\MSVisualStudio\v8\libOsiCpx\Debug\libOsiCpx.lib"
!ENDIF


!IF "$(OSI_INTERFACE)" == "OSL"
LPINCDIR = $(LPINCDIR) /I\
	"C:\Program Files\IbmOslV3Lib\osllib\include" /I\
	"$(COINROOT)\Osi\src\OsiOsl"
LPLIB = $(LPLIB) \
	"C:\Program Files\IbmOslV3Lib\osllib\lib\oslmd6030.lib" \
        "$(COINROOT)\Osi\MSVisualStudio\v8\libOsiOsl\Debug\libOsiOsl.lib"
!ENDIF


!IF "$(OSI_INTERFACE)" == "CLP"
LPINCDIR = $(LPINCDIR) /I\
	"$(COINROOT)\Clp\src" /I\
	"$(COINROOT)\Osi\src\OsiClp"
LPLIB = $(LPLIB) \
	"$(COINROOT)\Clp\MSVisualStudio\v8\libClp\Debug\libClp.lib" \
	"$(COINROOT)\Osi\MSVisualStudio\v8\libOsiClp\Debug\libOsiClp.lib"
!ENDIF

!IF "$(OSI_INTERFACE)" == "XPRESS"
LPINCDIR = $(LPINCDIR) /I\
	"C:\" /I\
	"$(COINROOT)\Osi\src\OsiXpr"
LPLIB = $(LPLIB) \
	"C:\" \
	"$(COINROOT)\Osi\MSVisualStudio\v8\libOsiXpr\Debug\libOsiXpr.lib"
!ENDIF

!IF "$(OSI_INTERFACE)" == "SOPLEX"
LPINCDIR = $(LPINCDIR) /I\
	"C:\" /I\
	"$(COINROOT)\Osi\src\OsiSpx"
LPLIB = $(LPLIB) \
	"C:\" \
	"$(COINROOT)\Osi\MSVisualStudio\v8\libOsiSpx\Debug\libOsiSpx.lib"
!ENDIF

!IF "$(OSI_INTERFACE)" == "DYLP"
LPINCDIR = $(LPINCDIR) /I\
	"C:\" /I\
	"$(COINROOT)\Osi\src\OsiDylp"
LPLIB = $(LPLIB) \
	"C:\" \
	"$(COINROOT)\Osi\MSVisualStudio\v8\libOsiDylp\Debug\libOsiDylp.lib"
!ENDIF


!IF "$(OSI_INTERFACE)" == "GLPK"
LPINCDIR = $(LPINCDIR) /I\
	"C:\GLPK\glpk-4.0\include" /I\
	"$(COINROOT)\Osi\src\OsiGlpk"
LPLIB = $(LPLIB) \
	"C:\GLPK\glpk-4.0\glpk.lib" \
	"$(COINROOT)\Osi\MSVisualStudio\v8\libOsiGlpk\Debug\libOsiGlpk.lib"
!ENDIF


##############################################################################
# Besides the above variables, you have to set your environment path to solver
# specific dynamic libraries if there exists any. For instance, you have to 
# set your path to where "cplex81.dll" is, something like: 
#
#              "set path = %path%;C:\ILOG\cplex81\bin\msvc6 " 
#
# if you are using CPLEX 8.1 and Visual C++ 6. 
##############################################################################

##############################################################################
# SOLVER definition for SYMPHONY
##############################################################################

!IF "$(LP_SOLVER)" == "OSI"
DEFINITIONS ="__$(LP_SOLVER)_$(OSI_INTERFACE)__"
!ELSE
DEFINITIONS ="__$(LP_SOLVER)__"
!ENDIF

##############################################################################
# GLPMPL definitions. The user should set "USE_GLPMPL" variable to "TRUE" and 
# specify the paths for "glpk" files if she wants to read in glpmpl files.  
# Note that, the user has to also set the paths to GLPK packages. 
##############################################################################

USE_GLPMPL = FALSE

!IF "$(USE_GLPMPL)" == "TRUE"
LPINCDIR = $(LPINCDIR) /I\
	"C:\GLPK\glpk-4.0\include" /I\
	"$(COINROOT)\Osi\src\OsiGlpk\include"
LPLIB = $(LPLIB) \
	"C:\GLPK\glpk-4.0\glpk.lib" \
	"$(COINROOT)\Osi\MSVisualStudio\v8\libOsiGlpk\Debug\libOsiGlpk.lib"
!ENDIF


!IF "$(USE_GLPMPL)" == "TRUE"
DEFINITIONS = $(DEFINITIONS) /D "USE_GLPMPL"
!ENDIF

##############################################################################
##############################################################################
# Generate generic cutting planes. If you are using the OSI interface, you 
# can now add generic cutting planes from the CGL by setting the flag below.
# Which cutting planes are added can be controlled by SYMPHONY parameters (see
# the user's manual
##############################################################################
##############################################################################

USE_CGL_CUTS = TRUE

!IF "$(USE_CGL_CUTS)" == "TRUE"
LPINCDIR = $(LPINCDIR) /I "$(COINROOT)\Cgl\include"
LPLIB = $(LPLIB) "$(COINROOT)\Cgl\MSVisualStudio\v8\libCgl\Debug\libCgl.lib"
DEFINITIONS= $(DEFINITIONS) /D "USE_CGL_CUTS"
!ENDIF

##############################################################################
# If you wish to compile and use the SYMPHONY callable library through the 
# SYMPHONY OSI interface, set USE_OSI_INTERFACE to TRUE below. Note that
# you must have COIN installed to use this capability. See below to set the 
# path to the COIN directories. 
##############################################################################

USE_OSI_INTERFACE = FALSE

!IF "$(USE_OSI_INTERFACE)" == "TRUE"
ALL_INCDIR = $(LPINCDIR) /I "$(COINROOT)\Osi\src\OsiSym\include"
ALL_LIB = $(LPLIB) "$(COINROOT)\Osi\MSVisualStudio\v8\libOsiSym\Debug\libOsiSym.lib"
!ELSE
ALL_INCDIR = $(LPINCDIR)
ALL_LIB = $(LPLIB)
!ENDIF

##############################################################################
##############################################################################
#
# Compiling and Linking...
#
##############################################################################
##############################################################################

ALL_LIB = $(ALL_LIB) ".\Debug\libSymphony.lib"

DEFINITIONS = $(DEFINITIONS) /D "WIN32" /D "_DEBUG" /D "_MBCS" /D "_LIB" \
	/D "COMPILE_IN_CG" /D "COMPILE_IN_CP" /D "COMPILE_IN_LP" \
	/D "COMPILE_IN_TM"

ALL_INCDIR = $(ALL_INCDIR) /I "$(SYMPHONYROOT)\include" \
/I "$(COINROOT)\BuildTools\headers" \
/I "$(COINROOT)\Cgl\src" \
/I "$(COINROOT)\Cgl\src\CglAllDifferent" \
/I "$(COINROOT)\Cgl\src\CglClique" \
/I "$(COINROOT)\Cgl\src\CglDuplicateRow" \
/I "$(COINROOT)\Cgl\src\CglFlowCover" \
/I "$(COINROOT)\Cgl\src\CglGomory" \
/I "$(COINROOT)\Cgl\src\CglKnapsackCover" \
/I "$(COINROOT)\Cgl\src\CglLandP" \
/I "$(COINROOT)\Cgl\src\CglLiftAndProject" \
/I "$(COINROOT)\Cgl\src\CglMixedIntegerRounding" \
/I "$(COINROOT)\Cgl\src\CglMixedIntegerRounding2" \
/I "$(COINROOT)\Cgl\src\CglOddHole" \
/I "$(COINROOT)\Cgl\src\CglPreProcess" \
/I "$(COINROOT)\Cgl\src\CglProbing" \
/I "$(COINROOT)\Cgl\src\CglRedSplit" \
/I "$(COINROOT)\Cgl\src\CglSimpleRounding" \
/I "$(COINROOT)\Cgl\src\CglTwoMir" \
/I "$(COINROOT)\CoinUtils\src"

.SILENT:

CPP=cl.exe 
CPPFLAGS= /I $(ALL_INCDIR) /D $(DEFINITIONS) \
/D "_CRT_SECURE_NO_DEPRECATE" /D "_VC80_UPGRADE=0x0600" \
/D "_MBCS" /Gm /EHsc /RTC1 /MTd /Fp"$(OUTDIR)/symphony.pch" /Fo"$(OUTDIR)\\" \
/Fd"$(OUTDIR)\sym.pdb" /W2 /nologo /c /ZI /TP /errorReport:prompt

CFLAGS= /I $(ALL_INCDIR) /D $(DEFINITIONS) \
/D "_CRT_SECURE_NO_DEPRECATE" /D "_VC80_UPGRADE=0x0600" \
/D "_MBCS" /Gm /EHsc /RTC1 /MTd /Fp"$(OUTDIR)/symphony.pch" /Fo"$(OUTDIR)" \
/Fd"$(OUTDIR)\sym.pdb" /W2 /nologo /c /ZI /errorReport:prompt

.c.obj: 
	$(CPP) $(CPPFLAGS) "$*.c"
	 
.c.cobj: 
	$(CPP) $(CFLAGS) "$*.c"

ALL : "$(OUTDIR)" "LIB_MESSAGE" sym_lib "SYMPHONY_MESSAGE" "OBJECTS" sym_exe 

CLEAN:
	del /Q $(OUTDIR)\*.obj
	del /Q $(OUTDIR)\symphony.exe 
	del /Q $(OUTDIR)\libSymphony.lib
	del /Q $(OUTDIR)\sym.idb
	del /Q $(OUTDIR)\sym.pdb
	del /Q $(OUTDIR)\sym.pch

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

LIB_MESSAGE:
	echo Creating SYMPHONY library...	

SYMPHONY_MESSAGE:
	echo Compiling SYMPHONY main function...

sym_lib : \
	$(SYMPHONYROOT)\src\Common\pack_array.obj \
	$(SYMPHONYROOT)\src\Common\pack_cut.obj \
	$(SYMPHONYROOT)\src\Common\proccomm.obj \
	$(SYMPHONYROOT)\src\Common\sym_qsort.obj \
	$(SYMPHONYROOT)\src\Common\timemeas.obj \
	$(SYMPHONYROOT)\src\CutGen\cg_func.obj \
	$(SYMPHONYROOT)\src\CutGen\cg_wrapper.obj \
	$(SYMPHONYROOT)\src\CutPool\cp_func.obj \
	$(SYMPHONYROOT)\src\CutPool\cp_proccomm.obj \
	$(SYMPHONYROOT)\src\CutPool\cp_wrapper.obj \
	$(SYMPHONYROOT)\src\LP\lp_branch.obj \
	$(SYMPHONYROOT)\src\LP\lp_free.obj \
	$(SYMPHONYROOT)\src\LP\lp_genfunc.obj \
	$(SYMPHONYROOT)\src\LP\lp_proccomm.obj \
	$(SYMPHONYROOT)\src\LP\lp_rowfunc.obj \
	$(SYMPHONYROOT)\src\LP\lp_solver.obj \
	$(SYMPHONYROOT)\src\LP\lp_varfunc.obj \
	$(SYMPHONYROOT)\src\LP\lp_wrapper.obj \
	$(SYMPHONYROOT)\src\Master\master.obj \
	$(SYMPHONYROOT)\src\Master\master_func.obj \
	$(SYMPHONYROOT)\src\Master\master_io.obj \
	$(SYMPHONYROOT)\src\Master\master_wrapper.obj \
	$(SYMPHONYROOT)\src\TreeManager\tm_func.obj \
	$(SYMPHONYROOT)\src\TreeManager\tm_proccomm.obj \
	$(SYMPHONYROOT)\src\PrimalHeuristics\feasibility_pump.obj \
	$(SYMPHONYROOT)\src\PrimalHeuristics\sp.obj \
	$(SYMPHONYROOT)\src\Preprocessor\preprocessor_basic.obj \
	$(SYMPHONYROOT)\src\Preprocessor\preprocessor.obj
	lib.exe /nologo /out:$(OUTDIR)\libSymphony.lib $(OUTDIR)\*.obj
	echo "libSymphony.lib" created successfully...
	echo ...

LINK_OBJECTS = $(OUTDIR)\main.obj

OBJECTS : \
	$(SYMPHONYROOT)\src\Master\main.obj
	echo main compiled successfully...
	echo ...	
               	          
sym_exe : $(LINK_OBJECTS) $(OUTDIR)\libSymphony.lib
	echo Linking...
	$(CPP) /nologo /W3 /Fe"$(OUTDIR)\symphony.exe" \
	$(ALL_LIB) $**
	echo "symphony.exe" created successfully...
