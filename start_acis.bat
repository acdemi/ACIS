@echo off
setlocal
set "ACIS_SCRIPT=%~dp0scripts\start_acis.ps1"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ACIS_SCRIPT%" -Action start %*
set "ACIS_EXIT_CODE=%ERRORLEVEL%"
if not "%ACIS_EXIT_CODE%"=="0" pause
exit /b %ACIS_EXIT_CODE%
