@echo off
REM Installe SubtitleTranslator (appelle install.ps1 via PowerShell).
REM Usage : install.bat [--no-hf] [--no-argos]
REM   --no-hf     : ne pas installer le backend Hugging Face
REM   --no-argos  : ne pas installer le backend Argos Translate
setlocal

set "PS_EXTRA="

:parse_args
if "%~1"=="" goto :run
if /i "%~1"=="--no-hf"    set "PS_EXTRA=%PS_EXTRA% -NoHF"    & shift & goto :parse_args
if /i "%~1"=="--no-argos" set "PS_EXTRA=%PS_EXTRA% -NoArgos" & shift & goto :parse_args
echo Option inconnue : %~1 1>&2
exit /b 1

:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %PS_EXTRA%
exit /b %ERRORLEVEL%
