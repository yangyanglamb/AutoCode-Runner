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
import json
import requests  # 添加requests导入
print("更新成功")
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

# 定义客户端类型
DEEPSEEK_CLIENT = 0
QWEN_CLIENT = 1
current_client_type = 0  # 修改这里的值来切换默认客户端: DEEPSEEK_CLIENT(0) 或 QWEN_CLIENT(1)

try:
    # 获取并验证API密钥
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        console.print("\n[red]❌ DEEPSEEK_API_KEY 未在.env文件中设置[/red]")
        console.print("[yellow]请在.env文件中添加正确的API key，格式如下：[/yellow]")
        console.print("[blue]DEEPSEEK_API_KEY=your_api_key_here[/blue]")
        sys.exit(1)
    
    # 初始化 DeepSeek 客户端
    deepseek_client = openai.OpenAI(
        api_key=deepseek_api_key,
        base_url="https://api.deepseek.com/v1"
    )
    
    # 初始化 通义千问 客户端（仅在需要时）
    qwen_api_key = os.getenv("DASHSCOPE_API_KEY")
    if current_client_type == QWEN_CLIENT and not qwen_api_key:
        console.print("\n[red]❌ DASHSCOPE_API_KEY 未在.env文件中设置[/red]")
        console.print("[yellow]请在.env文件中添加正确的API key，格式如下：[/yellow]")
        console.print("[blue]DASHSCOPE_API_KEY=your_api_key_here[/blue]")
        sys.exit(1)
    
    qwen_client = openai.OpenAI(
        api_key=qwen_api_key if qwen_api_key else "dummy_key",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    ) if current_client_type == QWEN_CLIENT else None
    
    # 根据当前客户端类型选择客户端
    client = deepseek_client if current_client_type == DEEPSEEK_CLIENT else qwen_client
    
except ValueError as e:
    if current_client_type == DEEPSEEK_CLIENT:
        console.print(f"\n[red]❌ {str(e)}[/red]")
        console.print("[yellow]请在.env文件中添加正确的API key，格式如下：[/yellow]")
        console.print("[blue]DEEPSEEK_API_KEY=your_api_key_here[/blue]")
        sys.exit(1)
    else:
        console.print(f"\n[red]❌ {str(e)}[/red]")
        console.print("[yellow]请在.env文件中添加正确的API key，格式如下：[/yellow]")
        console.print("[blue]DASHSCOPE_API_KEY=your_api_key_here[/blue]")
        sys.exit(1)
except (openai.AuthenticationError, TypeError) as e:
    console.print("\n[red]❌ API key(密钥)无效,请检查您的API key是否正确")
    console.print("\n[red]❌ to开发人员，也可能是|解释器|环境|依赖版本|问题")
    console.print("\n[yellow]当前API key值：")
    console.print(f"[blue]{deepseek_api_key if current_client_type == DEEPSEEK_CLIENT else os.getenv('DASHSCOPE_API_KEY')}[/blue]")
    console.print("\n[yellow]原始错误信息：")
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
    'wave', 'webbrowser', 'xml.etree.ElementTree', 'zlib', 'ctypes',
    'glob', 'array', 'ast', 'asyncio', 'base64', 'bisect', 'builtins',
    'bz2', 'cgi', 'chunk', 'cmd', 'code', 'codecs', 'codeop', 'colorsys',
    'contextlib', 'dataclasses', 'decimal', 'difflib', 'dis', 'filecmp',
    'fileinput', 'fnmatch', 'fractions', 'ftplib', 'getopt', 'getpass',
    'gettext', 'gzip', 'heapq', 'hmac', 'imaplib', 'imghdr', 'inspect',
    'io', 'ipaddress', 'keyword', 'linecache', 'locale', 'lzma', 'mailbox',
    'mimetypes', 'modulefinder', 'msilib', 'msvcrt', 'netrc', 'nis', 'nntplib',
    'numbers', 'operator', 'optparse', 'os.path', 'pdb', 'pipes', 'poplib',
    'posixpath', 'pprint', 'profile', 'pty', 'pwd', 'py_compile', 'pyclbr',
    'pydoc', 'quopri', 'runpy', 'sched', 'secrets', 'selectors', 'shelve',
    'signal', 'smtpd', 'smtplib', 'sndhdr', 'spwd', 'ssl', 'sunau', 'symbol',
    'symtable', 'sysconfig', 'tabnanny', 'tarfile', 'telnetlib', 'test',
    'timeit', 'token', 'tokenize', 'trace', 'traceback', 'tracemalloc', 'tty',
    'turtle', 'uu', 'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml.dom',
    'xml.parsers', 'xml.sax', 'xmlrpc'
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
                # 根据当前客户端类型选择显示的角色名
                role_name = "千问" if current_client_type == QWEN_CLIENT else "DeepSeek"
                console.print(f"\n[cyan]{role_name}:[/cyan] ", end="")
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
    # 修改正则表达式以更准确地匹配中文文件名
    filename_match = re.search(r'『([\u4e00-\u9fa5a-zA-Z0-9_-]+)』\.py', response)
    suggested_filename = filename_match.group(1) if filename_match else None
    
    # 提取代码块（严格格式要求）
    code_blocks = re.findall(
        r'```(?:python)?\s*\n'  # 开始三引号，可选的python标记
        r'(?:『[\u4e00-\u9fa5a-zA-Z0-9_-]+』\.py\n)?'  # 可选的文件名声明
        r'(.*?)'  # 捕获所有代码内容
        r'```',  # 结束三引号
        response,
        flags=re.DOTALL
    )
    
    if not code_blocks:
        return None, None
        
    # 获取第一个代码块
    code_content = code_blocks[0].strip()
    
    # 确保提取到依赖声明
    if not any(line.startswith('# 依赖包：') for line in code_content.split('\n')):
        console.print("[yellow]警告：未检测到依赖声明，可能会影响依赖安装[/yellow]")
    
    # 如果文件名包含中文，确保系统支持
    if suggested_filename and any('\u4e00' <= c <= '\u9fa5' for c in suggested_filename):
        try:
            # 测试文件名是否可用
            test_path = os.path.join("代码工具库", f"{suggested_filename}.py")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write("")
            os.remove(test_path)
        except OSError:
            # 如果中文文件名出现问题，使用拼音或时间戳
            console.print("[yellow]警告：中文文件名可能不被支持，将使用时间戳命名[/yellow]")
            suggested_filename = f"code_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return code_content, suggested_filename

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

        # 添加包名映射
        package_mapping = {
            'docx': 'python-docx',  # 将 docx 映射到 python-docx
            'dotenv': 'python-dotenv',  # 将 dotenv 映射到 python-dotenv
            # 可以添加其他需要映射的包
        }
        
        # 处理导入语句中的依赖
        tree = ast.parse(code_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    lib = alias.name.split('.')[0]
                    if lib not in STANDARD_LIBS:
                        # 检查是否需要替换包名
                        lib = package_mapping.get(lib, lib)
                        imports.add(lib)
            elif isinstance(node, ast.ImportFrom):
                lib = node.module.split('.')[0] if node.module else ''
                if lib and lib not in STANDARD_LIBS:
                    # 检查是否需要替换包名
                    lib = package_mapping.get(lib, lib)
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
        
        # 使用pip show检查包是否已安装
        result = subprocess.run(
            [python_path, "-m", "pip", "show", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 如果返回码为0，说明包已安装
        if result.returncode == 0:
            # 检查特殊包的依赖是否也已安装
            special_packages = {
                'manim': [
                    'numpy', 'pillow', 'scipy', 'matplotlib', 'tqdm', 'colour', 'pycairo',
                    'cloup', 'click', 'moderngl', 'moderngl_window', 'mapbox-earcut',
                    'networkx', 'decorator'
                ],
                'torch': ['numpy', 'typing-extensions', 'filelock', 'sympy', 'networkx', 'jinja2'],
                'tensorflow': [
                    'numpy', 'six', 'wheel', 'packaging', 'protobuf', 'keras',
                    'h5py', 'wrapt', 'opt-einsum', 'astunparse', 'gast'
                ],
                'opencv-python': ['numpy', 'pillow'],
                'pygame': ['numpy'],
                'kivy': ['docutils', 'pygments', 'kivy_deps.sdl2', 'kivy_deps.glew']
            }
            
            # 如果是特殊包，检查其依赖
            if package_name in special_packages:
                missing_deps = []
                for dep in special_packages[package_name]:
                    dep_result = subprocess.run(
                        [python_path, "-m", "pip", "show", dep],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if dep_result.returncode != 0:
                        console.print(f"[yellow]依赖包 {dep} 未安装[/yellow]")
                        missing_deps.append(dep)
                
                if missing_deps:
                    return False
            
            console.print(f"[green]✓ {package_name} 已安装[/green]")
            return True
            
        return False
        
    except Exception as e:
        console.print(f"[yellow]检查 {lib_name} 安装状态时出错: {str(e)}[/yellow]")
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

def check_special_dependencies(required_libs):
    """检查是否包含需要特殊处理的依赖包"""
    special_deps = {
        'manim': {
            'system_deps': ['MiKTeX', 'FFmpeg'],
            'install_instructions': {
                'MiKTeX': 'https://miktex.org/download',
                'FFmpeg': 'https://ffmpeg.org/download.html'
            }
        },
        'torch': {
            'system_deps': ['CUDA（可选）'],
            'install_instructions': {
                'CUDA': 'https://developer.nvidia.com/cuda-downloads'
            }
        },
        'tensorflow': {
            'system_deps': ['CUDA（可选）', 'cuDNN（可选）'],
            'install_instructions': {
                'CUDA': 'https://developer.nvidia.com/cuda-downloads',
                'cuDNN': 'https://developer.nvidia.com/cudnn'
            }
        },
        'opencv-python': {
            'system_deps': ['Visual C++ Redistributable'],
            'install_instructions': {
                'Visual C++': 'https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist'
            }
        },
        'mysqlclient': {
            'system_deps': ['MySQL', 'Visual C++ Build Tools'],
            'install_instructions': {
                'MySQL': 'https://dev.mysql.com/downloads/installer/',
                'Visual C++ Build Tools': 'https://visualstudio.microsoft.com/visual-cpp-build-tools/'
            }
        },
        'psycopg2': {
            'system_deps': ['PostgreSQL', 'Visual C++ Build Tools'],
            'install_instructions': {
                'PostgreSQL': 'https://www.postgresql.org/download/',
                'Visual C++ Build Tools': 'https://visualstudio.microsoft.com/visual-cpp-build-tools/'
            }
        },
        'pygame': {
            'system_deps': ['SDL', 'Visual C++ Redistributable'],
            'install_instructions': {
                'SDL': 'https://www.libsdl.org/download-2.0.php',
                'Visual C++': 'https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist'
            }
        },
        'kivy': {
            'system_deps': ['Visual C++ Build Tools', 'SDL2', 'GLEW'],
            'install_instructions': {
                'Visual C++ Build Tools': 'https://visualstudio.microsoft.com/visual-cpp-build-tools/',
                'SDL2': 'https://www.libsdl.org/download-2.0.php',
                'GLEW': 'http://glew.sourceforge.net/'
            }
        },
        'pycairo': {
            'system_deps': ['Cairo Graphics'],
            'install_instructions': {
                'Cairo': 'https://www.cairographics.org/download/'
            }
        },
        'python-ldap': {
            'system_deps': ['OpenLDAP', 'Visual C++ Build Tools'],
            'install_instructions': {
                'OpenLDAP': 'https://www.openldap.org/software/download/',
                'Visual C++ Build Tools': 'https://visualstudio.microsoft.com/visual-cpp-build-tools/'
            }
        },
        'pyaudio': {
            'system_deps': ['PortAudio'],
            'install_instructions': {
                'PortAudio': 'http://www.portaudio.com/download.html'
            }
        },
        'moviepy': {
            'system_deps': ['FFmpeg'],
            'install_instructions': {
                'FFmpeg': 'https://ffmpeg.org/download.html'
            }
        }
    }
    
    needs_special_handling = False
    special_instructions = []
    
    for lib in required_libs:
        lib_name = lib.split('==')[0] if '==' in lib else lib
        if lib_name in special_deps:
            needs_special_handling = True
            deps_info = special_deps[lib_name]
            
            special_instructions.append(f"\n[yellow]检测到 {lib_name} 需要以下系统级依赖：[/yellow]")
            for dep in deps_info['system_deps']:
                special_instructions.append(f"- {dep}")
            special_instructions.append("\n[blue]安装链接：[/blue]")
            for dep, url in deps_info['install_instructions'].items():
                special_instructions.append(f"- {dep}: {url}")
    
    return needs_special_handling, special_instructions

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
            lib_name = lib.split('==')[0] if '==' in lib else lib
            
            # 对特殊包进行处理
            special_packages = {
                'manim': {
                    'deps': [
                        'numpy', 'pillow', 'scipy', 'matplotlib', 'tqdm', 'colour', 'pycairo',
                        'cloup', 'click', 'moderngl', 'moderngl_window', 'mapbox-earcut',
                        'networkx', 'decorator'
                    ],
                    'message': """[yellow]提示：manim安装失败可能是因为：[/yellow]
1. 系统PATH中未正确添加MiKTeX和FFmpeg
2. 需要重启终端以使环境变量生效
3. 可以尝试手动执行: pip install manim"""
                },
                'torch': {
                    'deps': ['numpy', 'typing-extensions', 'filelock', 'sympy', 'networkx', 'jinja2'],
                    'message': """[yellow]提示：torch安装失败可能是因为：[/yellow]
1. 网络连接不稳定，建议使用国内镜像
2. 如果需要GPU支持，请先安装CUDA
3. 可以访问 https://pytorch.org/ 选择合适的版本"""
                },
                'tensorflow': {
                    'deps': [
                        'numpy', 'six', 'wheel', 'packaging', 'protobuf', 'keras',
                        'h5py', 'wrapt', 'opt-einsum', 'astunparse', 'gast'
                    ],
                    'message': """[yellow]提示：tensorflow安装失败可能是因为：[/yellow]
1. 需要先安装Microsoft Visual C++ Redistributable
2. 如果需要GPU支持，请先安装CUDA和cuDNN
3. 可以尝试安装CPU版本：pip install tensorflow-cpu"""
                },
                'opencv-python': {
                    'deps': ['numpy', 'pillow'],
                    'message': """[yellow]提示：opencv-python安装失败可能是因为：[/yellow]
1. 需要安装Microsoft Visual C++ Redistributable
2. 可以尝试安装headless版本：pip install opencv-python-headless"""
                },
                'pygame': {
                    'deps': ['numpy'],
                    'message': """[yellow]提示：pygame安装失败可能是因为：[/yellow]
1. 需要安装SDL库
2. 需要安装Microsoft Visual C++ Redistributable
3. 可以尝试：pip install pygame --pre"""
                },
                'kivy': {
                    'deps': ['docutils', 'pygments', 'kivy_deps.sdl2', 'kivy_deps.glew'],
                    'message': """[yellow]提示：kivy安装失败可能是因为：[/yellow]
1. 需要安装Microsoft Visual C++ Build Tools
2. 需要先安装kivy的依赖：pip install kivy_deps.sdl2 kivy_deps.glew
3. 建议使用官方预编译wheel：pip install kivy[base] kivy_examples"""
                }
            }
            
            if lib_name in special_packages:
                try:
                    package_info = special_packages[lib_name]
                    # 先尝试安装必要的依赖包
                    console.print(f"[yellow]正在安装{lib_name}的前置依赖...[/yellow]")
                    for dep in package_info['deps']:
                        try:
                            # 使用Popen实现实时输出
                            process = subprocess.Popen(
                                [python_path, "-m", "pip", "install", "--no-cache-dir", dep, "-i", mirrors[0]],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                bufsize=1,
                                universal_newlines=True
                            )
                            
                            # 读取输出
                            while True:
                                line = process.stdout.readline()
                                if not line and process.poll() is not None:
                                    break
                                if line:
                                    line = line.strip()
                                    if any(keyword in line for keyword in [
                                        "Successfully installed",
                                        "Requirement already satisfied",
                                        "ERROR:",
                                        "WARNING:"
                                    ]):
                                        console.print(f"[yellow]{line}[/yellow]")
                                    elif "%" in line and "Downloading" in line:
                                        console.print(f"[blue]{line}[/blue]", end="\r")
                            
                            # 检查错误输出
                            error_output = process.stderr.read()
                            if error_output:
                                console.print(f"[red]{error_output.strip()}[/red]")
                            
                            if process.returncode == 0:
                                console.print(f"[green]✓ {dep}[/green]")
                            else:
                                console.print(f"[red]安装 {dep} 失败[/red]")
                                
                        except Exception as e:
                            console.print(f"[red]安装 {dep} 时出错: {str(e)}[/red]")
                    
                    # 然后尝试安装主程序
                    console.print(f"[yellow]正在安装{lib_name}主程序...[/yellow]")
                    for mirror in mirrors:
                        try:
                            # 使用Popen实现实时输出
                            cmd = [
                                python_path, 
                                "-m", 
                                "pip", 
                                "install", 
                                "--no-cache-dir",  # 添加no-cache-dir参数
                                lib
                            ]
                            if mirror:
                                cmd.extend(["-i", mirror])
                            
                            process = subprocess.Popen(
                                cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                bufsize=1,
                                universal_newlines=True
                            )
                            
                            # 读取输出
                            success = False
                            while True:
                                line = process.stdout.readline()
                                if not line and process.poll() is not None:
                                    break
                                if line:
                                    line = line.strip()
                                    if "Successfully installed" in line:
                                        success = True
                                    if any(keyword in line for keyword in [
                                        "Successfully installed",
                                        "Requirement already satisfied",
                                        "ERROR:",
                                        "WARNING:"
                                    ]):
                                        console.print(f"[yellow]{line}[/yellow]")
                                    elif "%" in line and "Downloading" in line:
                                        console.print(f"[blue]{line}[/blue]", end="\r")
                            
                            # 检查错误输出
                            error_output = process.stderr.read()
                            if error_output:
                                console.print(f"[red]{error_output.strip()}[/red]")
                            
                            if process.returncode == 0 and success:
                                console.print(f"[green]✅ {lib_name}[/green]")
                                installed = True
                                break
                            elif process.returncode == 0:
                                # 如果返回码是0但没有成功信息，可能需要重试
                                continue
                            
                        except Exception as e:
                            console.print(f"[red]安装出错: {str(e)}[/red]")
                            continue
                except Exception as e:
                    console.print(f"[red]安装 {lib_name} 时出错: {str(e)}[/red]")
            else:
                # 其他包使用常规安装方式
                for mirror in mirrors:
                    try:
                        # 添加超时控制
                        timeout = 300  # 5分钟超时
                        start_time = time.time()
                        
                        cmd = [
                            python_path, 
                            "-m", 
                            "pip", 
                            "install", 
                            lib, 
                            "--prefer-binary",  # 优先使用预编译的wheel包
                            "--disable-pip-version-check"  # 禁用版本检查以加快速度
                        ]
                        if mirror:
                            cmd.extend(["-i", mirror])
                            console.print(f"[yellow]尝试使用下载源: {mirror}[/yellow]")
                        
                        # 实时打印pip输出
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        
                        # 使用线程来读取输出，避免阻塞
                        def read_output(pipe, is_error=False):
                            try:
                                for line in pipe:
                                    # 检查是否超时
                                    if time.time() - start_time > timeout:
                                        process.terminate()
                                        console.print(f"[red]安装超时，已终止[/red]")
                                        return
                                        
                                    line = line.strip()
                                    if line:
                                        # 只显示重要信息
                                        if any(keyword in line for keyword in [
                                            "Successfully installed",
                                            "ERROR:",
                                            "WARNING:",
                                            "Requirement already satisfied"
                                        ]):
                                            console.print(f"[{'red' if is_error else 'yellow'}]{line}[/{'red' if is_error else 'yellow'}]")
                                        elif "%" in line and "Downloading" in line:  # 只显示下载进度
                                            console.print(f"[blue]{line}[/blue]", end="\r")
                            except Exception as e:
                                console.print(f"[red]输出读取错误: {str(e)}[/red]")

                        # 创建并启动输出读取线程
                        stdout_thread = Thread(target=read_output, args=(process.stdout,))
                        stderr_thread = Thread(target=read_output, args=(process.stderr, True))
                        stdout_thread.daemon = True
                        stderr_thread.daemon = True
                        stdout_thread.start()
                        stderr_thread.start()
                        
                        try:
                            # 等待进程完成，添加超时
                            return_code = process.wait(timeout=timeout)
                            
                            # 确保线程完成
                            stdout_thread.join(timeout=1)  # 缩短线程等待时间
                            stderr_thread.join(timeout=1)
                            
                            # 关闭管道
                            process.stdout.close()
                            process.stderr.close()
                            
                            if return_code == 0:
                                console.print(f"[green]✅ {lib_name}[/green]")
                                installed = True
                                break
                        except subprocess.TimeoutExpired:
                            process.terminate()
                            console.print(f"[red]安装超时，已终止[/red]")
                            continue
                    except Exception as e:
                        console.print(f"[red]安装过程出错: {str(e)}[/red]")
                        continue
                        
                if not installed:
                    failed_libs.append(lib)
                    if lib_name in special_packages:
                        console.print(special_packages[lib_name]['message'])
                
                progress.update(install_task, advance=1)
    
    if failed_libs:
        console.print(f"\n[red]以下依赖安装失败: {', '.join(failed_libs)},若开启了VPN，请关闭VPN后重试[/red]")
        return False
                
    return True

def check_system_dependencies(code_content):
    """检查是否需要系统级依赖"""
    # 检查是否包含系统级依赖标记
    system_dep_pattern = r'#\s*是否需要提前安装除以上的其它依赖\s*[：:]\s*是'
    return bool(re.search(system_dep_pattern, code_content))

def save_pending_dependencies(filename, required_libs):
    """保存待安装的依赖信息"""
    pending_file = "pending_dependencies.json"
    data = {
        "filename": filename,
        "required_libs": list(required_libs),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(pending_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        console.print(f"[yellow]⚠️ 保存待安装依赖信息失败: {str(e)}[/yellow]")

def check_pending_dependencies():
    """检查是否有待安装的依赖"""
    pending_file = "pending_dependencies.json"
    if not os.path.exists(pending_file):
        return
        
    try:
        # 先读取文件内容
        with open(pending_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        # 如果文件为空，直接删除并返回
        if not content:
            os.remove(pending_file)
            return
            
        # 解析JSON内容
        data = json.loads(content)
            
        filename = data.get("filename")
        required_libs = data.get("required_libs", [])
        timestamp = data.get("timestamp")
        
        if not filename or not required_libs:
            os.remove(pending_file)
            return
            
        console.print(f"\n[yellow]检测到上次有未完成的依赖安装[/yellow]")
        console.print(f"[blue]文件: {filename}[/blue]")
        console.print(f"[blue]时间: {timestamp}[/blue]")
        console.print("[blue]待安装依赖:[/blue]")
        for lib in required_libs:
            console.print(f"- {lib}")
            
        while True:
            console.print("\n[yellow]是否现在安装这些依赖？(y/n)[/yellow]")
            choice = input().strip().lower()
            if choice in ('y', 'yes'):
                # 记录原始依赖列表
                original_libs = required_libs.copy()
                
                # 尝试安装依赖
                if install_dependencies(required_libs):
                    console.print("[green]✅ 所有依赖安装成功[/green]")
                    os.remove(pending_file)
                    
                    # 询问是否立即运行代码
                    console.print("\n[yellow]是否立即运行该代码？(y/n)[/yellow]")
                    run_choice = input().strip().lower()
                    if run_choice in ('y', 'yes'):
                        with open(filename, "r", encoding="utf-8") as f:
                            code_content = f.read()
                        save_and_execute_code((code_content, os.path.basename(filename)), True)
                else:
                    # 检查哪些依赖安装成功了
                    remaining_libs = [lib for lib in original_libs if not is_installed(lib)]
                    if len(remaining_libs) < len(original_libs):
                        # 更新JSON文件，只保留未安装成功的依赖
                        data["required_libs"] = remaining_libs
                        with open(pending_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        console.print(f"[yellow]已更新待安装依赖列表，剩余 {len(remaining_libs)} 个依赖需要安装[/yellow]")
                    console.print("[red]❌ 部分依赖安装失败[/red]")
                break
            elif choice in ('n', 'no'):
                console.print("[yellow]已取消安装[/yellow]")
                break
            else:
                console.print("[red]无效的输入，请输入 y 或 n[/red]")
                
    except json.JSONDecodeError:
        # JSON解析错误，说明文件格式不正确
        console.print("[yellow]⚠️ 依赖信息文件格式不正确，正在重置...[/yellow]")
        os.remove(pending_file)
    except Exception as e:
        console.print(f"[red]❌ 检查待安装依赖时出错: {str(e)}[/red]")
        if os.path.exists(pending_file):
            os.remove(pending_file)

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

        # 先生成文件名并保存代码
        if suggested_filename:
            if not suggested_filename.endswith('.py'):
                suggested_filename += '.py'
            filename = os.path.join(code_dir, suggested_filename)
        else:
            filename = os.path.join(code_dir, f"generated_{datetime.now().strftime('%Y%m%d%H%M%S')}.py")
            
        # 保存代码文件
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code_content)
            
        # 显示保存路径
        abs_path = os.path.abspath(filename)
        console.print(f"\n[blue]💾 代码保存路径: [cyan]{abs_path}[/cyan][/blue]")

        # 检查是否需要系统级依赖
        needs_system_deps = check_system_dependencies(code_content)
        if needs_system_deps:
            console.print("\n[yellow]⚠️ 检测到此代码需要额外的系统级依赖[/yellow]")
            console.print("[yellow]请按以下步骤操作：[/yellow]")
            console.print("1. 先安装代码注释中提到的系统级依赖")
            console.print("2. 关闭当前终端")
            console.print("3. 重新运行本程序")
            
            # 提取并保存待安装的依赖信息
            required_libs = [
                lib for lib in extract_imports(code_content)
                if not is_installed(lib)
            ]
            if required_libs:
                save_pending_dependencies(filename, required_libs)
                
            return True

        # 如果不需要系统级依赖，则继续安装Python依赖
        required_libs = [
            lib for lib in extract_imports(code_content)
            if not is_installed(lib)
        ]
        
        # 如果有依赖且安装失败，保存依赖信息
        if required_libs and not install_dependencies(required_libs):
            console.print("\n[red]⚠️ 部分依赖安装失败,代码可能无法正常运行[/red]")
            save_pending_dependencies(filename, required_libs)
            return True  # 返回True因为文件已经保存

        if execute:
            # 获取虚拟环境Python解释器
            python_path = setup_virtual_env()
            
            # 执行代码
            console.print("\n[yellow]🚀 正在新窗口中启动程序(Python 3.9)...[/yellow]")
            try:
                if sys.platform == "win32":
                    # Windows下使用相对路径执行Python文件
                    venv_python = os.path.join("venv3.9", "Scripts", "python.exe")
                    if not os.path.exists(venv_python):
                        console.print(f"\n[red]⚠️ 虚拟环境Python解释器不存在: {venv_python}[/red]")
                        return True  # 返回True因为文件已经保存
                    
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
                return True  # 返回True因为文件已经保存
            
            return True
        else:
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
            # 根据当前客户端类型选择模型
            if current_client_type == QWEN_CLIENT:
                model = "qwen-max-2025-01-25"
            
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
    """智能获取用户输入"""
    console.print("\n[bold green]用户:[/bold green] ", end="")

    try:
        first_line = input().strip()
    except UnicodeDecodeError:
        console.print("[red]❌ 输入编码错误，请使用UTF-8编码输入[/red]")
        return ""
    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]输入已取消[/yellow]")
        return ""

    if not first_line:
        return ""

    if len(first_line) < 25:
        return first_line

    lines = [first_line]
    console.print("[dim]（输入内容超过25字，进入多行模式。按回车键继续输入，输入空行结束）[/dim]")

    try:
        while True:
            console.print(f"[dim]{len(lines) + 1}> [/dim]", end="")

            try:
                line = input()
            except UnicodeDecodeError:
                console.print("[red]❌ 输入编码错误，继续输入或输入空行结束[/red]")
                continue
            except KeyboardInterrupt:
                console.print("\n[yellow]已取消当前行输入，按回车结束整体输入，或继续输入新行[/yellow]")
                continue

            if not line.strip():
                break

            lines.append(line)

            if len(lines) > 50:
                console.print("[yellow]⚠️ 输入行数较多，记得输入空行结束[/yellow]")

    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]多行输入已终止，返回已输入内容[/yellow]")

    return "\n".join(lines)

def check_for_updates():
    """检查程序更新"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        if not os.path.exists(os.path.join(current_dir, "version_check_update.py")):
            console.print("\n[yellow]⚠️ 未找到更新检查模块，跳过更新检查[/yellow]")
            return
            
        sys.path.insert(0, current_dir)
        from version_check_update import get_local_version, check_update, download_and_update, ensure_version_file
        sys.path.pop(0)
        
        ensure_version_file()
        
        console.print("\n[yellow]正在检查更新...[/yellow]")
        
        # 检查更新，显示详细信息
        update_info = check_update(show_detail=True)
        
        if update_info is None:
            console.print("\n[yellow]是否重试检查更新？(y/n)[/yellow]")
            retry = input().strip().lower()
            if retry in ['y', 'yes']:
                console.print("\n[yellow]正在重新检查更新...[/yellow]")
                update_info = check_update(show_detail=True)
        
        if update_info and update_info.get('has_update'):
            latest_version = update_info.get('last_version', '')
            
            # 询问是否更新
            while True:
                choice = input("\n检查到更新，是否更新到最新版本？(y/n): ").lower().strip()
                if choice in ['y', 'yes']:
                    console.print("[green]开始更新...[/green]")
                    if download_and_update():
                        # 更新成功后，更新版本号为最新版本号
                        with open(os.path.join(current_dir, "version.txt"), "w", encoding="utf-8") as f:
                            f.write(latest_version)
                        console.print("[green]✓ 更新完成！请重启程序以应用更新。[/green]")
                    else:
                        console.print("[red]× 更新失败！[/red]")
                    break
                elif choice in ['n', 'no']:
                    console.print("[yellow]已取消更新[/yellow]")
                    break
                else:
                    console.print("[red]无效的输入，请输入 y 或 n[/red]")
            
    except Exception as e:
        console.print(f"\n[red]更新检查失败: {str(e)}[/red]")
        console.print("[yellow]建议：[/yellow]")
        console.print("1. 检查网络连接")
        console.print("2. 确认是否可以访问更新服务器")
        console.print("3. 检查version.txt文件是否存在且未损坏")
        console.print("4. 如果问题持续，可以尝试重新下载程序")

def clear_terminal():
    """清除终端内容"""
    if sys.platform == "win32":
        os.system("cls")
    else:
        os.system("clear")

def ls_and_run_code():
    """列出代码工具库中的文件并允许选择运行"""
    code_dir = "代码工具库"
    if not os.path.exists(code_dir):
        console.print("[yellow]⚠️ 代码工具库目录不存在[/yellow]")
        return

    # 获取所有.py文件
    py_files = [f for f in os.listdir(code_dir) if f.endswith('.py')]
    if not py_files:
        console.print("[yellow]⚠️ 没有找到Python文件[/yellow]")
        return

    # 显示文件列表
    console.print("\n[cyan]代码工具库文件列表：[/cyan]")
    for i, file in enumerate(py_files, 1):
        console.print(f"[blue]{i}.[/blue] {file}")

    # 获取用户选择
    while True:
        try:
            choice = input("\n请输入文件序号（按回车返回）: ").strip()
            if not choice:  # 直接回车返回
                return
            
            file_index = int(choice) - 1
            if 0 <= file_index < len(py_files):
                selected_file = os.path.join(code_dir, py_files[file_index])
                
                # 读取文件内容
                with open(selected_file, 'r', encoding='utf-8') as f:
                    code_content = f.read()
                
                # 提取并检查依赖
                required_libs = extract_imports(code_content)
                if required_libs:
                    console.print("\n[yellow]正在检查已安装的依赖...[/yellow]")
                    # 过滤出未安装的依赖
                    uninstalled_libs = [lib for lib in required_libs if not is_installed(lib)]
                    if uninstalled_libs:
                        console.print("\n[yellow]检测到以下依赖尚未安装：[/yellow]")
                        for lib in uninstalled_libs:
                            console.print(f"[blue]- {lib}[/blue]")
                        console.print("\n[yellow]正在安装缺失的依赖...[/yellow]")
                        if not install_dependencies(uninstalled_libs):
                            console.print("\n[red]⚠️ 部分依赖安装失败，代码可能无法正常运行[/red]")
                            continue
                    else:
                        console.print("[green]✓ 所有依赖已安装[/green]")
                
                # 获取虚拟环境Python解释器
                python_path = setup_virtual_env()
                
                # 执行代码
                console.print("\n[yellow]🚀 正在新窗口中启动程序(Python 3.9)...[/yellow]")
                try:
                    if sys.platform == "win32":
                        # Windows下使用相对路径执行Python文件
                        venv_python = os.path.join("venv3.9", "Scripts", "python.exe")
                        if not os.path.exists(venv_python):
                            console.print(f"\n[red]⚠️ 虚拟环境Python解释器不存在: {venv_python}[/red]")
                            return
                        
                        # 使用相对路径构建命令
                        rel_python = os.path.relpath(venv_python)
                        rel_filename = os.path.relpath(selected_file)
                        cmd = f'start cmd /c "{rel_python} {rel_filename} & pause"'
                        subprocess.Popen(cmd, shell=True)
                    else:
                        if sys.platform == "darwin":  # macOS
                            subprocess.Popen(['open', '-a', 'Terminal', '--', python_path, selected_file])
                        else:  # Linux
                            terminals = ['gnome-terminal', 'xterm', 'konsole']
                            for term in terminals:
                                try:
                                    subprocess.Popen([term, '--', python_path, selected_file])
                                    break
                                except FileNotFoundError:
                                    continue
                            else:
                                # 如果没有找到图形终端，使用当前终端运行
                                subprocess.Popen([python_path, selected_file])
                except Exception as e:
                    console.print(f"\n[red]⚠️ 启动程序失败: {str(e)}[/red]")
                break
            else:
                console.print("[red]❌ 无效的序号，请重新输入[/red]")
        except ValueError:
            console.print("[red]❌ 请输入有效的数字[/red]")
        except Exception as e:
            console.print(f"[red]❌ 发生错误: {str(e)}[/red]")

def main():
    try:
        global current_client_type, client
        
        # 添加变量保存最后生成的代码
        last_generated_code = None
        last_suggested_filename = None
        
        # 检查程序更新
        check_for_updates()
        
        # 检查是否有待安装的依赖
        check_pending_dependencies()
        
        # 环境检查 - 只在DeepSeek模式下进行
        if current_client_type == DEEPSEEK_CLIENT:
            check_python_version()
            
            # 生成requirements.txt
            if not os.path.exists(REQUIREMENTS_FILE):
                generate_requirements()
            
            # 设置虚拟环境
            setup_virtual_env()
        
        printer = StreamPrinter()
        current_model = "deepseek-chat" if current_client_type == DEEPSEEK_CLIENT else "qwen-max-2025-01-25"  # 默认模型
        
        def show_menu():
            """显示程序菜单"""
            console.print(Panel.fit(
                "[bold yellow]AI 智能代码执行助手[/bold yellow]\n[dim]r 切换到 reasoner(深度思考) | c 切换到 chat(一般模式) | cl 清除记忆 | ls 列出并运行代码 | -n 仅保存不执行下次代码 | s 保存上次代码 |\nrun 保存并执行上次代码 | 触发词: 写, 代码, 生成 | 多于25字时，按两次回车发送[/dim]",
                border_style="blue"
            ))

        def init_messages():
            """初始化对话记忆，提示词"""
            return [{
                "role": "system",
                "content": """你是一个Python专家。在生成代码时，请遵循以下规则：

## 基础结构
1. 代码块格式（必须严格遵守）
- 代码块内容必须按以下格式编写：
文件名：『中文命名』.py  『』包裹名称，".py"在外围
```
# 依赖包：xxx
# 前置预装依赖包：xxx
# pip install xxx
# 是否需要处理中文字符：是
# 是否需要提前安装除以上的其它依赖：是
# 是否需要处理文件路径：是，考虑文件路径的引号兼容性问题

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
- 避免使用过时的包
- 复杂需求提示脚本能力边界
- 注意：如果需要安装系统级依赖（如MiKTeX、FFmpeg等），请提示用户：
1. 先安装所需的系统级依赖
2. 关闭当前终端
3. 重新运行本程序
这样才能确保系统级依赖生效
"""
            }]

        messages = init_messages()
        show_menu()
    
        while True:
            try:
                user_input = get_multiline_input().strip()
                
                # 忽略空输入
                if not user_input:
                    continue
                
                # 处理清除记忆命令
                if user_input == "cl":
                    messages = init_messages()  # 重新初始化消息列表
                    clear_terminal()  # 清除终端
                    show_menu()  # 重新显示菜单
                    console.print("[green]✓ 记忆已清除[/green]")
                    continue
                
                # 处理list命令
                if user_input == "ls":
                    ls_and_run_code()
                    continue

                # 处理run命令
                if user_input.strip().lower() == "run":
                    if last_generated_code:
                        # 检查依赖是否已安装
                        required_libs = extract_imports(last_generated_code)
                        if required_libs:
                            console.print("\n[yellow]正在检查已安装的依赖...[/yellow]")
                            # 过滤出未安装的依赖
                            uninstalled_libs = [lib for lib in required_libs if not is_installed(lib)]
                            if uninstalled_libs:
                                console.print("\n[yellow]检测到以下依赖尚未安装：[/yellow]")
                                for lib in uninstalled_libs:
                                    console.print(f"[blue]- {lib}[/blue]")
                                console.print("\n[yellow]正在安装缺失的依赖...[/yellow]")
                                if not install_dependencies(uninstalled_libs):
                                    console.print("\n[red]⚠️ 部分依赖安装失败，代码可能无法正常运行[/red]")
                                    continue
                            else:
                                console.print("[green]✓ 所有依赖已安装[/green]")
                        save_and_execute_code((last_generated_code, last_suggested_filename), True)
                    else:
                        console.print("\n[yellow]⚠️ 没有找到可以执行的代码，请先生成代码再使用run命令[/yellow]")
                    continue
                
                # 处理s命令（保存最后生成的代码）
                if user_input.strip().lower() == "s":
                    if last_generated_code:
                        save_and_execute_code((last_generated_code, last_suggested_filename), False)
                    else:
                        console.print("\n[yellow]⚠️ 没有找到可以保存的代码，请先生成代码再使用s命令[/yellow]")
                    continue
                
                # 处理模型切换 - 只在DeepSeek模式下有效
                if current_client_type == DEEPSEEK_CLIENT:
                    if user_input == "r":
                        current_model = "deepseek-reasoner"
                        console.print(f"\n[cyan]已切换到 [bright_blue]{current_model}[/bright_blue] 模型[/cyan]")
                        continue
                    elif user_input == "c":
                        current_model = "deepseek-chat"
                        console.print(f"\n[cyan]已切换到 {current_model} 模型[/cyan]")
                        continue
                
                # 检查是否包含 -n 标志
                execute_code = "-n" not in user_input
                # 移除 -n 标志，以免影响模型理解
                cleaned_input = user_input.replace("-n", "").strip()
                
                # 如果不是特殊命令，则传递给AI处理
                messages.append({"role": "user", "content": cleaned_input})
                
                # 流式对话时使用当前选择的模型
                response = chat_stream(messages, printer, current_model)
                printer.reset()  # 确保在对话结束后重置状态
                messages.append({"role": "assistant", "content": response["content"]})
                
                # 检查响应中是否包含代码块
                code_result = extract_code_from_response(response["content"])
                if code_result and code_result[0]:
                    code_content, suggested_filename = code_result
                    # 保存最后生成的代码
                    last_generated_code = code_content
                    last_suggested_filename = suggested_filename
                    
                    # 如果包含特定关键词，则自动处理代码
                    if any(kw in cleaned_input for kw in ["写", "代码", "生成"]):
                        # 提取并安装依赖
                        required_libs = extract_imports(code_content)
                        if required_libs:
                            console.print("\n[yellow]正在检查依赖...[/yellow]")
                            if not install_dependencies(required_libs):
                                console.print("\n[red]⚠️ 部分依赖安装失败，代码可能无法正常运行[/red]")
                                continue
                        
                        # 安装依赖成功后再保存和执行代码
                        save_and_execute_code((code_content, suggested_filename), execute_code)
                    else:
                        # 如果不包含关键词，提示用户可以使用run或s命令
                        console.print("\n[blue]💡 检测到代码块，你可以使用:[/blue]")
                        console.print("[yellow]- 输入 'run' 来保存并执行代码[/yellow]")
                        console.print("[yellow]- 输入 's' 来仅保存代码[/yellow]")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]🛑 操作已中断[/yellow]")
                break
    except Exception as e:
        console.print(f"\n[red]⚠️ 异常: {str(e)}[/red]")

if __name__ == "__main__":
    main()
    main()