@echo off

set c=gcc

REM determine platform (win32/win64)
echo main(){printf("SET PLATFORM=win%%d\n", (int) (sizeof(void *)*8));}>platform.c
%c% platform.c -o platform.exe
del platform.c
platform.exe >platform.bat
del platform.exe
call platform.bat
del platform.bat

if not exist bin\%PLATFORM%\*.* md bin\%PLATFORM%

set src=../../shared/commonlib.c ../../colamd/colamd.c lp_LUSOL.c ../../lp_utils.c ../../shared/myblas.c lusol/lusol.c bfp_LUSOL.c

%c% -DINLINE=static -I.. -I../.. -I../../colamd -I../../shared -Ilusol -I. -s -O3 -shared -mno-cygwin -enable-stdcall-fixup -D_WINDLL -D_USRDLL -DWIN32 -DRoleIsExternalInvEngine -DINVERSE_ACTIVE=INVERSE_LUSOL %src% ../lp_BFP.def -o bin\%PLATFORM%\bfp_LUSOL.dll

%c% -DINLINE=static -I.. -I../.. -I../../colamd -I../../shared -Ilusol -I. -s -O3 -shared -D_WINDLL -D_USRDLL -DWIN32 -DRoleIsExternalInvEngine -DINVERSE_ACTIVE=INVERSE_LUSOL %src% -o bin\%PLATFORM%\libbfp_LUSOL.so

%c% -DINLINE=static -I.. -I../.. -I../../colamd -I../../shared -Ilusol -I. -s -O3 -c -DRoleIsExternalInvEngine -DINVERSE_ACTIVE=INVERSE_LUSOL %src%
ar rv bin\%PLATFORM%\libbfp_LUSOL.a *.o

if exist *.o del *.o

set PLATFORM=
