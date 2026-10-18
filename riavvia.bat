@echo off
setlocal
title CarpeDiem Baskin - Riavvio pulito
cd /d "%~dp0"

echo ============================================
echo   Riavvio pulito del server CarpeDiem
echo ============================================
echo.

echo [1/2] Chiudo eventuali server gia attivi sulla porta 8000...
set KILLED=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  taskkill /f /pid %%a >nul 2>nul && set KILLED=1
)
echo   Porta 8000 liberata.
echo.

echo [2/2] Avvio un nuovo server...
call "%~dp0avvia.bat"

endlocal
