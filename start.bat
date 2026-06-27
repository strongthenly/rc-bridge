@echo off
chcp 65001 >nul
title RC Bridge - ViGEmBus 版
color 0A

echo =============================================
echo  RC Bridge - ViGEmBus 版
echo  虚拟 Xbox 手柄桥接程序
echo =============================================
echo.

:: 检查 ViGEmBus 驱动
sc query ViGEmBus >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] ViGEmBus 驱动未安装！
    echo.
    echo   虚拟手柄需要 ViGEmBus 驱动才能工作。
    echo   请以管理员身份运行安装程序：
    echo.
    echo   cd pc-receiver-vigem
    echo   python -c "import vgamepad; vgamepad.install()"
    echo.
    echo 或者手动安装：
    echo   下载 https://github.com/nefarius/ViGEmBus/releases
    echo.
    pause
    exit /b 1
) else (
    echo [OK] ViGEmBus 驱动已安装
)

echo [OK] 启动桥接程序...
echo.
:: 优先尝试同目录下的 exe，没有则回退到 Python 脚本
set EXE_PATH=%~dp0dist\rc-bridge-vigem.exe
set SCRIPT_PATH=%~dp0pc-receiver-vigem\rc_bridge_vigem.py

if exist "%EXE_PATH%" (
    "%EXE_PATH%"
) else if exist "%SCRIPT_PATH%" (
    python "%SCRIPT_PATH%"
) else (
    echo [错误] 找不到可执行文件和 Python 脚本
    pause
    exit /b 1
)

pause
