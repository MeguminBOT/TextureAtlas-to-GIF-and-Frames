@echo off
REM Translation management convenience script for Windows
REM Run from project root directory

if "%1"=="" (
    echo TextureAtlas Toolbox - Translation Management
    echo ==============================================
    echo Usage: translate [command] [languages...]
    echo.
    echo Commands:
    echo   extract  - Extract translatable strings from source code
    echo   compile  - Compile translation files for application use
    echo   status   - Show translation status for all languages
    echo   all      - Run full translation update cycle
    echo.
    echo Languages ^(optional^):
    echo   en sv es fr de ja zh - Specific language codes
    echo   all                  - Process all languages ^(default^)
    echo.
    echo Examples:
    echo   translate extract           ^(all languages^)
    echo   translate extract sv en     ^(Swedish and English only^)
    echo   translate compile sv        ^(Swedish only^)
    echo   translate status es fr de   ^(Spanish, French, German^)
    echo   translate all sv            ^(Full cycle for Swedish only^)
    goto :eof
)

python tools/translations/update_translations.py %*
