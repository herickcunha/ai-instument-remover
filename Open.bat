@echo off
title Instrument Remover
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Error running the application. Press any key to exit.
    pause >nul
)
