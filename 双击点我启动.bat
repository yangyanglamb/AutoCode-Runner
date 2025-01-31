@echo off
chcp 65001 > nul
title DeepSeek智能代码助手

:: 获取当前脚本所在目录的绝对路径
set "SCRIPT_DIR=%~dp0"
:: 移除路径末尾的反斜杠
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: 切换到脚本所在目录
cd /d "%SCRIPT_DIR%"

:: 设置Python脚本路径
set "SCRIPT_PATH=%SCRIPT_DIR%\aigene.py"
set "REQUIREMENTS_PATH=%SCRIPT_DIR%\requirements.txt"

:: 检查主程序是否存在
if not exist "%SCRIPT_PATH%" (
    echo [错误] 未找到aigene.py主程序
    echo [信息] 当前程序路径: %SCRIPT_PATH%
    pause
    exit /b 1
)

:: 检查是否安装了Python 3.9
py -3.9 --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python 3.9，请确保已安装Python 3.9
    pause
    exit /b 1
)

:: 设置虚拟环境路径
set "VENV_DIR=%SCRIPT_DIR%\venv3.9"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

:: 检查虚拟环境是否有效（静默）
if not exist "%VENV_DIR%" (
    echo [设置] 首次运行，正在初始化...
    py -3.9 -m venv "%VENV_DIR%" >nul 2>&1
    if errorlevel 1 (
        echo [错误] 环境初始化失败
        pause
        exit /b 1
    )
    cd /d "%VENV_DIR%\Scripts"
    :: 配置pip镜像源（静默）
    python.exe -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ >nul 2>&1
    python.exe -m pip config set global.trusted-host mirrors.aliyun.com >nul 2>&1
    :: 安装依赖（显示进度）
    echo [设置] 正在安装必要组件，请确保网络通畅...
    python.exe -m pip install --upgrade pip --disable-pip-version-check >nul 2>&1
    python.exe -m pip install -r "%REQUIREMENTS_PATH%" --disable-pip-version-check
    if errorlevel 1 (
        echo [错误] 组件安装失败，请检查网络连接
        cd /d "%SCRIPT_DIR%"
        pause
        exit /b 1
    )
    cd /d "%SCRIPT_DIR%"
    cls
    echo.
    echo ================================================
    echo                初始化完成！
    echo ================================================
    echo.
    timeout /t 2 >nul
    cls
)

:: 检查openai包（静默）
"%VENV_PYTHON%" -c "import openai" >nul 2>&1
if errorlevel 1 (
    cd /d "%VENV_DIR%\Scripts"
    echo [设置] 更新必要组件...
    python.exe -m pip install -r "%REQUIREMENTS_PATH%" --disable-pip-version-check
    cd /d "%SCRIPT_DIR%"
    if errorlevel 1 (
        echo [错误] 组件更新失败，请检查网络连接
        pause
        exit /b 1
    )
    timeout /t 1 >nul
    cls
)

:: 检查.env文件
if not exist ".env" (
    if exist ".env.example" (
        echo [错误] 未找到.env文件
        echo [提示] 请复制.env.example为.env并设置正确的API密钥
        pause
        exit /b 1
    ) else (
        echo [错误] 未找到.env和.env.example文件
        echo [提示] 请确保.env文件存在并包含正确的API密钥
        pause
        exit /b 1
    )
)

:: 检查.env文件内容
findstr "DEEPSEEK_API_KEY" ".env" >nul
if errorlevel 1 (
    echo [错误] .env文件中未找到DEEPSEEK_API_KEY配置
    echo [提示] 请在.env文件中添加正确的API密钥
    echo [示例] DEEPSEEK_API_KEY=your_api_key_here
    pause
    exit /b 1
)

:: 清屏并运行主程序
cls
timeout /t 1 >nul
cls
"%VENV_PYTHON%" "%SCRIPT_PATH%"

:: 如果发生错误则暂停
if errorlevel 1 (
    echo [错误] 程序执行出错
    pause
    exit /b 1
)

:: 程序正常结束也暂停
echo.
echo 程序已结束，按任意键退出...
pause>nul 