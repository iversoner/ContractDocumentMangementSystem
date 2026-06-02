@echo off
setlocal enabledelayedexpansion

title Suzhen Management System - Build Delivery Package

cd /d "%~dp0"

:: ============================================================
::  Suzhen Management System - Developer Build & Package Script
::  Build Docker images -> Export tar -> Put into build/ folder
:: ============================================================

:main
cls
echo.
echo  ========================================================================
echo  =                                                                      =
echo  =              Suzhen Management System - Build Package                =
echo  =                                                                      =
echo  ========================================================================
echo.
echo   This script will:
echo     1. Build frontend and backend Docker images
echo     2. Export images to build\suzhen-images.tar
echo     3. Package build\ into suzhen-system-v1.0.zip
echo.
echo  ========================================================================  
echo.

:: Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Docker not detected. Please install Docker Desktop first.
    pause
    exit /b 1
)
echo   [OK] Docker is ready
echo.

:: Configure DaoCloud registry mirror (speed up base image pulls)
echo   Configuring Docker registry mirror (DaoCloud)...
set DOCKER_CONFIG=%USERPROFILE%\.docker
if not exist "%DOCKER_CONFIG%" mkdir "%DOCKER_CONFIG%"
set DAEMON_FILE=%DOCKER_CONFIG%\daemon.json
if exist "%DAEMON_FILE%" (
    echo   [INFO] Backing up existing daemon.json
    copy /y "%DAEMON_FILE%" "%DAEMON_FILE%.bak" >nul
)
(
    echo {
    echo     "registry-mirrors": ["https://www.daocloud.io/mirror"]
    echo }
) > "%DAEMON_FILE%"
echo   [OK] Registry mirror configured: https://www.daocloud.io/mirror
echo   [INFO] If Docker Desktop is running, please restart it manually
echo.

:: ============================================================
:: Step 1: Build images
:: ============================================================
echo   [1/3] Building Docker images...
echo.

docker compose -f docker/docker-compose.yaml build
if errorlevel 1 (
    docker-compose -f docker/docker-compose.yaml build
    if errorlevel 1 (
        echo.
        echo   [ERROR] Image build failed! Check the error messages above.
        pause
        exit /b 1
    )
)

echo.
echo   [OK] Images built successfully
echo.

:: ============================================================
:: Step 2: Export images to build/
:: ============================================================
echo   [2/3] Exporting images to build\suzhen-images.tar ...
echo.

if not exist "build" mkdir "build"

docker save -o "build\suzhen-images.tar" suzhen-backend:latest suzhen-frontend:latest
if errorlevel 1 (
    echo   [ERROR] Image export failed!
    pause
    exit /b 1
)

echo   [OK] Images exported
echo.

:: ============================================================
:: Step 3: Package build/ into zip
:: ============================================================
echo   [3/3] Packaging build\ into suzhen-system-v1.0.zip ...
echo.

powershell -Command "Compress-Archive -Path 'build\*' -DestinationPath 'suzhen-system-v1.0.zip' -Force"
if errorlevel 1 (
    echo   [ERROR] Packaging failed!
    pause
    exit /b 1
)

echo.
echo  ========================================================================
echo  =                                                                      =
echo  =                     Build Complete!                                  =
echo  =                                                                      =
echo  ========================================================================  
echo.
echo   Delivery package: suzhen-system-v1.0.zip
echo.
echo   build\ directory contents (customer delivery files):
echo     - setup.bat              Customer one-click startup script
echo     - stop.bat               Stop services script
echo     - suzhen-images.tar      Pre-built Docker images
echo     - docker-compose.yaml    Service orchestration config
echo     - nginx.conf             Nginx configuration
echo.
echo  ======================================================================
echo   Customer delivery steps:
echo  ======================================================================
echo.
echo   1. Send suzhen-system-v1.0.zip to the customer
echo   2. Customer unzips to any directory
echo   3. Customer double-clicks setup.bat -> enters port -> auto startup
echo   4. Browser opens automatically, ready to use
echo.
echo   Customer must have Docker Desktop pre-installed!
echo.
echo  ======================================================================
echo.
echo   Press any key to exit...
pause >nul
exit /b 0
