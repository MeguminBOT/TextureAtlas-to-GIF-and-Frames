@echo off
REM Simple Translation Converter for Windows
REM Easy translation management for TextureAtlas Toolbox

setlocal EnableDelayedExpansion

REM Check if we have any arguments
if "%~1"=="" (
    call :show_interactive_menu
    goto :eof
)

set command=%1
shift

REM Collect all remaining arguments as language codes
set languages=
:loop
if "%1"=="" goto :endloop
set languages=!languages! %1
shift
goto :loop
:endloop

REM Run the Python script with appropriate arguments
if "%command%"=="extract" (
    echo Extracting translatable strings to simple format...
    python tools\simple_translation_converter.py !languages! --extract
) else if "%command%"=="create" (
    echo Creating example translation files...
    python tools\simple_translation_converter.py !languages! --create-example
) else if "%command%"=="apply" (
    echo Applying translations from simple format to Qt files...
    python tools\simple_translation_converter.py !languages!
) else (
    echo Error: Unknown command "%command%"
    echo Use: simple_translate [extract^|create^|apply] [language codes...]
    exit /b 1
)

echo.
echo Done!

REM Interactive menu function
:show_interactive_menu
cls
echo.
echo ===============================================================
echo   TextureAtlas Toolbox - Simple Translation Converter
echo ===============================================================
echo.
echo This tool makes it easy to translate the application without
echo needing Qt Linguist or other specialized tools.
echo.
echo What would you like to do?
echo.
echo   [1] Extract strings from one language to simple format
echo   [2] Create a new translation template file
echo   [3] Apply my translations to the application
echo   [4] Show available translation files
echo   [5] Show help and examples
echo   [6] Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto :extract_menu
if "%choice%"=="2" goto :create_menu
if "%choice%"=="3" goto :apply_menu
if "%choice%"=="4" goto :show_files
if "%choice%"=="5" goto :show_help
if "%choice%"=="6" goto :exit_script

echo Invalid choice. Please try again.
pause
goto :show_interactive_menu

:extract_menu
cls
echo.
echo ===============================================================
echo   Extract Strings to Simple Format
echo ===============================================================
echo.
echo This will extract translatable strings from existing Qt .ts files
echo into simple .txt files that are easy to edit.
echo.
echo Available languages with existing translations:
if exist "src\translations\app_sv.ts" echo   sv - Swedish
if exist "src\translations\app_es.ts" echo   es - Spanish
if exist "src\translations\app_fr.ts" echo   fr - French
if exist "src\translations\app_de.ts" echo   de - German
if exist "src\translations\app_ja.ts" echo   ja - Japanese
if exist "src\translations\app_zh.ts" echo   zh - Chinese
if exist "src\translations\app_en.ts" echo   en - English
echo.
set /p extract_lang="Enter ONE language code to extract (e.g., sv, de, es): "

if "%extract_lang%"=="" (
    echo No language specified.
    pause
    goto :show_interactive_menu
)

REM Check if multiple languages were entered (contains space)
echo %extract_lang% | find " " >nul
if not errorlevel 1 (
    echo Error: Please enter only ONE language code at a time.
    echo For multiple languages, use the command line version.
    pause
    goto :show_interactive_menu
)

echo.
echo Extracting strings for %extract_lang%...
python tools\simple_translation_converter.py %extract_lang% --extract

echo.
echo Extraction complete! Check translations\%extract_lang%.txt
echo You can now edit this file with any text editor.
echo.
pause
goto :show_interactive_menu

:create_menu
cls
echo.
echo ===============================================================
echo   Create New Translation Template
echo ===============================================================
echo.
echo This will create a template file with example translations
echo that you can use as a starting point.
echo.
echo Common language codes:
echo   sv - Swedish     de - German      es - Spanish
echo   fr - French      ja - Japanese    zh - Chinese
echo   pt - Portuguese  it - Italian     ru - Russian
echo   ko - Korean      ar - Arabic      pl - Polish
echo   nl - Dutch       da - Danish      no - Norwegian
echo.
set /p create_lang="Enter ONE language code for new template (e.g., de, it, pt): "

if "%create_lang%"=="" (
    echo No language specified.
    pause
    goto :show_interactive_menu
)

REM Check if multiple languages were entered (contains space)
echo %create_lang% | find " " >nul
if not errorlevel 1 (
    echo Error: Please enter only ONE language code at a time.
    echo For multiple languages, use the command line version.
    pause
    goto :show_interactive_menu
)

echo.
echo Creating template for %create_lang%...
python tools\simple_translation_converter.py %create_lang% --create-example

echo.
echo Template created! Check translations\%create_lang%.txt
echo Edit this file to add your translations, then use option 3 to apply them.
echo.
pause
goto :show_interactive_menu

:apply_menu
cls
echo.
echo ===============================================================
echo   Apply Translations to Application
echo ===============================================================
echo.
echo This will apply your translations from .txt files to the
echo application's Qt .ts files.
echo.
echo Available translation files:
if exist "translations\sv.txt" echo   sv.txt - Swedish
if exist "translations\es.txt" echo   es.txt - Spanish
if exist "translations\fr.txt" echo   fr.txt - French
if exist "translations\de.txt" echo   de.txt - German
if exist "translations\ja.txt" echo   ja.txt - Japanese
if exist "translations\zh.txt" echo   zh.txt - Chinese
if exist "translations\pt.txt" echo   pt.txt - Portuguese
if exist "translations\it.txt" echo   it.txt - Italian
if exist "translations\ru.txt" echo   ru.txt - Russian
echo.
set /p apply_lang="Enter ONE language code to apply (e.g., sv, de, es): "

if "%apply_lang%"=="" (
    echo No language specified.
    pause
    goto :show_interactive_menu
)

REM Check if multiple languages were entered (contains space)
echo %apply_lang% | find " " >nul
if not errorlevel 1 (
    echo Error: Please enter only ONE language code at a time.
    echo For multiple languages, use the command line version.
    pause
    goto :show_interactive_menu
)

if not exist "translations\%apply_lang%.txt" (
    echo Error: translations\%apply_lang%.txt not found!
    echo Use option 1 to extract or option 2 to create a translation file first.
    pause
    goto :show_interactive_menu
)

echo.
echo Applying translations for %apply_lang%...
python tools\simple_translation_converter.py %apply_lang%

echo.
echo Translations applied! You can now compile and test:
echo   .\tools\translate.bat compile %apply_lang%
echo.
pause
goto :show_interactive_menu

:show_files
cls
echo.
echo ===============================================================
echo   Available Translation Files
echo ===============================================================
echo.
echo Simple translation files (translations\):
if exist "translations\*.txt" (
    dir /B translations\*.txt 2>nul
) else (
    echo   No .txt translation files found
)
echo.
echo Qt translation files (src\translations\):
if exist "src\translations\app_*.ts" (
    dir /B src\translations\app_*.ts 2>nul
) else (
    echo   No .ts translation files found
)
echo.
echo Compiled translation files (src\translations\):
if exist "src\translations\app_*.qm" (
    dir /B src\translations\app_*.qm 2>nul
) else (
    echo   No .qm compiled files found
)
echo.
pause
goto :show_interactive_menu

:show_help
cls
echo.
echo ===============================================================
echo   Help and Examples
echo ===============================================================
echo.
echo TRANSLATION WORKFLOW:
echo =====================
echo.
echo 1. Extract existing translations:
echo    Choose option 1, enter language code (e.g., sv)
echo    This creates translations\sv.txt with current translations
echo.
echo 2. Edit the .txt file:
echo    Open translations\sv.txt in any text editor
echo    Format: original := translated
echo    Example: Cancel := Avbryt
echo.
echo 3. Apply your changes:
echo    Choose option 3, enter language code
echo    This updates the application files
echo.
echo 4. Compile and test:
echo    Run: .\tools\translate.bat compile sv
echo.
echo COMMAND LINE USAGE (Multiple Languages):
echo ==========================================
echo   simple_translate extract sv es    - Extract multiple languages
echo   simple_translate create de        - Create German template
echo   simple_translate apply sv es fr   - Apply multiple translations
echo.
echo INTERACTIVE MENU (Single Language):
echo ===================================
echo   Use this menu for one language at a time
echo   Perfect for beginners and step-by-step work
echo.
echo FILE LOCATIONS:
echo ===============
echo   Simple files:    translations\*.txt (easy to edit)
echo   Qt files:        src\translations\app_*.ts (application format)
echo   Compiled files:  src\translations\app_*.qm (binary format)
echo.
pause
goto :show_interactive_menu

:exit_script
echo.
echo Thank you for using the Simple Translation Converter!
echo.
pause
exit /b 0
