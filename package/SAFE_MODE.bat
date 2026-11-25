@echo off
rem turns off multithreaded rendering (if the game crashes or looks broken), then rebuilds
for %%G in (game_full game_demo) do (
  if not exist "%~dp0%%G" mkdir "%~dp0%%G"
  type nul > "%~dp0%%G\no_render_thread.txt"
)
echo Multithreaded rendering turned off. Rebuilding...
"%~dp0JV_Optim.exe"
