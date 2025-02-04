@echo off
REM This batch file runs the Python script from the same directory it resides in

REM Check if Python is accessible
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not found in your PATH.
    echo Install Python or add it to your PATH environment variable.
    pause
    exit /b
)

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Execute the Python script from the same directory
python "%SCRIPT_DIR%wallpaper_changer.py"

