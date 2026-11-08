@echo off
chcp 65001 > nul
title MOXXI 3.0 -- VKontakte Bot (moxxivk)
echo ===================================================
echo   Zapusk avtonomnogo bota MOXXI dlya VKontakte...
echo ===================================================

if exist "..\бот2.0\venv\Scripts\python.exe" (
    "..\бот2.0\venv\Scripts\python.exe" main.py
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" main.py
) else (
    python main.py
)

pause
