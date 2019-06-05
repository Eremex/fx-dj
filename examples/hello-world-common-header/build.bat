@echo off
if not exist output mkdir output

set CCFLAGS=/D "WIN32" /D "_CONSOLE" /D "_UNICODE" /D "UNICODE" /c /I . /FI common.h /Od /WX- /Gd /Oy- /nologo
call set OBJS=

del /F /Q helloworld.exe
del /F /Q output\*.*

fx-dj.py -v -p project -t MAIN:VERSION1 -o output\input.txt -c output\common.h

cd output

for /F "tokens=*" %%f in (input.txt) do (
    cl %CCFLAGS%  /Fo.\%%~nf.obj %%f
    call set OBJS=%%OBJS%% %%~nf.obj
)

link /OUT:..\helloworld.exe /DYNAMICBASE /MACHINE:X86 /SUBSYSTEM:CONSOLE %OBJS%

cd ..
