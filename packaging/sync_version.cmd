@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo Sincronizando versao entre config.json e instalador...

rem Ler versao do config.json
for /f "tokens=2 delims=:, " %%a in ('findstr /C:"\"app_version\"" config\config.json') do (
    set "VERSION=%%~a"
    set "VERSION=!VERSION:"=!"
)

if "!VERSION!"=="" (
    echo Erro: Nao foi possivel ler app_version do config.json
    exit /b 1
)

echo Versao encontrada: !VERSION!

rem Atualizar instalador Inno Setup
set "ISS_FILE=packaging\installer\SAS_Civitas.iss"
set "ISS_TEMP=packaging\installer\SAS_Civitas.iss.tmp"

(
    for /f "usebackq delims=" %%a in ("%ISS_FILE%") do (
        set "line=%%a"
        echo !line! | findstr /C:"#define MyAppVersion" >nul
        if !errorlevel! equ 0 (
            echo #define MyAppVersion "!VERSION!"
        ) else (
            echo !line!
        )
    )
) > "%ISS_TEMP%"

move /y "%ISS_TEMP%" "%ISS_FILE%" >nul

echo Instalador atualizado para versao !VERSION!
echo.
echo Arquivos atualizados:
echo   - %ISS_FILE%
echo.
echo Para aplicar a versao ao executavel, reconstrua com:
echo   packaging\build_installer.cmd