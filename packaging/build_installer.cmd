@echo off
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

where /q iscc.exe
if errorlevel 1 (
  rem Common winget per-user install path:
  if exist "%LocalAppData%\\Programs\\Inno Setup 6\\ISCC.exe" (
    set "ISCC=%LocalAppData%\\Programs\\Inno Setup 6\\ISCC.exe"
  ) else (
    echo Inno Setup compiler not found ^(iscc.exe^).
    echo Install Inno Setup, or add ISCC.exe to PATH.
    exit /b 1
  )
) else (
  set "ISCC=iscc.exe"
)

call "%~dp0build_exe.cmd"
if errorlevel 1 exit /b %errorlevel%

echo Building installer (Inno Setup) ...
"%ISCC%" "%~dp0installer\\SAS_Civitas.iss"

echo.
echo Done. Output: artifacts\\inno-output\\SAS Civitas - Instalador.exe
