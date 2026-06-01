@echo off

title suzhenSystem - Stop

cd /d "%~dp0"

echo.
echo ======================================
echo   suzhenSystem
echo   STOP suzhenSystem...
echo ======================================
echo.

echo STOP Docker...
docker compose -f docker/docker-compose.yaml down 2>nul
if errorlevel 1 docker-compose -f docker/docker-compose.yaml down 2>nul

echo.
echo ======================================
echo   ALL SERVICES STOPPED.
echo ======================================
echo.
echo   ALL DATA SOURCE IS SAVED LOCALY
echo   IF YOU NEED TO CLEAN ALL DATA, PLEASE DELETE THE DATA DIRECTORY.
echo.
pause
