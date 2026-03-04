@echo off
chcp 65001 >nul
echo ========================================
echo   用户行为分析平台 - 启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [完成] Python 环境正常

echo.
echo [2/3] 检查依赖包...
python -c "import streamlit, pandas, plotly, sklearn, networkx" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt
)
echo [完成] 依赖包已就绪

echo.
echo [3/3] 启动 Streamlit 应用...
echo.
echo ========================================
echo   应用将在浏览器中自动打开
echo   地址：http://localhost:8501
echo   按 Ctrl+C 停止应用
echo ========================================
echo.

streamlit run dashboard.py

pause
