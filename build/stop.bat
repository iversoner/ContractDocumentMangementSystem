@echo off

title 素珍管理系统 - 停止服务

cd /d "%~dp0"

echo.
echo ======================================
echo   素珍管理系统
echo   正在停止所有服务...
echo ======================================
echo.

echo 停止 Docker 容器...
docker compose -f docker-compose.yaml down 2>nul
if errorlevel 1 docker-compose -f docker-compose.yaml down 2>nul

echo.
echo ======================================
echo   所有服务已停止。
echo ======================================
echo.
echo   如需重新启动，请双击 setup.bat。
echo.
pause
