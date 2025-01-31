#!/bin/bash
# 设置UTF-8编码
export LANG=zh_CN.UTF-8

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 设置Python脚本路径
SCRIPT_PATH="$SCRIPT_DIR/aigene.py"
REQUIREMENTS_PATH="$SCRIPT_DIR/requirements.txt"

# 显示调试信息
echo "[调试] 当前工作目录: $PWD"
echo "[调试] 脚本路径: $SCRIPT_PATH"
echo "[调试] requirements路径: $REQUIREMENTS_PATH"

# 检查主程序是否存在
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "[错误] 未找到aigene.py主程序"
    echo "[信息] 当前程序路径: $SCRIPT_PATH"
    echo "[提示] 请确保解压完整，且文件名未被更改"
    read -p "按回车键退出..."
    exit 1
fi

# 检查requirements.txt是否存在
if [ ! -f "$REQUIREMENTS_PATH" ]; then
    echo "[错误] 未找到requirements.txt文件"
    echo "[信息] 当前文件路径: $REQUIREMENTS_PATH"
    echo "[提示] 请确保解压完整，且文件名未被更改"
    read -p "按回车键退出..."
    exit 1
fi

# 检查Python 3.9
echo "[检查] Python 3.9版本..."
if ! command -v python3.9 &> /dev/null; then
    echo "[错误] 未找到Python 3.9"
    echo "[提示] 请先安装Python 3.9"
    echo "[提示] Mac用户可使用: brew install python@3.9"
    echo "[提示] Linux用户请参考对应发行版的安装方法"
    read -p "按回车键退出..."
    exit 1
fi

# 设置虚拟环境路径
VENV_DIR="$SCRIPT_DIR/venv3.9"
VENV_PYTHON="$VENV_DIR/bin/python"

echo "[检查] 虚拟环境..."
# 检查虚拟环境是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo "[设置] 首次运行，正在初始化..."
    python3.9 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "[错误] 环境初始化失败"
        echo "[提示] 请检查Python 3.9是否正确安装，以及是否有足够的磁盘空间"
        read -p "按回车键退出..."
        exit 1
    fi
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    
    # 配置pip镜像源
    echo "[设置] 配置pip镜像源..."
    python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    python -m pip config set global.trusted-host mirrors.aliyun.com
    
    # 安装依赖
    echo "[设置] 正在安装必要组件，请确保网络通畅..."
    python -m pip install --upgrade pip --disable-pip-version-check
    python -m pip install -r "$REQUIREMENTS_PATH" --disable-pip-version-check
    if [ $? -ne 0 ]; then
        echo "[错误] 组件安装失败"
        echo "[提示] 请检查网络连接，或尝试关闭代理/VPN"
        cd "$SCRIPT_DIR"
        read -p "按回车键退出..."
        exit 1
    fi
    cd "$SCRIPT_DIR"
    clear
    echo
    echo "================================================"
    echo "                初始化完成！"
    echo "================================================"
    echo
    sleep 2
    clear
else
    source "$VENV_DIR/bin/activate"
fi

# 检查openai包
echo "[检查] 依赖包..."
if ! python -c "import openai" &> /dev/null; then
    echo "[设置] 更新必要组件..."
    python -m pip install -r "$REQUIREMENTS_PATH" --disable-pip-version-check
    if [ $? -ne 0 ]; then
        echo "[错误] 组件更新失败"
        echo "[提示] 请检查网络连接，或尝试关闭代理/VPN"
        read -p "按回车键退出..."
        exit 1
    fi
    sleep 1
    clear
fi

# 检查.env文件
echo "[检查] 配置文件..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[错误] 未找到.env文件"
        echo "[提示] 请复制.env.example为.env并设置正确的API密钥"
        echo "[信息] 当前目录: $PWD"
        read -p "按回车键退出..."
        exit 1
    else
        echo "[错误] 未找到.env和.env.example文件"
        echo "[提示] 请确保.env文件存在并包含正确的API密钥"
        echo "[信息] 当前目录: $PWD"
        read -p "按回车键退出..."
        exit 1
    fi
fi

# 检查.env文件内容
if ! grep -q "DEEPSEEK_API_KEY" ".env"; then
    echo "[错误] .env文件中未找到DEEPSEEK_API_KEY配置"
    echo "[提示] 请在.env文件中添加正确的API密钥"
    echo "[示例] DEEPSEEK_API_KEY=your_api_key_here"
    echo "[信息] 当前.env文件路径: $PWD/.env"
    read -p "按回车键退出..."
    exit 1
fi

# 清屏并运行主程序
clear
echo "[启动] 正在启动程序..."
sleep 1
clear
python "$SCRIPT_PATH"

# 如果发生错误则显示详细信息
if [ $? -ne 0 ]; then
    echo
    echo "[错误] 程序执行出错"
    echo "[信息] 错误代码: $?"
    echo "[提示] 请检查以上错误信息，或重新运行程序"
    read -p "按回车键退出..."
    exit 1
fi

# 程序正常结束也暂停
echo
echo "程序已结束，按回车键退出..."
read 