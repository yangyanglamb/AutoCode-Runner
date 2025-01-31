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

:: 显示当前工作目录和文件路径（调试用）
echo [调试] 当前工作目录: %CD%
echo [调试] 脚本路径: %SCRIPT_PATH%
echo [调试] requirements路径: %REQUIREMENTS_PATH%

:: 检查主程序是否存在
if not exist "%SCRIPT_PATH%" (
    echo [错误] 未找到aigene.py主程序
    echo [信息] 当前程序路径: %SCRIPT_PATH%
    echo [提示] 请确保解压完整，且文件名未被更改
    pause
    exit /b 1
)

:: 检查requirements.txt是否存在
if not exist "%REQUIREMENTS_PATH%" (
    echo [错误] 未找到requirements.txt文件
    echo [信息] 当前文件路径: %REQUIREMENTS_PATH%
    echo [提示] 请确保解压完整，且文件名未被更改
    pause
    exit /b 1
)

:: 检查是否安装了Python 3.9（显示版本信息）
echo [检查] Python 3.9版本...
py -3.9 --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python 3.9
    echo [提示] 请先安装Python 3.9，下载地址：https://www.python.org/downloads/release/python-3913/
    echo [提示] 安装时请勾选"Add Python 3.9 to PATH"选项
    pause
    exit /b 1
)

:: 设置虚拟环境路径
set "VENV_DIR=%SCRIPT_DIR%\venv3.9"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

echo [检查] 虚拟环境...
:: 检查虚拟环境是否有效
if not exist "%VENV_DIR%" (
    echo [设置] 首次运行，正在初始化...
    py -3.9 -m venv "%VENV_DIR%" >nul 2>&1
    if errorlevel 1 (
        echo [错误] 环境初始化失败
        echo [提示] 请检查Python 3.9是否正确安装，以及是否有足够的磁盘空间
        pause
        exit /b 1
    )
    cd /d "%VENV_DIR%\Scripts"
    :: 配置pip镜像源
    echo [设置] 配置pip镜像源...
    python.exe -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ >nul 2>&1
    python.exe -m pip config set global.trusted-host mirrors.aliyun.com >nul 2>&1
    :: 安装依赖
    echo [设置] 正在安装必要组件，请确保网络通畅...
    python.exe -m pip install --upgrade pip --disable-pip-version-check
    python.exe -m pip install -r "%REQUIREMENTS_PATH%" --disable-pip-version-check
    if errorlevel 1 (
        echo [错误] 组件安装失败
        echo [提示] 请检查网络连接，或尝试关闭代理/VPN
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

:: 检查openai包
echo [检查] 依赖包...
"%VENV_PYTHON%" -c "import openai" >nul 2>&1
if errorlevel 1 (
    cd /d "%VENV_DIR%\Scripts"
    echo [设置] 更新必要组件...
    python.exe -m pip install -r "%REQUIREMENTS_PATH%" --disable-pip-version-check
    cd /d "%SCRIPT_DIR%"
    if errorlevel 1 (
        echo [错误] 组件更新失败
        echo [提示] 请检查网络连接，或尝试关闭代理/VPN
        pause
        exit /b 1
    )
    timeout /t 1 >nul
    cls
)

:: 检查.env文件
echo [检查] 配置文件...
if not exist ".env" (
    if exist ".env.example" (
        echo [错误] 未找到.env文件
        echo [提示] 请复制.env.example为.env并设置正确的API密钥
        echo [信息] 当前目录: %CD%
        pause
        exit /b 1
    ) else (
        echo [错误] 未找到.env和.env.example文件
        echo [提示] 请确保.env文件存在并包含正确的API密钥
        echo [信息] 当前目录: %CD%
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
    echo [信息] 当前.env文件路径: %CD%\.env
    pause
    exit /b 1
)

:: 清屏并运行主程序
cls
echo [启动] 正在启动程序...
timeout /t 1 >nul
cls
"%VENV_PYTHON%" "%SCRIPT_PATH%"

:: 如果发生错误则显示详细信息
if errorlevel 1 (
    echo.
    echo [错误] 程序执行出错
    echo [信息] 错误代码: %errorlevel%
    echo [提示] 请检查以上错误信息，或重新运行程序
    pause
    exit /b 1
)

:: 程序正常结束也暂停
echo.
echo 程序已结束，按任意键退出...
pause>nul 