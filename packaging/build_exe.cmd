@echo off
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

if not exist ".venv_build\\Scripts\\python.exe" (
  echo Creating build venv in .venv_build ...
  py -3 -m venv .venv_build
)

set "PY=%CD%\\.venv_build\\Scripts\\python.exe"

echo Installing build deps ...
"%PY%" -m pip install -U pip >nul
"%PY%" -m pip install -r requirements.txt pyinstaller

echo Building EXE (PyInstaller) ...
"%PY%" -m PyInstaller --noconfirm --clean --workpath artifacts\\pyinstaller-build --distpath artifacts\\pyinstaller-dist packaging\\sas_civitas.spec
if errorlevel 1 exit /b %errorlevel%

echo.
echo Done. Output: "artifacts\\pyinstaller-dist\\SAS Civitas\\SAS Civitas.exe"
