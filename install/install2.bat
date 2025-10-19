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

echo Removing old installation...
if exist "%ADDON_DST%" rmdir /s /q "%ADDON_DST%" >nul 2>&1

echo Copying addon folder from repository...
xcopy /s /i /y "%ROOT%\io_scene_niftools" "%ADDON_DST%" >nul 2>&1

echo Copying dependencies...
xcopy /s /i /y "%ROOT%\dependencies\*" "%ADDON_DST%\dependencies" >nul 2>&1

echo.
echo Copying obfuscated files...

:: Copy obfuscated license_check.py
if exist "%DIST_OBFUSCATED%\license_check.py" (
    copy /y "%DIST_OBFUSCATED%\license_check.py" "%ADDON_DST%\license_check.py" >nul 2>&1
    echo   - Installed license_check.py
) else (
    echo   WARNING: license_check.py not found in dist_obfuscated
)

:: Copy obfuscated operator files
if exist "%DIST_OBFUSCATED%\nif_export_op.py" (
    copy /y "%DIST_OBFUSCATED%\nif_export_op.py" "%ADDON_DST%\operators\nif_export_op.py" >nul 2>&1
    echo   - Installed nif_export_op.py
) else (
    echo   WARNING: nif_export_op.py not found in dist_obfuscated
)

if exist "%DIST_OBFUSCATED%\nif_import_op.py" (
    copy /y "%DIST_OBFUSCATED%\nif_import_op.py" "%ADDON_DST%\operators\nif_import_op.py" >nul 2>&1
    echo   - Installed nif_import_op.py
) else (
    echo   WARNING: nif_import_op.py not found in dist_obfuscated
)

if exist "%DIST_OBFUSCATED%\kf_export_op.py" (
    copy /y "%DIST_OBFUSCATED%\kf_export_op.py" "%ADDON_DST%\operators\kf_export_op.py" >nul 2>&1
    echo   - Installed kf_export_op.py
) else (
    echo   WARNING: kf_export_op.py not found in dist_obfuscated
)

if exist "%DIST_OBFUSCATED%\kf_import_op.py" (
    copy /y "%DIST_OBFUSCATED%\kf_import_op.py" "%ADDON_DST%\operators\kf_import_op.py" >nul 2>&1
    echo   - Installed kf_import_op.py
) else (
    echo   WARNING: kf_import_op.py not found in dist_obfuscated
)

if exist "%DIST_OBFUSCATED%\egm_import_op.py" (
    copy /y "%DIST_OBFUSCATED%\egm_import_op.py" "%ADDON_DST%\operators\egm_import_op.py" >nul 2>&1
    echo   - Installed egm_import_op.py
) else (
    echo   WARNING: egm_import_op.py not found in dist_obfuscated
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
