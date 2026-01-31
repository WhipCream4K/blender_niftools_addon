@echo off

:: Script to install the blender nif scripts

set "BLENDER_ADDONS_DIR=%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons"

set "DIR=%~dps0"
:: remove trailing backslash
if "%DIR:~-1%" == "\" set "DIR=%DIR:~0,-1%"
for %%I in ("%DIR%\..") do set "ROOT=%%~fI"
set "NAME=blender_niftools_addon"
set /p VERSION=<%ROOT%\io_scene_niftools\VERSION.txt
for /f %%i in ('git rev-parse --short HEAD') do set HASH=%%i
:: Use PowerShell to get current date in YYYY-MM-DD format independent of local format
for /f %%i in ('powershell -executionpolicy bypass -Command Get-Date -Format "yyyy-MM-dd"') do set DATE=%%i
set "ZIP_NAME=%NAME%-%VERSION%-%DATE%-%HASH%"

if "%BLENDER_ADDONS_DIR%" == "" if not exist "%BLENDER_ADDONS_DIR%" (
echo. "Update BLENDER_ADDONS_DIR to the folder where the blender addons reside, such as:"
echo. "set BLENDER_ADDONS_DIR=%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons"
echo.
pause
goto end
)

echo "Blender addons directory : %BLENDER_ADDONS_DIR%"
echo. "Installing to: %BLENDER_ADDONS_DIR%\io_scene_niftools"

:: create zip
echo. "Building artifact"
call "%DIR%\makezip.bat"

:: remove old files
echo.Removing old installation
if exist "%BLENDER_ADDONS_DIR%\io_scene_niftools" rmdir /s /q "%BLENDER_ADDONS_DIR%\io_scene_niftools"

:: copy files from repository to blender addons folder
powershell -executionpolicy bypass -Command "%DIR%\unzip.ps1" -source '%DIR%\%ZIP_NAME%.zip' -destination '%BLENDER_ADDONS_DIR%'

:: ensure bundled dependencies are present (e.g., texconv.exe)
set "ADDON_DST=%BLENDER_ADDONS_DIR%\io_scene_niftools"
if not exist "%ADDON_DST%\dependencies\bin" mkdir "%ADDON_DST%\dependencies\bin"
if exist "%ROOT%\bin\texconv.exe" (
  echo Copying texconv.exe to "%ADDON_DST%\dependencies\bin\texconv.exe"
  copy /y "%ROOT%\bin\texconv.exe" "%ADDON_DST%\dependencies\bin\texconv.exe" >nul 2>&1
) else (
  echo WARNING: "%ROOT%\bin\texconv.exe" not found. Auto-convert to DXT1 will fall back to PATH.
)

if exist "%ROOT%\bin\ToonRamp.png" (
  echo Copying ToonRamp.png to "%ADDON_DST%\dependencies\bin\ToonRamp.png"
  copy /y "%ROOT%\bin\ToonRamp.png" "%ADDON_DST%\dependencies\bin\ToonRamp.png" >nul 2>&1
) else (
  echo WARNING: "%ROOT%\bin\ToonRamp.png" not found. Zone4 ToonRamp embedding may fail.
)

:end
