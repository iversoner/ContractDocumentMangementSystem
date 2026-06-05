@echo off
setlocal enabledelayedexpansion

title Suzhen Management System - Setup

cd /d "%~dp0"

:main
cls
echo.
echo  ======================================================================
echo  =                                                                      =
echo  =              Suzhen Management System - Setup                        =
echo  =                                                                      =
echo  ======================================================================
echo.
echo   This script will help you:
echo.
echo     1. Check Docker environment
echo     2. Import system images
echo     3. Start services
echo.
echo  ======================================================================
echo.
echo Press any key to continue...
pause >nul

:check_files
cls
echo.
echo  ======================================================================
echo   Step 1/4: Check Required Files
echo  ======================================================================
echo.

if exist suzhen-images.tar goto check1_ok
goto check1_fail
:check1_fail
echo   [ERROR] suzhen-images.tar not found (system image file)
echo   Please ensure this file is in the same directory as setup.bat.
echo.
echo Press any key to exit...
pause >nul
exit /b 1
:check1_ok
echo   [OK] suzhen-images.tar found

if exist docker-compose.yaml goto check2_ok
goto check2_fail
:check2_fail
echo   [ERROR] docker-compose.yaml not found
echo   Please ensure this file is in the same directory as setup.bat.
echo.
echo Press any key to exit...
pause >nul
exit /b 1
:check2_ok
echo   [OK] docker-compose.yaml found
echo.
timeout /t 2 >nul

:check_docker
cls
echo.
echo  ======================================================================
echo   Step 2/4: Check Docker Installation
echo  ======================================================================
echo.

docker --version >nul 2>&1
if not errorlevel 1 goto docker_ok
goto docker_fail

:docker_ok
echo   [OK] Docker is installed
docker --version
echo.
goto import_images

:docker_fail
echo   [ERROR] Docker not detected
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

docker --version >nul 2>&1
if not errorlevel 1 goto docker_ok2
goto docker_fail2

:docker_ok2
echo   [OK] Docker is now available
goto import_images

:docker_fail2
echo.
echo   [ERROR] Docker still not detected, please confirm:
echo     1. Docker Desktop is installed
echo     2. System has been restarted
echo     3. Docker Desktop is running (check system tray icon)
echo.
set /p RETRY="   Retry detection? (Y/N, default Y): "
if /i "!RETRY!"=="" set RETRY=Y
if /i "!RETRY!"=="Y" goto check_docker
echo   Exiting script...
echo Press any key to exit...
pause >nul
exit /b 1

:import_images
cls
echo.
echo  ======================================================================
echo   Step 3/4: Import System Images
echo  ======================================================================
echo.

echo   Importing images from suzhen-images.tar...
echo   This may take a few minutes, please wait...
echo.

docker load -i suzhen-images.tar
if errorlevel 1 goto import_fail
goto import_ok

:import_fail
echo.
echo   [ERROR] Failed to import images
echo.
echo Press any key to exit...
pause >nul
exit /b 1
:import_ok
echo.
echo   [OK] Images imported successfully
echo.
timeout /t 2 >nul

:configure_start
cls
echo.
echo  ======================================================================
echo   Step 4/4: Configure and Start Services
echo  ======================================================================
echo.

echo   The system needs to store database and uploaded files on local disk.
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

if "!DATA_DIR:~-1!"=="\" set DATA_DIR=!DATA_DIR:~0,-1!

if exist !DATA_DIR! goto data_dir_ok
goto data_dir_create

:data_dir_create
echo   [INFO] Directory does not exist, creating...
mkdir !DATA_DIR! 2>nul
if errorlevel 1 goto data_dir_fail
goto data_dir_ok

:data_dir_fail
echo   [ERROR] Unable to create directory !DATA_DIR!
echo   Please check if path is valid and you have write permissions.
echo.
echo Press any key to retry...
pause >nul
goto configure_start

:data_dir_ok
echo   [OK] Data directory: !DATA_DIR!
echo.

set PORT=8080
set /p PORT="   Enter service port (default 8080, press Enter): "
if "!PORT!"=="" set PORT=8080

echo.
echo   [1/2] Generating configuration file...
(
    echo DATA_DIR=!DATA_DIR!
    echo APP_PORT=!PORT!
) > .env

echo   [2/2] Starting services...
echo.
docker compose -f docker-compose.yaml up -d
if errorlevel 1 goto try_legacy
goto services_ok

:try_legacy
docker-compose -f docker-compose.yaml up -d
if errorlevel 1 goto services_fail
goto services_ok

:services_fail
echo.
echo   [ERROR] Startup failed, possible causes:
echo     1. Docker service temporarily unavailable - please retry
echo     2. Port !PORT! is occupied - please use a different port
echo     3. Docker Desktop not fully started - wait for tray icon to stabilize
echo.
echo   Please close this window and run the script again.
echo.
echo Press any key to exit...
pause >nul
exit /b 1

:services_ok
echo.
echo   Waiting for services to start...
timeout /t 5 >nul

:done
cls
echo.
echo  ======================================================================
echo  =                                                                      =
echo  =                      Installation Successful!                        =
echo  =                                                                      =
echo  ======================================================================
echo.
echo    System Access Address:
echo.
echo        http://localhost:!PORT!
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
echo       View logs:          docker compose -f docker-compose.yaml logs -f
echo       Restart services:   docker compose -f docker-compose.yaml restart
echo.
echo  ======================================================================
echo.
echo   Press any key to open the system...
pause >nul
start "" "http://localhost:!PORT!"
exit /b 0