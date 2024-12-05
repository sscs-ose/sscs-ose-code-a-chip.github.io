@echo off

REM This batch file compiles the lp_solve driver program with the Microsoft Visual C/C++ compiler under Windows


set src=../shared/commonlib.c ../shared/mmio.c ../shared/myblas.c ../ini.c ../lp_rlp.c ../lp_crash.c ../bfp/bfp_LUSOL/lp_LUSOL.c ../bfp/bfp_LUSOL/LUSOL/lusol.c ../lp_Hash.c ../lp_lib.c ../lp_wlp.c ../lp_matrix.c ../lp_mipbb.c ../lp_MPS.c ../lp_params.c ../lp_presolve.c ../lp_price.c ../lp_pricePSE.c ../lp_report.c ../lp_scale.c ../lp_simplex.c lp_solve.c ../lp_SOS.c ../lp_utils.c ../yacc_read.c ../lp_MDO.c ../colamd/colamd.c %1
set c=cl

REM determine platform (win32/win64)
echo #include "stdio.h">platform.c
echo void main(){printf("SET PLATFORM=win%%d\n", (int) (sizeof(void *)*8));}>>platform.c
%c% /nologo platform.c /Feplatform.exe
del platform.c
platform.exe >platform.bat
del platform.exe
call platform.bat
del platform.bat

if "%PLATFORM%" == "win32" goto ok1
echo.
echo This batch file is entended for 32 bit compilation with MS Visual C 6
echo For newer versions use cvc8*.bat
goto done
:ok1

if not exist bin\%PLATFORM%\*.* md bin\%PLATFORM%

%c% -I.. -I../bfp -I../bfp/bfp_LUSOL -I../bfp/bfp_LUSOL/LUSOL -I../colamd -I../shared /O2 /Zp8 /Gd -D"LP_MAXLINELEN=0" -DNoParanoia -DWIN32 -D_CRT_SECURE_NO_DEPRECATE -D_CRT_NONSTDC_NO_DEPRECATE -DYY_NEVER_INTERACTIVE -DPARSER_LP -DINVERSE_ACTIVE=INVERSE_LUSOL -DRoleIsExternalInvEngine -Febin\%PLATFORM%\lp_solve.exe %src%

if exist *.obj del *.obj
:done
set PLATFORM=
