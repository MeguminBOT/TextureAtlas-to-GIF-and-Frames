@echo off
cd /d "%~dp0.."
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo  TextureAtlas Toolbox - Windows Nuitka Build Script
echo ============================================================
echo.
echo  This script is provided as-is and I won't give support for it if any issues with it arise.
echo.
echo  This script will:
echo    - Check for Python 3.10, 3.11, or 3.12 (3.13+ requires MSVC)
echo    - Automatically install or upgrade Nuitka via pip
echo    - Check for Visual Studio (MSVC)
echo    - Build the 'TextureAtlas Toolbox' python code into a Windows executable
echo.
echo  If you have Python 3.10-3.12 and Visual Studio installed,
echo  you can choose to use MSVC or MinGW64 for building.
echo.
echo  Visual Studio dependencies required for MSVC builds:
echo    * Windows 10 SDK (10.0.19041.0) or later
echo    * MSVC v143 - VS 2022 C++ x64/x86 build tools (or later if they exist)
echo    * C++/CLI Support for v143 build tools (or later if they exist)
echo    * Optional: C++ Clang Compiler for Windows
echo    * Optional: MSBuild support for LLVM (clang-cl) toolset
echo.
echo  The .exe file output will be placed in the '_build-output\dist' folder.
echo ============================================================
echo.

choice /m "Do you wish to proceed?"
if errorlevel 2 (
    echo Exiting...
    exit /b
)

:: Detect Python version
for /f "delims=" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo %PYVER% | find "3.13" >nul
if %errorlevel%==0 (
    echo.
    echo ============================================================
    echo  WARNING: Python 3.13 detected.
    echo  Nuitka requires Visual Studio to build with Python 3.13.
    echo ============================================================
    echo.
    pause
)

python -m pip install -U nuitka

:: Detect compatible Python versions
set PY310_312=0
echo %PYVER% | find "3.10" >nul && set PY310_312=1
echo %PYVER% | find "3.11" >nul && set PY310_312=1
echo %PYVER% | find "3.12" >nul && set PY310_312=1

:: Detect MSVC
set MSVC_INSTALLED=0
where cl >nul 2>nul && set MSVC_INSTALLED=1

:: Clean export folder
if exist _build-output rmdir /s /q _build-output

:: Choose compiler
set NUITKA_COMPILER=--msvc=latest
if "%PY310_312%"=="1" if "%MSVC_INSTALLED%"=="0" (
    set NUITKA_COMPILER=--mingw64
)

if "%MSVC_INSTALLED%"=="1" (
    echo %PYVER% | find "3.13" >nul
    if not %errorlevel%==0 (
        choice /m "MSVC detected. Do you want to use MinGW64 instead of MSVC for building?"
        if errorlevel 2 (
            set NUITKA_COMPILER=--msvc=latest
        ) else (
            set NUITKA_COMPILER=--mingw64
        )
    )
)

:: Ask if user wants to use clang
set NUITKA_CLANG=
if "%NUITKA_COMPILER%"=="--msvc=latest" (
    set ASK_CLANG=1
) else (
    set ASK_CLANG=0
)

if "%ASK_CLANG%"=="1" (
    choice /m "Do you want to use the clang compiler (from Visual Studio) for building? (Enter 'N' if unsure)"
    if errorlevel 2 (
        set NUITKA_CLANG=
    ) else (
        set NUITKA_CLANG=--clang
    )
)
echo [DEBUG] NUITKA_CLANG set to: %NUITKA_CLANG%
echo.

:: Ask if user wants verbose scons output from Nuitka
:: This is useful for debugging build issues
set SHOW_SCONS=
choice /m "Do you want to enable --show-scons for verbose build/debug output? Useful if you encounter issues."
if errorlevel 2 (
    set SHOW_SCONS=
) else (
    set SHOW_SCONS=--show-scons
)
echo [DEBUG] SHOW_SCONS set to: %SHOW_SCONS%
echo.

:: Get version input
set /p APP_VERSION=Enter the application version number (e.g., 1.0.0): 
echo.

:: Build command
echo [DEBUG] Running Nuitka build...
call nuitka ^
 --standalone^
 --assume-yes-for-downloads^
 --deployment %NUITKA_COMPILER%^
 --follow-imports^
 --include-qt-plugins=qml^
 --enable-plugin=pyside6^
 --windows-console-mode=attach^
 --include-data-dir=assets=assets^
 --include-data-files=src\translations\translations.qrc=translations\^
 --include-data-files=src\translations\*.ts=translations\^
 --include-data-files=src\translations\*.qm=translations\^
 --include-data-dir=docs=docs^
 --include-data-dir=ImageMagick=ImageMagick^
 --include-data-files=ImageMagick\*.dll=ImageMagick\^
 --include-data-files=LICENSE=LICENSE^
 --include-data-files=README.md=README.md^
 --include-package=src^
 --windows-icon-from-ico=assets\icon.ico^
 --company-name="AutisticLulu"^
 --product-name="TextureAtlas Toolbox"^
 --file-version=%APP_VERSION%^
 --product-version=%APP_VERSION%^
 --copyright="Copyright © 2025 AutisticLulu. Licensed under the GNU Affero General Public License (AGPL)"^
 --file-description="TextureAtlas Toolbox v%APP_VERSION%"^
 --output-filename="TextureAtlasToolbox.exe"^
 --output-dir=_build-output src\Main.py %SHOW_SCONS% %NUITKA_CLANG%

if %errorlevel%==0 (
    echo.
    echo ============================================================
    echo  Build succeeded! Output directory:
    echo    _build-output\dist
    echo ============================================================
) else if defined NUITKA_CLANG (
    echo.
    echo ============================================================
    echo  Build with clang failed. Retrying build without clang...
    echo ============================================================

    call nuitka ^
     --standalone^
     --assume-yes-for-downloads^
     --deployment %NUITKA_COMPILER%^
     --follow-imports^
     --windows-console-mode=attach^
     --include-data-dir=assets=assets^
     --include-data-files=src\translations\translations.qrc=translations\^
     --include-data-files=src\translations\*.ts=translations\^
     --include-data-files=src\translations\*.qm=translations\^
     --include-data-dir=docs=docs^
     --include-data-dir=ImageMagick=ImageMagick^
     --include-data-files=ImageMagick\*.dll=ImageMagick\^
     --include-data-files=LICENSE=LICENSE^
     --include-data-files=README.md=README.md^
     --include-package=src^
     --include-qt-plugins=qml^
     --enable-plugin=pyside6^
     --windows-icon-from-ico=assets\icon.ico^
     --company-name="AutisticLulu"^
     --product-name="TextureAtlas Toolbox"^
     --file-version=%APP_VERSION%^
     --product-version=%APP_VERSION%^
     --copyright="Copyright © 2025 AutisticLulu. Licensed under the GNU Affero General Public License (AGPL)"^
     --file-description="TextureAtlas Toolbox v%APP_VERSION%"^
     --output-filename="TextureAtlasToolbox.exe"^
     --output-dir=_build-output src\Main.py %SHOW_SCONS%

    if %errorlevel%==0 (
        echo.
        echo ============================================================
        echo  Build succeeded without clang. Output directory:
        echo    _build-output\dist
        echo ============================================================
    )
) else (
    echo.
    echo ============================================================
    echo  Build failed!
    echo ============================================================
)

endlocal
pause