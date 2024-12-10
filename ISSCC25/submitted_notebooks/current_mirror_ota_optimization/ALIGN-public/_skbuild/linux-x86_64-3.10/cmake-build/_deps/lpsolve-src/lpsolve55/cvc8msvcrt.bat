@echo off

REM This batch file compiles the lpsolve libraries with the Microsoft Visual C/C++ compiler under Windows

REM Microsoft Visual C++ 2005 or 2008 Redistributable Package must be installed at the client for this to work:

REM 32-bit:
REM http://www.microsoft.com/downloads/details.aspx?FamilyId=32BC1BEE-A3F9-4C13-9C99-220B62A191EE&displaylang=en
REM http://www.microsoft.com/downloads/details.aspx?familyid=9B2DA534-3E03-4391-8A4D-074B9F2BC1BF&displaylang=en
REM http://www.microsoft.com/downloads/details.aspx?familyid=A5C84275-3B97-4AB7-A40D-3802B2AF5FC2&displaylang=en

REM 64-bit:
REM http://www.microsoft.com/downloads/details.aspx?familyid=BA9257CA-337F-4B40-8C14-157CFDFFEE4E&displaylang=en

REM See also
REM http://channel9.msdn.com/ShowPost.aspx?PostID=23261
REM http://msdn2.microsoft.com/en-us/library/ms235291.aspx  (How to: Deploy using XCopy)
REM http://msdn2.microsoft.com/en-us/library/ms235299.aspx  (Redistributing Visual C++ Files)

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

if not exist bin\%PLATFORM%\*.* md bin\%PLATFORM%

set src=../lp_MDO.c ../shared/commonlib.c ../shared/mmio.c ../shared/myblas.c ../ini.c ../colamd/colamd.c ../lp_rlp.c ../lp_crash.c ../bfp/bfp_LUSOL/lp_LUSOL.c ../bfp/bfp_LUSOL/LUSOL/lusol.c ../lp_Hash.c ../lp_lib.c ../lp_wlp.c ../lp_matrix.c ../lp_mipbb.c ../lp_MPS.c ../lp_params.c ../lp_presolve.c ../lp_price.c ../lp_pricePSE.c ../lp_report.c ../lp_scale.c ../lp_simplex.c ../lp_SOS.c ../lp_utils.c ../yacc_read.c

if not exist bin\%PLATFORM%\*.* md bin\%PLATFORM%

rc lpsolve.rc
%c% -W1 -I.. -I../shared -I../bfp -I../bfp/bfp_LUSOL -I../bfp/bfp_LUSOL/LUSOL -I../colamd /LD /MD /O2 /Zp8 /Gz -D_WINDLL -DWIN32 -D_CRT_SECURE_NO_DEPRECATE -D_CRT_NONSTDC_NO_DEPRECATE -DYY_NEVER_INTERACTIVE -DPARSER_LP -DINVERSE_ACTIVE=INVERSE_LUSOL -DRoleIsExternalInvEngine %src% lpsolve.res ..\lp_solve.def /Febin\%PLATFORM%\lpsolve55.dll
editbin /LARGEADDRESSAWARE bin\%PLATFORM%\lpsolve55.dll

rem http://msdn2.microsoft.com/en-us/library/ms235229.aspx
rem for vs2005 need to embed manifest in dll with manifest tool - #2 on the next line does this.
mt /outputresource:"bin\%PLATFORM%\lpsolve55.dll;#2" /manifest "bin\%PLATFORM%\lpsolve55.dll.manifest"
rem pause

if exist *.obj del *.obj
%c% -I.. -I../shared -I../bfp -I../bfp/bfp_LUSOL -I../bfp/bfp_LUSOL/LUSOL -I../colamd /MT /O2 /Zp8 /Gd /c -DWIN32 -D_CRT_SECURE_NO_DEPRECATE -D_CRT_NONSTDC_NO_DEPRECATE -DYY_NEVER_INTERACTIVE -DPARSER_LP -DINVERSE_ACTIVE=INVERSE_LUSOL -DRoleIsExternalInvEngine %src%
lib *.obj /OUT:bin\%PLATFORM%\liblpsolve55.lib

if exist *.obj del *.obj
%c% -I.. -I../shared -I../bfp -I../bfp/bfp_LUSOL -I../bfp/bfp_LUSOL/LUSOL -I../colamd /MTd /Od /Zp8 /Gd /RTC1 /c -DWIN32 -D_CRT_SECURE_NO_DEPRECATE -D_CRT_NONSTDC_NO_DEPRECATE -DYY_NEVER_INTERACTIVE -DPARSER_LP -DINVERSE_ACTIVE=INVERSE_LUSOL -DRoleIsExternalInvEngine %src%
lib *.obj /OUT:bin\%PLATFORM%\liblpsolve55d.lib

if exist *.obj del *.obj
set PLATFORM=
