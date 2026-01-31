@echo off
setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo Install/Upgrade PyArmor (Blender Python)
echo ============================================================
echo.

:: Locate highest Blender version
set "BEST_PY="
set "BEST_VER="
for %%B in (
  "%PROGRAMFILES%\Blender Foundation\Blender*"
  "%PROGRAMFILES(X86)%\Blender Foundation\Blender*"
  "%LOCALAPPDATA%\Programs\Blender Foundation\Blender*"
) do (
  for /f "delims=" %%D in ('dir /b /ad "%%~B" 2^>nul') do (
    set "CAND=%%~B\%%D\python\bin\python.exe"
    if exist "!CAND!" (
      set "VER=%%D"
      set "VER=!VER:Blender =!"
      set "VER=!VER:Blender=!"
      set "VER=!VER: =!"
      if "!BEST_VER!"=="" (
        set "BEST_VER=!VER!"
        set "BEST_PY=!CAND!"
      ) else (
        call :CompareVer "!VER!" "!BEST_VER!"
        if "!CMP!"=="GT" (
          set "BEST_VER=!VER!"
          set "BEST_PY=!CAND!"
        )
      )
    )
  )
)

if not defined BEST_PY (
  echo Blender Python not found automatically.
  set /p "USER_BLENDER_DIR=Enter Blender install folder (e.g. C:\Program Files\Blender Foundation\Blender 4.5): "
  if "%USER_BLENDER_DIR%"=="" goto end
  set "BEST_PY=%USER_BLENDER_DIR%\python\bin\python.exe"
)

if not exist "%BEST_PY%" (
  echo ERROR: Blender Python not found at:
  echo   %BEST_PY%
  goto end
)

echo Using Blender Python:
echo   %BEST_PY%
echo.

echo Upgrading pip...
"%BEST_PY%" -m pip install --upgrade pip
if errorlevel 1 goto end

echo Installing/Upgrading PyArmor...
"%BEST_PY%" -m pip install --upgrade pyarmor
if errorlevel 1 goto end

echo Verifying PyArmor...
"%BEST_PY%" -m pyarmor.cli -h
if errorlevel 1 goto end

echo.
echo ============================================================
echo PyArmor install complete.
echo ============================================================
echo.
pause
goto :eof

:CompareVer
:: Compare dotted version strings (e.g., 4.5 vs 3.6.2)
:: Sets CMP=GT if %1 > %2, CMP=LT if %1 < %2, CMP=EQ if equal
set "A=%~1"
set "B=%~2"
for /f "tokens=1-4 delims=." %%a in ("%A%") do (
  set "A1=%%a"& set "A2=%%b"& set "A3=%%c"& set "A4=%%d"
)
for /f "tokens=1-4 delims=." %%a in ("%B%") do (
  set "B1=%%a"& set "B2=%%b"& set "B3=%%c"& set "B4=%%d"
)
if not defined A2 set A2=0
if not defined A3 set A3=0
if not defined A4 set A4=0
if not defined B2 set B2=0
if not defined B3 set B3=0
if not defined B4 set B4=0

call :CmpNum %A1% %B1% && goto :eof
call :CmpNum %A2% %B2% && goto :eof
call :CmpNum %A3% %B3% && goto :eof
call :CmpNum %A4% %B4% && goto :eof
set "CMP=EQ"
goto :eof

:CmpNum
set "CMP=EQ"
if %1 GTR %2 set "CMP=GT" & goto :eof
if %1 LSS %2 set "CMP=LT" & goto :eof
goto :eof

:end
echo.
echo ============================================================
echo PyArmor install failed or cancelled.
echo ============================================================
echo.
pause
endlocal
