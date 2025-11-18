@echo off
REM Check for administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PF86=%ProgramFiles(x86)%"
set "REQ_STABLE=requirements.txt"
set "REQ_EXPERIMENTAL=requirements-experimental.txt"
set "PY_MIN_MAJOR=3"
set "PY_MIN_MINOR=10"
set "PY_INSTALL_DIR=Python312"
set "PY_INSTALL_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
set "PY_INSTALLER=%TEMP%\textureatlas-python-installer.exe"

call :DetectPython
if not defined PY_VER (
    echo Python %PY_MIN_MAJOR%.%PY_MIN_MINOR%+ not found. Attempting automatic installation...
    call :InstallPython || goto :InstallFail
    call :DetectPython
)

call :CheckVersion
if !VER_OK! NEQ 1 (
    echo Detected Python version !PY_VER! is below the required %PY_MIN_MAJOR%.%PY_MIN_MINOR%.
    echo Installing the bundled Python build...
    call :InstallPython || goto :InstallFail
    call :DetectPython
    call :CheckVersion
    if !VER_OK! NEQ 1 goto :InstallFail
)

echo Python !PY_VER! is ready.
"!PY_CMD!" -m pip install --upgrade pip --user

call :InstallRequirements
echo.
echo Setup complete.
pause
goto :EOF

:InstallRequirements
set /p INSTALL_REQ="Do you want to install the required libraries for TextureAtlas Toolbox? (Y/N): "
if /I not "%INSTALL_REQ%"=="Y" (
    echo Skipping requirements installation.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 0
)

echo Select the dependency profile to install:
echo   1. Stable (recommended) - !REQ_STABLE!
echo   2. Experimental         - !REQ_EXPERIMENTAL!
set REQ_FILE=!REQ_STABLE!
set /p REQ_CHOICE="Enter 1 or 2 [default: 1]: "
if "%REQ_CHOICE%"=="2" set REQ_FILE=!REQ_EXPERIMENTAL!

echo Installing dependencies from !REQ_FILE! ...
"!PY_CMD!" -m pip install --upgrade --user -r "!SCRIPT_DIR!!REQ_FILE!"
if errorlevel 1 (
    echo Dependency installation encountered errors.
    echo.
    echo Press any key to exit...
    pause >nul
) else (
    echo Dependencies installed successfully.
    echo.
    echo Adding Python Scripts directory to user PATH...
    call :AddScriptsToPath
)
exit /b 0

:DetectPython
set "PY_CMD="
set "PY_VER="
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
    call :DetectFromKnownPaths
)
exit /b 0

:DetectFromKnownPaths
for %%P in ("%ProgramFiles%\!PY_INSTALL_DIR!\python.exe" "!PF86!\!PY_INSTALL_DIR!\python.exe" "!LOCALAPPDATA!\Programs\Python\!PY_INSTALL_DIR!\python.exe") do (
    if exist %%~fP (
        for /f "tokens=2 delims= " %%I in ('"%%~fP" --version 2^>nul') do (
            set PY_VER=%%I
            set PY_CMD=%%~fP
            goto :FoundPythonExe
        )
    )
)
:FoundPythonExe
exit /b 0

:CheckVersion
set /a VER_OK=0
if not defined PY_VER exit /b 0
set MAJOR=0
set MINOR=0
for /f "tokens=1,2 delims=." %%A in ("!PY_VER!") do (
    set MAJOR=%%A
    set MINOR=%%B
)
if !MAJOR! GEQ %PY_MIN_MAJOR% (
    if !MAJOR! GTR %PY_MIN_MAJOR% (
        set /a VER_OK=1
    ) else if !MINOR! GEQ %PY_MIN_MINOR% (
        set /a VER_OK=1
    )
)
exit /b 0

:InstallPython
echo Downloading Python installer from %PY_INSTALL_URL% ... This step may take a few minutes.
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%PY_INSTALL_URL%' -OutFile '%PY_INSTALLER%' -UseBasicParsing } catch { exit 1 }"
if errorlevel 1 (
    echo Failed to download Python installer.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo Running silent Python installer (you may be prompted for administrator approval)...
echo This step may take a few minutes.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$proc = Start-Process -FilePath '%PY_INSTALLER%' -ArgumentList '/quiet','InstallAllUsers=1','PrependPath=1','Include_test=0','SimpleInstall=1','Include_launcher=1' -Verb RunAs -Wait -PassThru; exit $proc.ExitCode"
set PY_INSTALL_EXIT=%ERRORLEVEL%
if !PY_INSTALL_EXIT! NEQ 0 (
    echo Python installer returned exit code !PY_INSTALL_EXIT!.
    del /f /q "%PY_INSTALLER%" >nul 2>&1
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo Python installation completed successfully.
del /f /q "%PY_INSTALLER%" >nul 2>&1

REM Refresh environment to pick up new PATH
echo Refreshing environment variables...
call :RefreshEnv
exit /b 0

:RefreshEnv
for /f "skip=2 tokens=3*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYS_PATH=%%A %%B"
for /f "skip=2 tokens=3*" %%A in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USR_PATH=%%A %%B"
set "PATH=%SYS_PATH%;%USR_PATH%;%USERPROFILE%\AppData\Roaming\Python\Python312\Scripts"
exit /b 0

:AddScriptsToPath
set "SCRIPTS_DIR=%USERPROFILE%\AppData\Roaming\Python\Python312\Scripts"
for /f "skip=2 tokens=3*" %%A in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "CURRENT_PATH=%%A %%B"
echo !CURRENT_PATH! | findstr /C:"!SCRIPTS_DIR!" >nul
if errorlevel 1 (
    echo Adding !SCRIPTS_DIR! to user PATH registry...
    setx PATH "!CURRENT_PATH!;!SCRIPTS_DIR!" >nul
    if errorlevel 1 (
        echo Failed to update PATH. You may need to add it manually.
    ) else (
        echo PATH updated successfully. The change will take effect in new terminal sessions.
        set "PATH=!PATH!;!SCRIPTS_DIR!"
    )
) else (
    echo Scripts directory already in PATH.
)
exit /b 0

:InstallFail
echo Unable to ensure a compatible Python installation automatically.
echo Please install Python %PY_MIN_MAJOR%.%PY_MIN_MINOR% or later manually and re-run this script.
pause
exit /b 1
