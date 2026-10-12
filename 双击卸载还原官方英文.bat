@echo off
chcp 65001 >nul
title Antigravity 2.0 卸载汉化与还原工具

echo ========================================================
echo        Antigravity 2.0 卸载汉化（恢复官方英文原版）
echo ========================================================
echo.
echo [1/2] 正在卸载汉化并恢复官方原版文件...
where python >nul 2>nul
if %errorlevel% equ 0 (
    python "%~dp0localization_engine.py" --huifu %*
) else (
    node "%~dp0localization_engine.js" --huifu %*
)

if %errorlevel% neq 0 (
    echo.
    echo [×] 还原失败，请检查上方错误信息。
    pause
    exit /b 1
)

echo.
echo [2/2] 已无痕恢复为官方英文原版！Antigravity 2.0 正在重新启动...
echo.
echo 窗口将在 5 秒后自动关闭...
timeout /t 5
