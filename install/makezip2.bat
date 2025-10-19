@echo off

set "DIR=%~dps0"
:: remove trailing backslash
if "%DIR:~-1%" == "\" (
    set "DIR=%DIR:~0,-1%"
)

for %%I in ("%DIR%\..") do set "ROOT=%%~fI"
set "NAME=blender_niftools_addon"
set /p VERSION=<%ROOT%\io_scene_niftools\VERSION.txt
:: Abuse for loop to execute and store command output
for /f %%i in ('git rev-parse --short HEAD') do set HASH=%%i
for /f %%i in ('echo %date%') do set DATE=%%i
set "ZIP_NAME=%NAME%-%VERSION%-%DATE%-%HASH%"
set PYFFI_VERSION="2.2.4.dev3"
set DEPS="io_scene_niftools\dependencies"
set "GENERATED_FOLDER=%ROOT%\dependencies\nifgen"
if exist "%DIR%\temp" rmdir /s /q "%DIR%\temp"

mkdir "%DIR%"\temp

pushd "%DIR%"\temp
mkdir io_scene_niftools
xcopy /s "%ROOT%\io_scene_niftools" io_scene_niftools
mkdir "%DEPS%"

python -m pip install "PyFFI==%PYFFI_VERSION%" --target="%DEPS%"

xcopy "%GENERATED_FOLDER%" "%DEPS%\nifgen" /s /q /i

:: Copy obfuscated files
xcopy "%ROOT%\dist_obfuscated\license_check.py" "io_scene_niftools" /y
xcopy "%ROOT%\dist_obfuscated\nif_export_op.py" "io_scene_niftools\operators" /y
xcopy "%ROOT%\dist_obfuscated\nif_import_op.py" "io_scene_niftools\operators" /y
xcopy "%ROOT%\dist_obfuscated\kf_export_op.py" "io_scene_niftools\operators" /y
xcopy "%ROOT%\dist_obfuscated\kf_import_op.py" "io_scene_niftools\operators" /y
xcopy "%ROOT%\dist_obfuscated\egm_import_op.py" "io_scene_niftools\operators" /y

:: Copy PyArmor runtime to dependencies
xcopy /e /i /y "%ROOT%\dist_obfuscated\pyarmor_runtime_000000" "%DEPS%\pyarmor_runtime_000000"

:: Copy texconv.exe to dependencies/bin
if not exist "%DEPS%\bin" mkdir "%DEPS%\bin"
if exist "%ROOT%\bin\texconv.exe" (
    xcopy /y "%ROOT%\bin\texconv.exe" "%DEPS%\bin"
)

xcopy "%ROOT%"\AUTHORS.rst io_scene_niftools
xcopy "%ROOT%"\CHANGELOG.rst io_scene_niftools
xcopy "%ROOT%"\LICENSE.rst io_scene_niftools
xcopy "%ROOT%"\README.rst io_scene_niftools

:: remove all __pycache__ folders
for /d /r %%x in (*) do if "%%~nx" == "__pycache__" rd %%x /s /q

popd

set "COMMAND_FILE=%DIR%\zip.ps1"
set "COMMAND_FILE=%COMMAND_FILE: =` %"

set "SOURCE_DIR=%DIR%\temp\io_scene_niftools"
set "SOURCE_DIR=%SOURCE_DIR: =` %"

set "DESTINATION_DIR=%DIR%\%ZIP_NAME%.zip"
set "DESTINATION_DIR=%DESTINATION_DIR: =` %"

powershell -executionpolicy bypass -Command "%COMMAND_FILE%" -source "%SOURCE_DIR%" -destination "%DESTINATION_DIR%"
rmdir /s /q "%DIR%\temp"
