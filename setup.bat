@echo off
setlocal enabledelayedexpansion
title Suzhen Management System - One-Click Installation

cd /d "%~dp0"

:: ============================================================
::  Suzhen Management System - One-Click Installation Script
::  Detects environment, installs Docker, configures mirror, starts services
:: ============================================================

:main
cls
echo.
echo  ======================================================================
echo  =                                                                     =
echo  =              Suzhen Management System - One-Click Setup             =
echo  =                                                                     =
echo  ======================================================================
echo.
echo   This script will perform the following operations:
echo.
echo     1. Check Docker installation
echo     2. Configure registry mirror
echo     3. Select data storage directory
echo     4. Get local IP and configure port
echo     5. Build and start services
echo.
echo  ======================================================================
echo.
pause

:: ============================================================
:: Step 1: Check Docker
:: ============================================================
:check_docker
cls
echo.
echo  ======================================================================
echo   Step 1/5: Check Docker Installation
echo  ======================================================================
echo.

docker --version >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Docker is already installed
    docker --version
    echo.
    goto :configure_mirror
)

echo   [WARN] Docker not detected
echo.
echo   Docker Desktop is required to run this system.
echo   Opening Docker Desktop download page...
echo.
echo   Please download and install Docker Desktop, then return to this window.
echo.
echo   Docker Desktop download URL:
echo   https://www.docker.com/products/docker-desktop
echo.
set /p OPEN="   Open browser to download page? (Y/N, default Y): "
if /i "!OPEN!"=="" set OPEN=Y
if /i "!OPEN!"=="Y" start "" "https://www.docker.com/products/docker-desktop"

echo.
echo   ============================================
echo   Docker Desktop Installation Notes:
echo   - During installation, check "Use WSL 2 instead of Hyper-V" (recommended)
echo   - Restart required after installation
echo   - Docker Desktop will start automatically
echo   ============================================
echo.
set /p DONE="   Press Enter after installation is complete..."

:: Check again
docker --version >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Docker is now available
    goto :configure_mirror
)

echo.
echo   [WARN] Docker still not detected, please confirm:
echo     1. Docker Desktop is installed
echo     2. System has been restarted
echo     3. Docker Desktop is running (check system tray icon)
echo.
set /p RETRY="   Retry detection? (Y/N, default Y): "
if /i "!RETRY!"=="" set RETRY=Y
if /i "!RETRY!"=="Y" goto :check_docker
echo   Skipping Docker check, exiting script...
pause
exit /b 1

:: ============================================================
:: Step 2: Configure Docker registry mirror
:: ============================================================
:configure_mirror
cls
echo.
echo  ======================================================================
echo   Step 2/5: Configure Registry Mirror
echo  ======================================================================
echo.
echo   To improve Docker image download speed, configure a mirror accelerator:
echo.
echo   Recommended sources:
echo     [1] DaoCloud Mirror (recommended)
echo     [2] 1ms.run Mirror
echo     [3] Alibaba Cloud Mirror
echo     [4] Skip, use default (may be slow)
echo.
set /p MIRROR_CHOICE="   Please select (1/2/3/4, default 1): "
if "!MIRROR_CHOICE!"=="" set MIRROR_CHOICE=1

if "!MIRROR_CHOICE!"=="1" set MIRROR_URL=https://www.daocloud.io/mirror
if "!MIRROR_CHOICE!"=="2" set MIRROR_URL=https://docker.1ms.run
if "!MIRROR_CHOICE!"=="3" set MIRROR_URL=https://registry.cn-hangzhou.aliyuncs.com
if "!MIRROR_CHOICE!"=="4" goto :skip_mirror

echo.
echo   Setting Docker mirror source: !MIRROR_URL!

:: Create Docker daemon.json
set DOCKER_CONFIG=%USERPROFILE%\.docker
if not exist "%DOCKER_CONFIG%" mkdir "%DOCKER_CONFIG%"

:: Backup existing configuration if exists
set DAEMON_FILE=%DOCKER_CONFIG%\daemon.json
if exist "%DAEMON_FILE%" (
    echo   [INFO] Existing Docker config detected, backing up to daemon.json.bak
    copy /y "%DAEMON_FILE%" "%DAEMON_FILE%.bak" >nul
)

:: Write new configuration
(
    echo {
    echo     "registry-mirrors": ["!MIRROR_URL!"]
    echo }
) > "%DAEMON_FILE%"

echo   [OK] Configuration written to: %DAEMON_FILE%
echo.
echo   [INFO] Changes will take effect after restarting Docker Desktop
echo   [INFO] If Docker Desktop is running, please restart manually:
echo         System tray icon -> Right click -> Restart
echo.

:: Also try via docker desktop CLI
docker config ls >nul 2>&1

:skip_mirror

:: ============================================================
:: Step 3: Choose data directory
:: ============================================================
:choose_data_dir
cls
echo.
echo  ======================================================================
echo   Step 3/5: Select Data Storage Directory
echo  ======================================================================
echo.
echo   The system needs to store database and uploaded files on local disk.
echo   Please select a directory to store this data.
echo.
echo   Recommendations:
echo     - D:\suzhen-data
echo     - E:\suzhen-data
echo     - Press Enter directly to use default: %~dp0data
echo.
echo   Note: Avoid system drive (C:) or temporary directories to prevent data loss
echo.

set DATA_DIR=%~dp0data
set /p USER_DATA="   Enter data storage directory path (or press Enter for default): "
if not "!USER_DATA!"=="" set DATA_DIR=!USER_DATA!

:: Remove trailing backslash
if "!DATA_DIR:~-1!"=="\" set DATA_DIR=!DATA_DIR:~0,-1!

:: Create directory
if not exist "!DATA_DIR!" (
    echo   [INFO] Directory does not exist, creating...
    mkdir "!DATA_DIR!" 2>nul
    if errorlevel 1 (
        echo   [ERROR] Unable to create directory !DATA_DIR!
        echo   Please check if path is valid and you have write permissions.
        pause
        goto :choose_data_dir
    )
)
echo   [OK] Data directory: !DATA_DIR!

:: Docker Desktop on Windows uses Windows path format directly
set DOCKER_DATA_DIR=!DATA_DIR!

:: ============================================================
:: Step 4: Get local IP
:: ============================================================
:get_ip
cls
echo.
echo  ======================================================================
echo   Step 4/5: Get Local IP Address
echo  ======================================================================
echo.

:: Get local IPv4 address - prefer WLAN adapter over VMware/Ethernet
set LOCAL_IP=localhost

:: Use PowerShell Get-NetIPAddress to find the best IP: prefer Wi-Fi, skip virtual adapters
for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command ^
  "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' } | ForEach-Object { $iface=$_|Get-NetAdapter; [pscustomobject]@{IP=$_.IPAddress;Name=$iface.Name;IsVM=$iface.Name -match 'VMware|VirtualBox|Hyper-V';IsWLAN=$iface.Name -match 'Wi-Fi|Wireless|WLAN'} } | Sort-Object {if($_.IsVM){2}elseif($_.IsWLAN){0}else{1}} | Select-Object -First 1 -ExpandProperty IP"`) do (
    set LOCAL_IP=%%a
)

if "!LOCAL_IP!"=="" set LOCAL_IP=localhost

:ip_found
echo   Local IP Address: !LOCAL_IP!
echo.
set /p PORT="   Enter service port (default 8080, press Enter): "
if "!PORT!"=="" set PORT=8080

:: ============================================================
:: Step 5: Build and start
:: ============================================================
:start_services
cls
echo.
echo  ======================================================================
echo   Step 5/5: Build Images and Start Services
echo  ======================================================================
echo.
echo   Data directory: !DATA_DIR!
echo   Service port:   !PORT!
echo   Local IP:       !LOCAL_IP!
echo.
echo   Starting to initialize services, this may take a few minutes...
echo.

:: Stop existing services
echo   [1/3] Stopping existing services...
docker compose -f docker/docker-compose.yaml down 2>nul
if errorlevel 1 docker-compose -f docker/docker-compose.yaml down 2>nul

:: Write .env file
echo   [2/3] Generating configuration file...
(
    echo DATA_DIR=!DOCKER_DATA_DIR!
    echo APP_PORT=!PORT!
    echo HOST_DATA_DIR=!DATA_DIR!
) > docker\.env

:: Start services
echo   [3/3] Building images and starting services (first run will be slower)...
echo.
docker compose -f docker/docker-compose.yaml up -d --build
if errorlevel 1 (
    docker-compose -f docker/docker-compose.yaml up -d --build
    if errorlevel 1 (
        echo.
        echo   [ERROR] Startup failed, possible causes:
        echo     1. Docker service temporarily unavailable - please retry
        echo     2. Port !PORT! is occupied - please use a different port
        echo     3. Docker Desktop not fully started - wait for tray icon to stabilize
        echo.
        echo   Please close this window and run the script again.
        pause
        exit /b 1
    )
)

:: Wait for services to start
echo.
echo   Waiting for services to start...
timeout /t 5 >nul

:: ============================================================
:: Done
:: ============================================================
:done
cls
echo.
echo  ======================================================================
echo                                                                       
echo                       Installation Successful!                        
echo                                                                        
echo  ======================================================================
echo.
echo    System Access Address:
echo.
if "!LOCAL_IP!"=="localhost" (
    echo        http://localhost:!PORT!
) else (
    echo        http://localhost:!PORT!
    echo        http://!LOCAL_IP!:!PORT!          ^(Accessible from other devices on LAN^)
)
echo.
echo  ======================================================================
echo    Initial Login Credentials
echo  ======================================================================
echo.
echo       Username:   admin
echo       Password:   admin!
echo.
echo    Please change password after first login!
echo.
echo  ======================================================================
echo    Data Storage
echo  ======================================================================
echo.
echo       Database and uploaded files stored in: !DATA_DIR!
echo       Do not delete this directory!
echo.
echo  ======================================================================
echo    Common Commands
echo  ======================================================================
echo.
echo       Stop services:      Double-click stop.bat
echo       View logs:          docker compose -f docker/docker-compose.yaml logs -f
echo       Restart services:   docker compose -f docker/docker-compose.yaml restart
echo.
echo  ======================================================================
echo.
echo   Press any key to open the system...
pause >nul
start "" "http://localhost:!PORT!"
exit /b 0
