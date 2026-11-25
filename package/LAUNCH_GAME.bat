@echo off
rem starts the optimised game (full game first, else the demo), with the
rem launch options copied from Steam and the mode chosen in COMPAT_MODE.bat,
rem and notes each start in launch_log.txt
setlocal
set "HERE=%~dp0"
set "DIR="
if exist "%HERE%game_full\volleyball_optim.exe" (
  set "DIR=%HERE%game_full"
  set "EXE=volleyball_optim.exe"
) else if exist "%HERE%game_demo\volleyballdemo_optim.exe" (
  set "DIR=%HERE%game_demo"
  set "EXE=volleyballdemo_optim.exe"
)
if not defined DIR (
  echo Run JV_Optim.exe first.
  pause
  exit /b
)
set "ARGS="
if exist "%DIR%\launch_args.txt" set /p ARGS=<"%DIR%\launch_args.txt"
set "MODE="
if exist "%HERE%compat_mode.txt" set /p MODE=<"%HERE%compat_mode.txt"
rem Windows applies this compatibility mode to the program started below
if defined MODE set "__COMPAT_LAYER=%MODE%"
>>"%HERE%launch_log.txt" echo %DATE% %TIME%  %EXE% %ARGS%  [compat: %MODE%]
cd /d "%DIR%"
start "" "%EXE%" %ARGS%
