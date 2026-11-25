@echo off
rem picks a Windows compatibility mode that LAUNCH_GAME.bat applies when it starts the game
setlocal
set "FILE=%~dp0compat_mode.txt"
echo.
echo Compatibility mode for the optimised game:
echo   1  Windows 8
echo   2  Windows 7
echo   3  Windows XP (Service Pack 3)
echo   4  Disable fullscreen optimizations
echo   5  Windows 8 + disable fullscreen optimizations
echo   6  Run as administrator
echo   0  None (turn it off)
echo.
choice /c 1234560 /n /m "Your choice (pick the same one as on the Steam game): "
set "MODE="
if errorlevel 7 goto off
if errorlevel 6 set "MODE=RUNASADMIN"
if errorlevel 6 goto save
if errorlevel 5 set "MODE=WIN8RTM DISABLEDXMAXIMIZEDWINDOWEDMODE"
if errorlevel 5 goto save
if errorlevel 4 set "MODE=DISABLEDXMAXIMIZEDWINDOWEDMODE"
if errorlevel 4 goto save
if errorlevel 3 set "MODE=WINXPSP3"
if errorlevel 3 goto save
if errorlevel 2 set "MODE=WIN7RTM"
if errorlevel 2 goto save
set "MODE=WIN8RTM"
:save
>"%FILE%" echo %MODE%
echo.
echo Saved: %MODE%
echo LAUNCH_GAME.bat will use it from now on.
pause
exit /b
:off
if exist "%FILE%" del "%FILE%"
echo.
echo Compatibility mode turned off.
pause
