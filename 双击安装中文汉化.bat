@echo off
chcp 65001 >nul
title Antigravity 2.0 中文汉化一键安装工具

echo ========================================================
echo        Antigravity 2.0 中文汉化一键安装工具
echo ========================================================
echo.
echo 请选择左上角品牌显示方式：
echo   [1] 保持英文 Antigravity（默认推荐）
echo   [2] 隐藏左上角品牌名
echo   [3] 显示中文品牌名（反重力）
echo.
set "CHOICE_VAL=1"
set /p "CHOICE_VAL=请输入选项 [1/2/3] (直接按回车默认为 1): "
set "BRAND_ARG=--brand-title english"
if "%CHOICE_VAL%"=="2" set "BRAND_ARG=--brand-title hidden"
if "%CHOICE_VAL%"=="3" set "BRAND_ARG=--brand-title translated"

echo.
echo [1/2] 正在注入 Antigravity 2.0 中文汉化并自动重启客户端...
where python >nul 2>nul
if %errorlevel% equ 0 (
    python "%~dp0localization_engine.py" %BRAND_ARG% %*
) else (
    node "%~dp0localization_engine.js" %BRAND_ARG% %*
)

if %errorlevel% neq 0 (
    echo.
    echo [×] 汉化注入失败，请检查上方错误信息。
    pause
    exit /b 1
)

echo.
echo [2/2] 汉化安装完成！Antigravity 2.0 正在自动重新启动...
echo.
echo 窗口将在 5 秒后自动关闭...
timeout /t 5
