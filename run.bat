@echo off
REM Lance SubtitleTranslator (appelle run.ps1 via PowerShell).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
exit /b %ERRORLEVEL%
