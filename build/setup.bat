@echo off
setlocal enabledelayedexpansion

title 素珍管理系统 - 安装启动

cd /d "%~dp0"

:: ============================================================
::  素珍管理系统 — 客户一键安装启动脚本
::  检测环境、导入镜像、启动服务
:: ============================================================

:main
cls
echo.
echo  ======================================================================
echo  ║                                                                      ║
echo  ║                 素珍管理系统 - 安装启动                             ║
echo  ║                 Suzhen Management System                            ║
echo  ║                                                                      ║
echo  ======================================================================
echo.
echo   本脚本将帮助您完成以下操作：
echo.
echo     1. 检测 Docker 环境
echo     2. 导入系统镜像
echo     3. 启动服务
echo.
echo  ======================================================================
echo.

:: 检查必要文件
if not exist "suzhen-images.tar" (
    echo   [ERROR] 未找到 suzhen-images.tar（系统镜像文件）
    echo   请确保此文件与 setup.bat 在同一目录下。
    echo.
    pause
    exit /b 1
)

if not exist "docker-compose.yaml" (
    echo   [ERROR] 未找到 docker-compose.yaml
    echo   请确保此文件与 setup.bat 在同一目录下。
    echo.
    pause
    exit /b 1
)

pause

:: ============================================================
:: Step 1: Check Docker
:: ============================================================
:check_docker
cls
echo.
echo  ======================================================================
echo   步骤 1/3: 检测 Docker 环境
echo  ======================================================================
echo.

docker --version >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Docker 已安装
    docker --version
    echo.
    goto :import_images
)

echo   [WARN] 未检测到 Docker
echo.
echo   本系统需要 Docker Desktop 才能运行。
echo   即将为您打开 Docker Desktop 下载页面...
echo.
echo   请下载并安装 Docker Desktop，安装完成后重启电脑，再运行此脚本。
echo.
echo   Docker Desktop 下载地址：
echo   https://www.docker.com/products/docker-desktop
echo.
set /p OPEN="   是否现在打开下载页面？(Y/N，默认 Y): "
if /i "!OPEN!"=="" set OPEN=Y
if /i "!OPEN!"=="Y" start "" "https://www.docker.com/products/docker-desktop"

echo.
echo  ============================================
echo   安装 Docker Desktop 注意事项：
echo   - 安装过程中使用默认选项即可
echo   - 安装完成后需要重启电脑
echo   - 重启后 Docker Desktop 会自动启动（任务栏右下角出现鲸鱼图标）
echo  ============================================
echo.
echo   完成安装并重启后，请重新运行此脚本。
echo.
pause
exit /b 1

:: ============================================================
:: Step 2: Import images
:: ============================================================
:import_images
cls
echo.
echo  ======================================================================
echo   步骤 2/3: 导入系统镜像
echo  ======================================================================
echo.
echo   正在导入系统镜像，请稍候...
echo.

docker load -i suzhen-images.tar
if errorlevel 1 (
    echo.
    echo   [ERROR] 镜像导入失败！
    echo   请检查 suzhen-images.tar 文件是否完整。
    pause
    exit /b 1
)

echo.
echo   [OK] 镜像导入完成
echo.
pause

:: ============================================================
:: Step 3: Start services
:: ============================================================
:start_services
cls
echo.
echo  ======================================================================
echo   步骤 3/3: 启动服务
echo  ======================================================================
echo.

set /p PORT="   请输入服务端口（默认 8080，直接回车）: "
if "!PORT!"=="" set PORT=8080

echo.
echo   正在启动服务...

:: 停止旧容器
docker compose -f docker-compose.yaml down 2>nul
if errorlevel 1 docker-compose -f docker-compose.yaml down 2>nul

:: 写入 .env 文件
echo APP_PORT=!PORT!> .env

:: 启动服务
docker compose -f docker-compose.yaml up -d
if errorlevel 1 (
    docker-compose -f docker-compose.yaml up -d
    if errorlevel 1 (
        echo.
        echo   [ERROR] 启动失败！常见原因：
        echo     1. 端口 !PORT! 被占用 - 请重新运行并换一个端口
        echo     2. Docker Desktop 未完全启动 - 等待鲸鱼图标稳定后再试
        echo.
        pause
        exit /b 1
    )
)

:: 等待后端就绪
echo.
echo   等待服务就绪...
timeout /t 5 >nul

:: ============================================================
:: Done
:: ============================================================
:done
cls
echo.
echo  ======================================================================
echo  ║                                                                      ║
echo  ║                     启动成功！                                      ║
echo  ║                                                                      ║
echo  ======================================================================
echo.
echo    服务访问地址：
echo.
echo        http://localhost:!PORT!
echo.
echo  ======================================================================
echo    首次登录凭据
echo  ======================================================================
echo.
echo       用户名:   admin
echo       密码:     admin!
echo.
echo    首次登录后请立即修改密码！
echo.
echo  ======================================================================
echo    常用操作
echo  ======================================================================
echo.
echo       停止服务:   双击 stop.bat
echo       重启服务:   先双击 stop.bat，再双击 setup.bat
echo.
echo  ======================================================================
echo.
echo   按任意键打开浏览器访问系统...
pause >nul
start "" "http://localhost:!PORT!"
exit /b 0
