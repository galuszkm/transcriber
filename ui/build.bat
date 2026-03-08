@echo off
REM Build the Transcriber UI and output to src\transcriber\server\static
cd /d "%~dp0"

echo "==> Installing dependencies..."
call npm install
if errorlevel 1 exit /b 1

echo "==> Running tests..."
call npm run test
if errorlevel 1 exit /b 1

echo "==> Building UI..."
call npm run build
if errorlevel 1 exit /b 1

echo "==> Done. Static files written to ..\src\transcriber\server\static\"
