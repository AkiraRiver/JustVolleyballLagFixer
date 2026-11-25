@echo off
rem gathers everything needed to understand a problem into JV_report.zip on the Desktop
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\report.ps1" -Here "%~dp0."
pause
