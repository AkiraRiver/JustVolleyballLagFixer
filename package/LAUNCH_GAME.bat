@echo off
rem starts the optimised game (full game first, else the demo)
if exist "%~dp0game_full\volleyball_optim.exe" (
  cd /d "%~dp0game_full"
  start "" volleyball_optim.exe
) else if exist "%~dp0game_demo\volleyballdemo_optim.exe" (
  cd /d "%~dp0game_demo"
  start "" volleyballdemo_optim.exe
) else (
  echo Run JV_Optim.exe first.
  pause
)
