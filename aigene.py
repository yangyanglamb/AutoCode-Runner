import os
import re
import sys
import time
import ast  # 添加ast导入
import subprocess
import importlib.util
import platform
import venv
from pathlib import Path
from datetime import datetime
from threading import Thread, Event
from dotenv import load_dotenv
import openai
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console
from rich.panel import Panel

# 环境配置
PYTHON_MIN_VERSION = (3, 7)  # 保持原来的最低版本要求
VENV_DIR = "venv3.9"  # 指定Python 3.9的虚拟环境目录
REQUIREMENTS_FILE = "requirements.txt"  # 依赖文件

# 根据操作系统动态设置Python命令
if sys.platform == "win32":
    PYTHON39_PATH = "py -3.9"  # Windows下的Python 3.9启动器命令
else:
    PYTHON39_PATH = "python3.9"  # Unix系统下的Python 3.9命令

# 先加载环境变量！！！
load_dotenv()

# 初始化Rich控制台
console = Console()

try:
    # 获取API密钥
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("未找到API密钥")
        
    # 初始化 DeepSeek 客户端
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )
except ValueError as e:
    console.print(f"\n[red]❌ {str(e)}[/red]")
    console.print("[yellow]请在.env文件中添加正确的API key，格式如下：[/yellow]")
    console.print("[blue]DEEPSEEK_API_KEY=your_api_key_here[/blue]")
    sys.exit(1)
except (openai.AuthenticationError, TypeError) as e:
    console.print("\n[red]❌ API key(密钥)无效,请检查您的API key是否正确[/red]")
    console.print("\n[red]❌ to开发人员，也可能是|解释器|环境|依赖版本|问题[/red]")
    console.print("\n[yellow]当前API key值：[/yellow]")
    console.print(f"[blue]{api_key}[/blue]")
    console.print("\n[yellow]原始错误信息：[/yellow]")
    console.print(f"[red]{type(e).__name__}: {str(e)}[/red]")

    sys.exit(1)
except Exception as e:
    console.print(f"\n[red]❌ 初始化客户端时发生错误: {type(e).__name__}[/red]")
    console.print(f"[yellow]原始错误信息：[/yellow]")
    console.print(f"[red]{str(e)}[/red]")
    sys.exit(1)

# 常见标准库列表
STANDARD_LIBS = {
    'os', 'sys', 're', 'time', 'datetime', 'random', 'json',
    'math', 'collections', 'subprocess', 'importlib', 'argparse',
    'threading', 'multiprocessing', 'logging', 'unittest', 'csv',
    'sqlite3', 'xml', 'html', 'http', 'urllib', 'socket', 'email',
    'calendar', 'configparser', 'copy', 'enum', 'functools', 'hashlib',
    'itertools', 'pathlib', 'pickle', 'queue', 'shutil', 'statistics',
    'tempfile', 'typing', 'uuid', 'warnings', 'weakref', 'zipfile',
    'platform', 'string', 'struct', 'textwrap', 'tkinter', 'venv',
    'wave', 'webbrowser', 'xml.etree.ElementTree', 'zlib', 'ctypes'
}

class ProgressManager:
    """进度管理器"""
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="green"),
            TaskProgressColumn(),
            console=console
        )
    
    def __enter__(self):
        return self.progress.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.progress.__exit__(exc_type, exc_val, exc_tb)

class StreamPrinter:
    """流式输出处理器"""
    def __init__(self):
        self.buffer = []
        self.is_first_chunk = True
        self.print_lock = Event()
        self.print_lock.set()
        self.last_chunk_ended_with_newline = False

    def stream_print(self, content):
        """优化后的流式输出逻辑"""
        if not content:
            return
            
        self.buffer.append(content)
        if self.print_lock.is_set():
            self.print_lock.clear()
            
            # 首次输出时添加前缀
            if self.is_first_chunk:
                console.print("\n[cyan]DeepSeek:[/cyan] ", end="")
                self.is_first_chunk = False
            
            while self.buffer:
                chunk = self.buffer.pop(0)
                # 处理换行
                lines = chunk.split('\n')
                for i, line in enumerate(lines):
                    if i > 0:  # 不是第一行时添加缩进
                        console.print()
                        console.print("[cyan]          [/cyan]", end="")
                    console.print(line, end="", highlight=False)
                
                # 记录是否以换行结束
                self.last_chunk_ended_with_newline = chunk.endswith('\n')
            
            self.print_lock.set()

    def reset(self):
        """重置状态"""
        self.is_first_chunk = True
        # 如果最后一个chunk没有换行，确保添加换行
        if not self.last_chunk_ended_with_newline:
            console.print()
        self.last_chunk_ended_with_newline = False

def extract_code_from_response(response):
    """代码提取函数（必须定义）"""
    # 提取文件名（如果有）
    filename_match = re.search(r'『(.+?)』\.py', response)
    suggested_filename = filename_match.group(1) if filename_match else None
    
    # 提取代码块（严格格式要求）
    code_blocks = re.findall(
        r'```\s*\n'  # 开始三引号
        r'『[\w\s-]+』\.py\n'  # 文件名声明
        r'((?:#[^\n]*\n)*\n.*?)'  # 捕获所有代码内容，包括依赖声明
        r'```',  # 结束三引号
        response,
        flags=re.DOTALL
    )
    
    if not code_blocks:
        # 如果严格格式匹配失败，尝试宽松匹配
        code_blocks = re.findall(
            r'```\s*\n?(.*?)\n?\s*```', 
            response, 
            flags=re.DOTALL
        )
    
    if not code_blocks:
        return None, None
        
    return code_blocks[0].strip(), suggested_filename

def extract_imports(code_content):
    """使用AST解析器从代码中提取依赖，并从注释中提取版本信息"""
    imports = set()
    try:
        # 从新格式的注释中提取依赖
        # 匹配 "依赖包：xxx" 或 "依赖包:xxx" 格式
        dep_pattern = r'#\s*依赖包[：:]\s*([^（\n]+)'
        # 匹配 "pip install xxx" 格式
        pip_pattern = r'#\s*pip\s+install\s+([^\n]+)'
        
        # 提取依赖包
        dep_matches = re.findall(dep_pattern, code_content)
        if dep_matches:
            for deps in dep_matches:
                if deps.strip().lower() != "无":
                    # 处理可能的多个依赖（用逗号分隔）
                    for dep in deps.split(','):
                        dep = dep.strip()
                        if dep and dep not in STANDARD_LIBS:
                            imports.add(dep)
        
        # 提取pip install行
        pip_matches = re.findall(pip_pattern, code_content)
        if pip_matches:
            for deps in pip_matches:
                if deps.strip().lower() != "无":
                    # 处理可能的多个依赖（用空格分隔）
                    for dep in deps.split():
                        dep = dep.strip()
                        if dep and dep not in STANDARD_LIBS:
                            imports.add(dep)

        # 从导入语句中提取依赖
        tree = ast.parse(code_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    lib = alias.name.split('.')[0]
                    # 特殊处理 python-dotenv
                    if lib == 'dotenv':
                        if 'python-dotenv' not in {i.split('==')[0] for i in imports}:
                            imports.add('python-dotenv')
                    elif lib not in STANDARD_LIBS:
                        # 如果在注释中没有指定版本，则只添加包名
                        if lib not in {i.split('==')[0] for i in imports}:
                            imports.add(lib)
            elif isinstance(node, ast.ImportFrom):
                lib = node.module.split('.')[0] if node.module else ''
                # 特殊处理 python-dotenv
                if lib == 'dotenv':
                    if 'python-dotenv' not in {i.split('==')[0] for i in imports}:
                        imports.add('python-dotenv')
                elif lib and lib not in STANDARD_LIBS:
                    # 如果在注释中没有指定版本，则只添加包名
                    if lib not in {i.split('==')[0] for i in imports}:
                        imports.add(lib)
    except SyntaxError:
        console.print("\n[red]⚠️ 代码解析错误，无法提取依赖[/red]")
    
    # 调试输出
    if imports:
        console.print("\n[yellow]检测到的依赖：[/yellow]")
        for dep in imports:
            console.print(f"[blue]- {dep}[/blue]")
    
    return imports

def is_installed(lib_name):
    """检查库是否已安装"""
    try:
        # 如果是标准库，直接返回 True
        if lib_name in STANDARD_LIBS:
            return True
            
        # 处理带版本号的包名
        package_name = lib_name.split('==')[0] if '==' in lib_name else lib_name
        
        # 获取虚拟环境Python解释器路径
        python_path = setup_virtual_env()
        # 使用虚拟环境的Python检查包是否已安装
        result = subprocess.run(
            [python_path, "-c", f"import {package_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def check_python_version():
    """检查Python版本是否满足要求"""
    current_version = sys.version_info[:2]
    if current_version < PYTHON_MIN_VERSION:
        raise RuntimeError(
            f"Python版本过低。需要Python {'.'.join(map(str, PYTHON_MIN_VERSION))} 或更高版本"
        )

def setup_virtual_env():
    """设置Python 3.9虚拟环境"""
    venv_path = Path(VENV_DIR).absolute()
    if not venv_path.exists():
        console.print("[yellow]正在创建Python 3.9虚拟环境...[/yellow]")
        try:
            # 检查Python 3.9是否可用
            version_check = subprocess.run(
                [PYTHON39_PATH.split()[0], PYTHON39_PATH.split()[1] if len(PYTHON39_PATH.split()) > 1 else "--version"],
                capture_output=True,
                text=True
            )
            if version_check.returncode != 0:
                raise RuntimeError("未找到Python 3.9，请确保已安装并添加到系统路径")
            
            # 使用Python 3.9创建虚拟环境
            subprocess.run([PYTHON39_PATH.split()[0], "-m", "venv", str(venv_path)], check=True)
            console.print("[green]✓ 成功创建Python 3.9虚拟环境[/green]")
            
            # 升级pip
            python_path = get_venv_python_path(venv_path)
            subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
            
        except subprocess.CalledProcessError:
            console.print("[red]创建虚拟环境失败，请确保已正确安装Python 3.9[/red]")
            raise
        except FileNotFoundError:
            console.print("[red]未找到Python 3.9，请确保已安装并添加到系统路径[/red]")
            raise
    
    return get_venv_python_path(venv_path)

def get_venv_python_path(venv_path):
    """获取虚拟环境中的Python解释器路径"""
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"
    return str(python_path)

def generate_requirements():
    """生成requirements.txt文件"""
    required_packages = {
        "openai": "1.0.0",
        "python-dotenv": "1.0.0",
        "rich": "13.0.0",
        "colorama": "0.4.6"
    }
    
    with open(REQUIREMENTS_FILE, "w") as f:
        for package, version in required_packages.items():
            f.write(f"{package}=={version}\n")

def install_dependencies(required_libs):
    """安装依赖"""
    if not required_libs:
        return True

    # 确保虚拟环境存在
    python_path = setup_virtual_env()
    
    failed_libs = []
    mirrors = [
        "https://mirrors.aliyun.com/pypi/simple/",  # 阿里云（优先）
        "https://pypi.org/simple/",  # PyPI官方源（第二）
    ]
    
    with ProgressManager() as progress:
        install_task = progress.add_task("[yellow]正在安装依赖...[/yellow]", total=len(required_libs))
        
        for lib in required_libs:
            installed = False
            for mirror in mirrors:
                try:
                    # 使用虚拟环境的pip安装
                    cmd = [python_path, "-m", "pip", "install", lib, "--quiet"]
                    if mirror:
                        cmd.extend(["-i", mirror])
                        console.print(f"[yellow]尝试使用下载源: {mirror}[/yellow]")
                    
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=300  # 5分钟超时
                    )
                    
                    if result.returncode == 0:
                        # 显示不带版本号的包名
                        lib_name = lib.split('==')[0] if '==' in lib else lib
                        console.print(f"[green]✅ {lib_name}[/green]")
                        installed = True
                        break
                        
                except subprocess.TimeoutExpired:
                    continue
                except Exception as e:
                    continue
            
            if not installed:
                failed_libs.append(lib)
            
            progress.update(install_task, advance=1)
    
    if failed_libs:
        console.print(f"\n[red]以下依赖安装失败: {', '.join(failed_libs)},若开启了VPN，请关闭VPN后重试[/red]")
        return False
                
    return True

def save_and_execute_code(code_content, execute=True):
    """保存并执行代码"""
    try:
        # 创建代码保存目录
        code_dir = "代码工具库"
        if not os.path.exists(code_dir):
            os.makedirs(code_dir)

        # 分离代码内容和文件名
        if isinstance(code_content, tuple):
            code_content, suggested_filename = code_content
        else:
            suggested_filename = None

        # 先生成文件
        if suggested_filename:
            if not suggested_filename.endswith('.py'):
                suggested_filename += '.py'
            filename = os.path.join(code_dir, suggested_filename)
        else:
            filename = os.path.join(code_dir, f"generated_{datetime.now().strftime('%Y%m%d%H%M%S')}.py")
            
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code_content)
            
        abs_path = os.path.abspath(filename)
        # 获取文件所在目录路径
        dir_path = os.path.dirname(abs_path)
        
        # 打印保存路径
        console.print(f"\n[blue]💾 代码保存路径: [cyan]{abs_path}[/cyan][/blue]")
        
        # 直接打开文件夹
        try:
            if sys.platform == "win32":
                os.startfile(dir_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.run(['open', dir_path])
            else:  # Linux
                subprocess.run(['xdg-open', dir_path])
        except Exception as e:
            console.print(f"[yellow]⚠️ 无法自动打开文件夹: {str(e)}[/yellow]")

        if not execute:
            return True

        # 再检测和安装依赖
        required_libs = [
            lib for lib in extract_imports(code_content)
            if not is_installed(lib)
        ]
        
        if required_libs and not install_dependencies(required_libs):
            console.print("\n[red]⚠️ 部分依赖安装失败,代码可能无法正常运行[/red]")
            return False

        # 获取虚拟环境Python解释器
        python_path = setup_virtual_env()
        
        # 执行代码 - 使用新的控制台窗口
        console.print("\n[yellow]🚀 正在新窗口中启动程序(Python 3.9)...[/yellow]")
        try:
            if sys.platform == "win32":
                # Windows下使用相对路径执行Python文件
                venv_python = os.path.join("venv3.9", "Scripts", "python.exe")
                if not os.path.exists(venv_python):
                    console.print(f"\n[red]⚠️ 虚拟环境Python解释器不存在: {venv_python}[/red]")
                    return False
                
                # 使用相对路径构建命令
                rel_python = os.path.relpath(venv_python)
                rel_filename = os.path.relpath(filename)
                cmd = f'start cmd /c "{rel_python} {rel_filename} & pause"'
                subprocess.Popen(cmd, shell=True)
            else:
                if sys.platform == "darwin":  # macOS
                    subprocess.Popen(['open', '-a', 'Terminal', '--', python_path, filename])
                else:  # Linux
                    terminals = ['gnome-terminal', 'xterm', 'konsole']
                    for term in terminals:
                        try:
                            subprocess.Popen([term, '--', python_path, filename])
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        # 如果没有找到图形终端，使用当前终端运行
                        subprocess.Popen([python_path, filename])
        except Exception as e:
            console.print(f"\n[red]⚠️ 启动程序失败: {str(e)}[/red]")
            return False

        return True
    except Exception as e:
        console.print(f"\n[red]⚠️ 异常: {str(e)}[/red]")
        return False

def chat_stream(messages, printer, model="deepseek-chat"):
    """流式对话处理"""
    full_response = []
    reasoning_content = []
    is_reasoning = False  # 标记是否正在输出思维链
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 直接创建聊天完成并流式输出
            for chunk in client.chat.completions.create(
                model=model,  # 使用指定的模型
                messages=messages,
                temperature=0.7,
                stream=True,
                timeout=30  # 添加超时设置
            ):
                # 处理思维链内容
                if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                    content = chunk.choices[0].delta.reasoning_content
                    reasoning_content.append(content)
                    
                    # 如果是思维链的开始，打印前缀
                    if not is_reasoning:
                        console.print("\n[bright_blue]（思考中）[/bright_blue] ", end="")
                        is_reasoning = True
                        
                    # 直接打印思维链内容，使用默认颜色
                    console.print(content, end="")
                    
                # 处理最终回答内容
                elif chunk.choices[0].delta.content:
                    # 如果之前在输出思维链，添加结束标记和换行
                    if is_reasoning:
                        console.print("\n[bright_blue]\n（思考结束）[/bright_blue]")
                        is_reasoning = False
                        
                    content = chunk.choices[0].delta.content
                    full_response.append(content)
                    printer.stream_print(content)
                
            # 如果成功完成，跳出重试循环
            break
                
        except openai.AuthenticationError:
            console.print("\n[red]❌ 认证失败，请检查 DEEPSEEK_API_KEY 是否正确[/red]")
            return {"reasoning_content": "", "content": ""}
            
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            retry_count += 1
            console.print(f"\n[red]❌ 连接错误详情：[/red]")
            console.print(f"[yellow]错误类型：{type(e).__name__}[/yellow]")
            console.print(f"[yellow]错误信息：{str(e)}[/yellow]")
            console.print(f"[yellow]错误详情：{repr(e)}[/yellow]")
            
            # 根据错误类型提供具体建议
            if isinstance(e, openai.APIConnectionError):
                console.print("\n[yellow]可能原因：[/yellow]")
                console.print("1. 网络连接不稳定或断开")
                console.print("2. DNS解析失败")
                console.print("3. 服务器响应超时")
                console.print("4. 代理配置不正确")
                console.print("\n[yellow]建议解决方案：[/yellow]")
                console.print("1. 检查网络连接是否正常")
                console.print("2. 如果使用VPN，请关闭VPN后重试")
            elif isinstance(e, openai.APITimeoutError):
                console.print("\n[yellow]可能原因：[/yellow]")
                console.print("1. 服务器处理请求时间过长")
                console.print("2. 网络延迟较高")
                console.print("3. 系统资源不足")
                console.print("\n[yellow]建议解决方案：[/yellow]")
                console.print("1. 检查网络速度是否正常")
                console.print("2. 尝试减小请求的数据量")
                console.print("3. 关闭其他占用带宽的程序")
                console.print("4. 稍后重试")
            
            if retry_count < max_retries:
                wait_time = 2 ** retry_count  # 指数退避
                console.print(f"\n[yellow]⚠️ 连接失败，{wait_time}秒后进行第{retry_count + 1}次重试...[/yellow]")
                time.sleep(wait_time)
            else:
                console.print("\n[red]❌ 连接失败，请检查网络连接或稍后重试[/red]")
                console.print("[yellow]建议：[/yellow]")
                console.print("1. 检查网络连接是否正常")
                console.print("2. 确认是否可以访问 api.deepseek.com")
                console.print("3. 如果使用了代理，请检查代理设置")
                console.print("4. 尝试重启程序")
                console.print("5. 确认API密钥额度是否充足")
                console.print("6. 检查系统时间是否准确")
                return {"reasoning_content": "", "content": ""}
                
        except Exception as e:
            console.print(f"\n[red]❌ 发生未知错误[/red]")
            console.print(f"[yellow]错误类型：{type(e).__name__}[/yellow]")
            console.print(f"[yellow]错误信息：{str(e)}[/yellow]")
            console.print(f"[yellow]错误详情：{repr(e)}[/yellow]")
            return {"reasoning_content": "", "content": ""}
    
    # 确保思维链在最后也能正确结束
    if is_reasoning:
        console.print("\n[bright_blue]（思考结束）[/bright_blue]\n")
        
    return {
        "reasoning_content": "".join(reasoning_content),
        "content": "".join(full_response)
    }

def get_multiline_input():
    """
    智能获取用户输入：
    1) 当输入小于25字时，直接回车即可发送
    2) 当输入大于等于25字时：
       - 用户输入任意文本并按回车
       - 如果下一个输入是空行(立即按回车)，则视为结束
       - 如果下一个输入不是空行，则视为多行输入，直到出现一次空行(按回车)即结束
    """
    console.print(
        "\n[bold green]用户:[/bold green] ", end=""
    )

    lines = []
    try:
        # 第一次输入
        first_line = input()
        if not first_line.strip():
            # 如果刚开始就直接回车，返回空
            return ""

        # 将第一行加入
        lines.append(first_line)
        
        # 如果第一行小于25字，直接返回
        if len(first_line.strip()) < 25:
            return first_line

        # 尝试读取下一行
        while True:
            line = input()
            # 如果遇到空行，则结束输入
            if not line.strip():
                break
            lines.append(line)
    except EOFError:
        # 用户可能触发了 Ctrl+Z / Ctrl+D
        pass
    except KeyboardInterrupt:
        # 处理 Ctrl+C
        return ""

    return "\n".join(lines)

def main():
    try:
        # 环境检查
        check_python_version()
        
        # 生成requirements.txt
        if not os.path.exists(REQUIREMENTS_FILE):
            generate_requirements()
        
        # 设置虚拟环境
        setup_virtual_env()
        
        printer = StreamPrinter()
        current_model = "deepseek-chat"  # 默认模型
        messages = [{
            "role": "system",
            "content": """你是一个Python专家。在生成代码时，请遵循以下规则：

## 基础结构
1. 代码块格式（必须严格遵守）
- 代码块内容必须按以下格式编写：
文件名：『中文命名』.py  需要用『』包裹
```
# 依赖包：xxx
# 前置预装依赖包：xxx
# pip install xxx
# 是否需要处理中文字符：是

import os
import sys

# 在导入其他包之前，确保使用正确的Python环境
def ensure_correct_python():
    #确保使用正确的Python环境
    current_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = os.path.join(os.path.dirname(current_dir), "venv3.9", "Scripts", "python.exe")
    
    if os.path.exists(python_path) and sys.executable.lower() != python_path.lower():
        print(f"正在切换到正确的Python环境...")
        os.execv(python_path, [python_path] + sys.argv)

# 先执行环境切换
if __name__ == "__main__":
    ensure_correct_python()

# 在确保环境正确后，再导入其他包
import glob
from datetime import datetime

其余代码内容
```

2. 代码规范
- 生成的代码固定声明PYTHON39_PATH = "../venv3.9/Scripts/python.exe"

## 编码规范
- 强制使用UTF-8编码
- 核心逻辑必须添加中文注释
- 文件处理需要支持中文
- 使用f-string格式输出日志

## 安全规范
- 通过.env加载敏感信息
- 使用项目专属变量名（如：MYAPP_OPENAI_KEY）
- 禁用明文存储API密钥

## 运行保障
- 必须包含try-except异常捕获
- 错误日志前缀使用❌符号
- 文件操作自动处理路径拼接

## 交互规范
├─ 用户输入特定文件地址时，直接写入程序中而不启用文件选择器
├─ 涉及非特定文件选择时，集成tkinter文件选择器
├─ 使用tkinter时，确保窗口内容显示完全
├─ 添加windll.shcore.SetProcessDpiAwareness(1)
└─ 长操作添加进度提示（time.sleep）

## 环境约束
- 优先选用轻量级依赖包，不需要额外系统依赖
- 复杂需求提示脚本能力边界
- 判断依赖包是否需要前置安装为基础，比如manim需要MiKTeX和FFmpeg为基础，请提醒用户
"""
        }]
    
        
        console.print(Panel.fit(
            "[bold yellow]DeepSeek 智能代码执行助手[/bold yellow]\n[dim]r 切换到 reasoner(深度思考) | c 切换到 chat(一般模式) | -n 仅保存不执行下次代码 | s 保存上次代码 |\nrun 保存并执行上次代码 | 触发词: 写, 代码, 生成 | 多于25字时，按两次回车发送[/dim]",
            border_style="blue"
        ))
        
        while True:
            try:
                user_input = get_multiline_input().strip()
                
                # 忽略空输入
                if not user_input:
                    continue
                # 处理模型切换
                if user_input == "r":
                    current_model = "deepseek-reasoner"
                    console.print(f"\n[cyan]已切换到 [bright_blue]{current_model}[/bright_blue] 模型[/cyan]")
                    continue
                elif user_input == "c":
                    current_model = "deepseek-chat"
                    console.print(f"\n[cyan]已切换到 {current_model} 模型[/cyan]")
                    continue
                
                # 处理保存和执行上次代码的命令
                if user_input == "s" or user_input == "run":
                    # 从消息历史中获取上一次AI的回复
                    if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                        last_response = messages[-1]["content"]
                        code_result = extract_code_from_response(last_response)
                        if code_result and code_result[0]:
                            execute = user_input == "run"  # 如果是run命令则执行，s命令则只保存
                            save_thread = Thread(target=save_and_execute_code, args=(code_result, execute))
                            save_thread.start()
                            save_thread.join()
                            continue
                    console.print("\n[yellow]⚠️ 没有找到上一次生成的代码[/yellow]")
                    continue
                
                # 检查是否包含 -n 标志
                execute_code = "-n" not in user_input
                # 移除 -n 标志，以免影响模型理解
                cleaned_input = user_input.replace("-n", "").strip()
                
                messages.append({"role": "user", "content": cleaned_input})
                
                # 流式对话时使用当前选择的模型
                response = chat_stream(messages, printer, current_model)
                printer.reset()  # 确保在对话结束后重置状态
                messages.append({"role": "assistant", "content": response["content"]})
                
                # 自动代码处理
                if any(kw in cleaned_input for kw in ["写", "代码", "生成"]):
                    code_result = extract_code_from_response(response["content"])
                    if code_result and code_result[0]:
                        # 保存最后生成的代码
                        if execute_code:
                            # 等待代码保存完成
                            save_thread = Thread(target=save_and_execute_code, args=(code_result, execute_code))
                            save_thread.start()
                            save_thread.join()  # 等待线程完成
                    else:
                        console.print("\n[yellow]⚠️ 未检测到有效代码块[/yellow]")
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]🛑 操作已中断[/yellow]")
                break
    except Exception as e:
        console.print(f"\n[red]⚠️ 异常: {str(e)}[/red]")

if __name__ == "__main__":
    main()