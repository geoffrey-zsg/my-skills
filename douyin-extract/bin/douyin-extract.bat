@echo off
REM 抖音文案提取 Skill 入口 (Windows)
REM 用法: douyin-extract <链接>

setlocal enabledelayedexpansion

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM 切换到项目目录
cd /d "%PROJECT_DIR%"

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请安装 Python 3.10+
    exit /b 1
)

REM 执行提取
python skill_extract.py %*
