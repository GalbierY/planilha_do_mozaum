@echo off
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

set "DIST=artifacts\\pyinstaller-dist\\SAS Civitas"
set "EXE=%DIST%\\SAS Civitas.exe"
set "INNO=artifacts\\inno-output\\SAS Civitas - Instalador.exe"

if not exist "%EXE%" (
  echo EXE nao encontrado em "%EXE%".
  echo Rode primeiro: GERAR_EXE.cmd
  exit /b 1
)

if not exist "release" mkdir "release"
if not exist "release\\portable" mkdir "release\\portable"

if exist "release\\portable\\SAS Civitas" rmdir /s /q "release\\portable\\SAS Civitas"
xcopy /e /i /y "%DIST%" "release\\portable\\SAS Civitas\\" >nul

if exist "release\\SAS Civitas - Portable.zip" del /q "release\\SAS Civitas - Portable.zip"
tar -a -c -f "release\\SAS Civitas - Portable.zip" -C "release\\portable" "SAS Civitas"
if errorlevel 1 exit /b %errorlevel%

if exist "%INNO%" (
  copy /y "%INNO%" "release\\SAS Civitas - Instalador.exe" >nul
) else (
  echo Aviso: instalador nao encontrado em "%INNO%".
)

echo SHA256SUMS:
(
  if exist "release\\SHA256SUMS.txt" del /q "release\\SHA256SUMS.txt"
) >nul 2>nul

call :hash "release\\SAS Civitas - Portable.zip" >> "release\\SHA256SUMS.txt"
if exist "release\\SAS Civitas - Instalador.exe" call :hash "release\\SAS Civitas - Instalador.exe" >> "release\\SHA256SUMS.txt"

type "release\\SHA256SUMS.txt"
echo.
echo Pronto. Pasta para commit: release\\
exit /b 0

:hash
for /f "tokens=1" %%H in ('certutil -hashfile "%~1" SHA256 ^| findstr /r /c:"^[0-9A-Fa-f][0-9A-Fa-f]"') do (
  echo %%H  %~nx1
  goto :eof
)
exit /b 0
