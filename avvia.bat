@echo off
setlocal
title CarpeDiem Baskin - Avvio locale
cd /d "%~dp0"

echo ============================================
echo   CarpeDiem Baskin - avvio ambiente locale
echo ============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERRORE] Python non trovato. Installa Python da https://www.python.org/downloads/
  echo          Ricordati di spuntare "Add python.exe to PATH" durante l'installazione.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creo l'ambiente virtuale...
  py -m venv .venv
  if errorlevel 1 ( echo [ERRORE] Creazione ambiente fallita. & pause & exit /b 1 )
  echo [2/3] Installo le dipendenze...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
  if errorlevel 1 ( echo [ERRORE] Installazione dipendenze fallita. & pause & exit /b 1 )
) else (
  echo [1/3] Ambiente virtuale gia presente.
  echo [2/3] Dipendenze gia installate.
)

if not exist "carpediem.db" (
  echo [3/3] Popolo il database con dati di esempio...
  ".venv\Scripts\python.exe" -m app.seed
) else (
  echo [3/3] Database gia presente.
)

echo.
echo Avvio il server su http://127.0.0.1:8000
echo Premi CTRL+C in questa finestra per fermarlo.
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul & start "" http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

pause
endlocal
