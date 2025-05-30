@echo off

setlocal EnableDelayedExpansion

set PY_CMD=
set PY_VER=

for /f "tokens=2 delims= " %%I in ('py --version 2^>nul') do set PY_VER=%%I
if defined PY_VER (
    set PY_CMD=py
) else (
    for /f "tokens=2 delims= " %%I in ('python --version 2^>nul') do set PY_VER=%%I
    if defined PY_VER (
        set PY_CMD=python
    )
)

if not defined PY_VER (
    echo Python 3.10 or later not found.
    set /p INSTALL_PY="Do you want to download and install the latest Python version? (Y/N): "
    if /I "%INSTALL_PY%"=="Y" (
        start https://www.python.org/downloads/windows/
        echo Please install Python, then re-run this script.
        pause
        exit /b
    ) else (
        echo Python is required. Exiting.
        pause
        exit /b
    )
)


for /f "tokens=1,2 delims=." %%A in ("!PY_VER!") do (
    set MAJOR=%%A
    set MINOR=%%B
)

set /a VER_OK=0
if !MAJOR! GEQ 3 (
    if !MAJOR! GTR 3 (
        set /a VER_OK=1
    ) else if !MINOR! GEQ 10 (
        set /a VER_OK=1
    )
)

if !VER_OK! NEQ 1 (
    echo Python version !PY_VER! is less than 3.10.
    set /p INSTALL_PY="Do you want to download and install the latest Python version? (Y/N): "
    if /I "%INSTALL_PY%"=="Y" (
        start https://www.python.org/downloads/windows/
        echo Please install Python, then re-run this script.
        pause
        exit /b
    ) else (
        echo Python 3.10 or later is required. Exiting.
        pause
        exit /b
    )
)

echo Python !PY_VER! found.

:INSTALL_REQUIREMENTS
set /p INSTALL_REQ="Do you want to install the required libraries for TextureAtlas to GIF and Frames? (Y/N): "
if /I "%INSTALL_REQ%"=="Y" (
    !PY_CMD! -m pip install -r "%~dp0requirements.txt"
    pause
) else (
    echo Skipping requirements installation.
    pause
)
