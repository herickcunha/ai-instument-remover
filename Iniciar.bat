@echo off
title Instrument Remover
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Erro ao executar. Pressione qualquer tecla para sair.
    pause >nul
)
