@echo off

:: Script to install obfuscated license files to the blender addon
:: This script copies obfuscated files from dist_obfuscated/ to replace the original module files

setlocal enabledelayedexpansion

set "BLENDER_ADDONS_DIR=%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons"

set "DIR=%~dps0"
:: remove trailing backslash
if "%DIR:~-1%" == "\" set "DIR=%DIR:~0,-1%"
for %%I in ("%DIR%\..") do set "ROOT=%%~fI"

set "ADDON_DST=%BLENDER_ADDONS_DIR%\io_scene_niftools"
set "DIST_OBFUSCATED=%ROOT%\dist_obfuscated"

echo.
echo ============================================================
echo Installing Obfuscated License Files
echo ============================================================
echo.

echo Generating obfuscated files...
python "%ROOT%\obfuscate_license.py"
if errorlevel 1 (
    echo ERROR: Obfuscation failed. Aborting install.
    goto end
)

:: Check if dist_obfuscated folder exists
if not exist "%DIST_OBFUSCATED%" (
    echo ERROR: dist_obfuscated folder not found at: %DIST_OBFUSCATED%
    echo.
    echo Please run obfuscate_license.py first:
    echo   python obfuscate_license.py
    echo.
    pause
    goto end
)

echo Blender addons directory: %BLENDER_ADDONS_DIR%
echo Addon directory: %ADDON_DST%
echo Obfuscated files source: %DIST_OBFUSCATED%
echo.

echo Running base install...
call "%DIR%\install.bat"
if errorlevel 1 (
    echo ERROR: Base install failed. Aborting obfuscated install.
    goto end
)

echo.
echo Copying obfuscated files...
if exist "%DIST_OBFUSCATED%" (
    xcopy /e /i /y "%DIST_OBFUSCATED%" "%ADDON_DST%" >nul 2>&1
    if exist "%ADDON_DST%\pyarmor_runtime_000000" rmdir /s /q "%ADDON_DST%\pyarmor_runtime_000000" >nul 2>&1
    echo   - Installed obfuscated files
) else (
    echo   WARNING: dist_obfuscated not found, skipping obfuscated file copy
)

:: Copy PyArmor runtime to dependencies
echo.
echo Installing PyArmor runtime...
if exist "%DIST_OBFUSCATED%\pyarmor_runtime_000000" (
    :: Remove old runtime if exists
    if exist "%ADDON_DST%\dependencies\pyarmor_runtime_000000" rmdir /s /q "%ADDON_DST%\dependencies\pyarmor_runtime_000000" >nul 2>&1
    
    :: Copy new runtime to dependencies folder
    xcopy /e /i /y "%DIST_OBFUSCATED%\pyarmor_runtime_000000" "%ADDON_DST%\dependencies\pyarmor_runtime_000000" >nul 2>&1
    echo   - Installed pyarmor_runtime_000000 to dependencies
) else (
    echo   WARNING: pyarmor_runtime_000000 not found in dist_obfuscated
)

echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo Obfuscated files have been installed to:
echo   %ADDON_DST%
echo.
echo Next steps:
echo   1. Restart Blender
echo   2. Test import/export functionality
echo   3. Verify license checks are working
echo.
pause

:end
