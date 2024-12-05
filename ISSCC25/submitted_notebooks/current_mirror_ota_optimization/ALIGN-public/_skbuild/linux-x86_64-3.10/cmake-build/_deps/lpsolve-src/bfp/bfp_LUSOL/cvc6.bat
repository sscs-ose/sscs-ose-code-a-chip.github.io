@echo off

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
echo This batch file is intended for 32 bit compilation with MS Visual C 6
echo For newer versions use cvc8*.bat
goto done
:ok1

if not exist bin\%PLATFORM%\*.* md bin\%PLATFORM%

set src=../../shared/commonlib.c ../../colamd/colamd.c lp_LUSOL.c ../../lp_utils.c ../../shared/myblas.c lusol/lusol.c bfp_LUSOL.c

%c% -I.. -I../.. -I../../colamd -I../../shared -Ilusol -I. /LD /MD /O2 /Zp8 /Gz -D_WINDLL -D_USRDLL -DWIN32 -D_CRT_SECURE_NO_DEPRECATE -D_CRT_NONSTDC_NO_DEPRECATE -DRoleIsExternalInvEngine -DINVERSE_ACTIVE=INVERSE_LUSOL %src% ../lp_BFP.def -o bin\%PLATFORM%\bfp_LUSOL.dll

if exist *.obj del *.obj
:done
set PLATFORM=
