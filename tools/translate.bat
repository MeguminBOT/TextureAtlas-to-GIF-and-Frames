@echo off
REM Translation Management Script for TextureAtlas Toolbox
REM This batch file provides a convenient way to run the translation management tool

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Set the project root (parent of tools directory)
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10+ and try again
    pause
    exit /b 1
)

REM Check if translate.py exists
if not exist "%SCRIPT_DIR%translate.py" (
    echo Error: translate.py not found in tools directory
    echo Expected location: %SCRIPT_DIR%translate.py
    pause
    exit /b 1
)

REM Change to project root directory
cd /d "%PROJECT_ROOT%"

REM If no arguments provided, show help
if "%~1"=="" (
    python "%SCRIPT_DIR%translate.py"
    pause
    exit /b 0
)

REM Run the translation script with all provided arguments
python "%SCRIPT_DIR%translate.py" %*

REM Pause if running interactively (not from command line with arguments)
if "%~1"=="extract" pause
if "%~1"=="compile" pause
if "%~1"=="resource" pause
if "%~1"=="status" pause
if "%~1"=="disclaimer" pause
if "%~1"=="all" pause
