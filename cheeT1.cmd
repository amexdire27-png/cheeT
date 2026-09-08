@echo off
title cheeT1
cd /d "%~dp0"
if exist "%~dp0cheeT1.exe" (
    start "" "%~dp0cheeT1.exe"
    goto :eof
)
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0launch.py"
) else (
    start "" pythonw "%~dp0launch.py"
)
