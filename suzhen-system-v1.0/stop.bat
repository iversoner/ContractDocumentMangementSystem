@echo off

title Suzhen Management System - Stop

cd /d "%~dp0"

echo.
echo ======================================
echo   Suzhen Management System
echo   Stopping all services...
echo ======================================
echo.

echo Stopping Docker containers...
docker compose -f docker-compose.yaml down 2>nul
if errorlevel 1 docker-compose -f docker-compose.yaml down 2>nul

echo.
echo ======================================
echo   All services stopped.
echo   Data is preserved on local disk.
echo ======================================
echo.
echo   To restart, run setup.bat again.
echo.
pause
