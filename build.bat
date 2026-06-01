@echo off
setlocal enabledelayedexpansion

title 素珍管理系统 - 构建交付包

cd /d "%~dp0"

:: ============================================================
::  素珍管理系统 — 开发者构建打包脚本
::  构建 Docker 镜像 → 导出 tar → 放到 build/ 目录
:: ============================================================

:main
cls
echo.
echo  ======================================================================
echo  ║                                                                      ║
echo  ║              素珍管理系统 - 构建交付包                              ║
echo  ║              Build Delivery Package                                  ║
echo  ║                                                                      ║
echo  ======================================================================
echo.
echo   此脚本将：
echo     1. 构建前端和后端 Docker 镜像
echo     2. 导出镜像为 build\suzhen-images.tar
echo     3. 打包 build\ 为 suzhen-system-v1.0.zip
echo.
echo  ======================================================================
echo.

:: 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] 未检测到 Docker，请先安装 Docker Desktop
    pause
    exit /b 1
)
echo   [OK] Docker 已就绪
echo.

:: 配置 DaoCloud 镜像加速（加速基础镜像拉取）
echo   配置 Docker 镜像加速 (DaoCloud)...
set DOCKER_CONFIG=%USERPROFILE%\.docker
if not exist "%DOCKER_CONFIG%" mkdir "%DOCKER_CONFIG%"
set DAEMON_FILE=%DOCKER_CONFIG%\daemon.json
if exist "%DAEMON_FILE%" (
    echo   [INFO] 备份现有 daemon.json
    copy /y "%DAEMON_FILE%" "%DAEMON_FILE%.bak" >nul
)
(
    echo {
    echo     "registry-mirrors": ["https://www.daocloud.io/mirror"]
    echo }
) > "%DAEMON_FILE%"
echo   [OK] 镜像加速已配置: https://www.daocloud.io/mirror
echo   [INFO] 如果 Docker Desktop 正在运行，请手动重启它
echo.

:: ============================================================
:: Step 1: 构建镜像
:: ============================================================
echo   [1/3] 构建 Docker 镜像...
echo.

docker compose -f docker/docker-compose.yaml build
if errorlevel 1 (
    docker-compose -f docker/docker-compose.yaml build
    if errorlevel 1 (
        echo.
        echo   [ERROR] 镜像构建失败！请检查错误信息。
        pause
        exit /b 1
    )
)

echo.
echo   [OK] 镜像构建完成
echo.

:: ============================================================
:: Step 2: 导出镜像到 build/
:: ============================================================
echo   [2/3] 导出镜像到 build\suzhen-images.tar ...
echo.

if not exist "build" mkdir "build"

docker save -o "build\suzhen-images.tar" suzhen-backend:latest suzhen-frontend:latest
if errorlevel 1 (
    echo   [ERROR] 镜像导出失败！
    pause
    exit /b 1
)

echo   [OK] 镜像已导出
echo.

:: ============================================================
:: Step 3: 打包 build/ 为 zip
:: ============================================================
echo   [3/3] 打包 build\ 为 suzhen-system-v1.0.zip ...
echo.

powershell -Command "Compress-Archive -Path 'build\*' -DestinationPath 'suzhen-system-v1.0.zip' -Force"
if errorlevel 1 (
    echo   [ERROR] 打包失败！
    pause
    exit /b 1
)

echo.
echo  ======================================================================
echo  ║                                                                      ║
echo  ║                     构建完成！                                      ║
echo  ║                                                                      ║
echo  ======================================================================
echo.
echo   交付包位置: suzhen-system-v1.0.zip
echo.
echo   build\ 目录内容（客户交付文件）:
echo     - setup.bat              客户一键启动脚本
echo     - stop.bat               停止服务脚本
echo     - suzhen-images.tar      预构建 Docker 镜像
echo     - docker-compose.yaml    服务编排配置
echo     - nginx.conf             Nginx 配置
echo.
echo  ======================================================================
echo   交付给客户的操作步骤:
echo  ======================================================================
echo.
echo   1. 将 suzhen-system-v1.0.zip 发送给客户
echo   2. 客户解压 zip 到任意目录
echo   3. 客户双击 setup.bat → 输入端口 → 自动启动
echo   4. 浏览器自动打开，开始使用
echo.
echo   客户需要预先安装 Docker Desktop！
echo.
echo  ======================================================================
echo.
echo   按任意键退出...
pause >nul
exit /b 0
