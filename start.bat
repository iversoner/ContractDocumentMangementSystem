@echo off
setlocal enabledelayedexpansion

title Suzhen Management - Start

cd /d "%~dp0"

echo.
echo ======================================
echo   Suzhen Management System
echo ======================================
echo.
echo   Select start mode:
echo.
echo   [1] Full-stack Docker (frontend + backend)
echo   [2] Local backend only (Flask dev server)
echo   [3] Docker frontend + Local backend
echo   [0] Exit
echo.
set /p MODE="Enter option (1/2/3/0): "
echo.

if "%MODE%"=="1" call :start_docker_full
if "%MODE%"=="2" call :start_backend
if "%MODE%"=="3" call :start_both
if "%MODE%"=="0" goto :exit

if not defined FINISHED (
    echo Invalid option. Please re-run.
    pause
)
exit /b 0

:: ============================================================
:start_docker_full
    echo.
    echo --- Full-stack Docker ---
    echo.

    docker --version >nul 2>&1
    if errorlevel 1 (
        echo Docker not found. Please install Docker Desktop.
        echo Download: https://www.docker.com/products/docker-desktop
        echo.
        echo After install, configure registry mirror:
        echo Docker Desktop ^> Settings ^> Docker Engine, add:
        echo   "registry-mirrors": ["https://www.daocloud.io/mirror"]
        echo Apply ^& Restart, then re-run this script.
        echo.
        set /p OPEN="Open download page? (Y/N): "
        if /i "!OPEN!"=="Y" start "" "https://www.docker.com/products/docker-desktop"
        pause
        exit /b 1
    )

    echo [1/2] Stopping old containers...
    docker compose -f docker/docker-compose.yaml down 2>nul
    if errorlevel 1 (
        docker-compose -f docker/docker-compose.yaml down 2>nul
    )
    REM Also stop any containers from mode 3 that use suzhen-net
    docker stop suzhen-frontend 2>nul
    docker rm suzhen-frontend 2>nul
    docker network rm suzhen-net 2>nul

    echo [2/2] Building and starting...
    docker compose -f docker/docker-compose.yaml up -d --build
    if errorlevel 1 (
        docker-compose -f docker/docker-compose.yaml up -d --build
        if errorlevel 1 (
            echo.
            echo Build failed. Common issues:
            echo   1. Docker Hub unreachable - configure registry mirror
            echo   2. Port 8080 in use - edit docker/docker-compose.yaml
            echo   3. Image pull timeout - check network
            pause
            exit /b 1
        )
    )

    echo.
    echo Waiting for backend to be ready...
    timeout /t 3 >nul

    set FINISHED=1
    goto :done_full

:: ============================================================
:start_both
    call :start_backend_bg
    echo.
    echo --- Docker Frontend ---
    echo.

    docker --version >nul 2>&1
    if errorlevel 1 (
        echo Docker not found. Skipping frontend.
        goto :done
    )

    echo Building frontend image...
    docker compose -f docker/docker-compose.yaml build frontend
    if errorlevel 1 docker-compose -f docker/docker-compose.yaml build frontend

    REM Stop Docker backend and old frontend
    docker stop suzhen-backend 2>nul
    docker rm suzhen-backend 2>nul
    docker stop suzhen-frontend 2>nul
    docker rm suzhen-frontend 2>nul

    REM Get host LAN IP for nginx to reach local Flask backend
    set HOST_IP=127.0.0.1
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /r "IPv4.*192\.168\." 2^>nul') do (
        set TMP_IP=%%a
        set TMP_IP=!TMP_IP: =!
        if not "!TMP_IP!"=="" set HOST_IP=!TMP_IP!
    )

    echo Host IP: !HOST_IP!
    echo Starting frontend container (nginx proxies to !HOST_IP!:5000)...

    docker run -d --name suzhen-frontend ^
        --add-host backend:!HOST_IP! ^
        -p 8080:80 ^
        suzhen-frontend:latest

    if errorlevel 1 (
        echo Frontend container failed to start
        pause
        exit /b 1
    )

    set FINISHED=1
    goto :done

:: ============================================================
:start_backend
    echo.
    echo --- Flask Backend (dev) ---
    echo.

    set VENV_PYTHON=.venv\Scripts\python.exe

    if not exist "%VENV_PYTHON%" (
        echo .venv not found. Creating virtual environment...
        python --version >nul 2>&1
        if errorlevel 1 (
            echo Python not found. Please install Python 3.9+
            pause
            exit /b 1
        )
        python -m venv .venv
        if errorlevel 1 (
            echo Failed to create .venv
            pause
            exit /b 1
        )
        echo Virtual environment created.
    )

    if not exist "backend\run.py" (
        echo backend\run.py not found
        pause
        exit /b 1
    )

    echo Checking dependencies...
    %VENV_PYTHON% -m pip show Flask >nul 2>&1
    if errorlevel 1 (
        echo Installing dependencies...
        %VENV_PYTHON% -m pip install -r backend\requirements.txt
        if errorlevel 1 (
            echo Dependency install failed
            pause
            exit /b 1
        )
        echo Done.
    )

    echo.
    echo Starting backend...
    echo Access: http://localhost:5000
    echo API:    http://localhost:5000/api
    echo Press Ctrl+C to stop
    echo.
    %VENV_PYTHON% backend\run.py
    set FINISHED=1
    exit /b 0

:: ============================================================
:start_backend_bg
    echo.
    echo Starting backend in background...

    set VENV_PYTHON=.venv\Scripts\python.exe
    if not exist "%VENV_PYTHON%" goto :skip_bg

    %VENV_PYTHON% -m pip show Flask >nul 2>&1
    if errorlevel 1 %VENV_PYTHON% -m pip install -r backend\requirements.txt >nul 2>&1

    start "Suzhen-Backend" cmd /k "cd /d %~dp0 && %VENV_PYTHON% backend\run.py"
    echo Backend started in new window (http://localhost:5000)
    timeout /t 3 >nul
    :skip_bg
    exit /b 0

:: ============================================================
:done_full
    echo.
    echo ======================================
    echo   Started! (Full-stack Docker)
    echo ======================================
    echo.
    echo   Frontend : http://localhost:8080
    echo   Backend  : http://localhost:8080/api  (via nginx proxy)
    echo   Login    : admin / admin!
    echo   Stop     : double-click stop.bat
    echo ======================================
    echo.
    pause
    exit /b 0

:: ============================================================
:done
    echo.
    echo ======================================
    echo   Started!
    echo ======================================
    echo.
    echo   Frontend : http://localhost:8080
    echo   Backend  : http://localhost:5000
    echo   Login    : admin / admin!
    echo   Stop     : double-click stop.bat
    echo ======================================
    echo.
    pause
    exit /b 0

:exit
    echo Cancelled.
    exit /b 0
