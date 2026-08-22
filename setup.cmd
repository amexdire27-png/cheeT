@echo off
title Sync Host setup
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 (
    echo.
    echo Setup failed.
    echo If Python is missing: setup tries to install it with winget.
    echo Otherwise install Python 3.11+ from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH", then run this file again.
)
echo.
pause
