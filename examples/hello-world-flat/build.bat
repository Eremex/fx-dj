@echo off
if not exist flat_build mkdir flat_build

set CCFLAGS=/D "WIN32" /D "_CONSOLE" /D "_UNICODE" /D "UNICODE" /c /I . /Od /FI includes.inc /WX- /Gd /Oy- /nologo
call set OBJS=

del /F /Q helloworld.exe
del /F /Q flat_build\*.*

fx-dj.py -v -p project -t MAIN:VERSION1 -o flat_build -c test.h

cd flat_build

echo #define FX_METADATA^(data^) > includes.inc
echo #define FX_INTERFACE^(hdr^) ^<hdr.h^> >> includes.inc

for %%f in (*.c) do (
    cl %CCFLAGS%  /Fo.\%%~nf.obj %%f
    call set OBJS=%%OBJS%% %%~nf.obj
)

link /OUT:..\helloworld.exe /DYNAMICBASE /MACHINE:X86 /SUBSYSTEM:CONSOLE %OBJS%

cd ..
