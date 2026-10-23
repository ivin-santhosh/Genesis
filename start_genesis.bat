@echo off
setlocal
cd /d "%~dp0\.."
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    py -3 -m Genesis
) else (
    python -m Genesis
)
if errorlevel 1 (
    echo Genesis could not start. Check Python 3.11+ and review FIRST_RUN.md.
    pause
)
