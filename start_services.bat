@echo off
echo Starting CyberRisk Phase 2 Services...

REM Start API server in new window
start "CyberRisk API" cmd /k "cd /d %~dp0 && uvicorn api.main:app --port 8000 --reload"

REM Wait a moment for API to start
timeout /t 3 /nobreak >nul

REM Start Frontend in new window  
start "CyberRisk Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo Both services starting...
echo API: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to close this window...
pause >nul 