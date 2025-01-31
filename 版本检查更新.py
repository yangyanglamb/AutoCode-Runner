'''版本检查更新'''
# 依赖包：requests
# pip install requests

import os
import sys
import json
import shutil
import zipfile
import requests
from pathlib import Path
from datetime import datetime

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

# 版本信息文件路径
VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.txt")
# API基础URL
BASE_URL = "http://43.242.201.140:5000"

def get_local_version():
    """获取本地版本号（hash）"""
    try:
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "0" * 40  # 如果文件不存在，返回一个初始hash（40个0）
    except Exception as e:
        print(f"❌ 读取本地版本失败: {e}")
        return "0" * 40

def check_update():
    """检查更新"""
    try:
        response = requests.get(f"{BASE_URL}/check_update")
        if response.status_code == 200:
            update_info = response.json()
            # 确保返回的数据包含所需的字段
            if all(key in update_info for key in ['current_version', 'last_version', 'has_update', 'error']):
                return update_info
            else:
                print("❌ 服务器返回的数据格式不正确")
                return None
        elif response.status_code == 404:
            print("❌ 远程仓库不存在")
        else:
            print(f"❌ 检查更新失败: HTTP {response.status_code}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 检查更新时发生网络错误: {e}")
        return None
    except Exception as e:
        print(f"❌ 检查更新时发生错误: {e}")
        return None

def download_and_update():
    """下载并更新程序"""
    try:
        # 获取项目根目录
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 下载更新包
        print("正在下载更新...")
        response = requests.get(f"{BASE_URL}/download", stream=True)
        if response.status_code != 200:
            print(f"❌ 下载失败: HTTP {response.status_code}")
            return False

        # 保存更新包到临时目录
        temp_dir = os.path.join(root_dir, "temp_update")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        update_zip = os.path.join(temp_dir, "update.zip")
        with open(update_zip, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # 解压更新包
        print("正在解压更新包...")
        with zipfile.ZipFile(update_zip, 'r') as zip_ref:
            # 解压到临时目录
            extract_dir = os.path.join(temp_dir, "extracted")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)
            zip_ref.extractall(extract_dir)

        # 复制更新文件
        def copy_files(src_dir, dst_dir):
            # 获取当前运行的Python文件的绝对路径
            current_file = os.path.abspath(__file__)
            aigene_file = os.path.join(root_dir, "aigene.py")
            
            for item in os.listdir(src_dir):
                src_path = os.path.join(src_dir, item)
                dst_path = os.path.join(dst_dir, item)
                
                if os.path.isfile(src_path):
                    # 跳过当前正在运行的文件
                    if os.path.abspath(dst_path) in [current_file, aigene_file]:
                        print(f"跳过更新正在运行的文件: {item}")
                        continue
                        
                    # 如果目标文件存在，先删除
                    if os.path.exists(dst_path):
                        os.remove(dst_path)
                    shutil.copy2(src_path, dst_path)
                    print(f"更新文件: {item}")
                elif os.path.isdir(src_path):
                    if not os.path.exists(dst_path):
                        os.makedirs(dst_path)
                    copy_files(src_path, dst_path)

        # 从临时目录复制文件到项目目录
        print("正在更新文件...")
        copy_files(extract_dir, root_dir)

        # 将正在运行的文件标记为待更新
        pending_update_file = os.path.join(root_dir, "pending_update.json")
        pending_files = {
            "files": [
                os.path.relpath(__file__, root_dir),
                "aigene.py"
            ],
            "source_dir": extract_dir,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(pending_update_file, "w", encoding="utf-8") as f:
            json.dump(pending_files, f, ensure_ascii=False, indent=2)

        # 清理临时文件（保留解压目录供后续更新）
        os.remove(update_zip)
        
        print("✅ 更新完成！")
        print("注意：部分核心文件将在程序重启后完成更新")
        return True

    except Exception as e:
        print(f"❌ 更新过程中发生错误: {e}")
        return False

def check_pending_updates():
    """检查是否有待更新的文件"""
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pending_update_file = os.path.join(root_dir, "pending_update.json")
        
        if not os.path.exists(pending_update_file):
            return
            
        with open(pending_update_file, "r", encoding="utf-8") as f:
            pending_files = json.load(f)
            
        source_dir = pending_files.get("source_dir")
        if not source_dir or not os.path.exists(source_dir):
            os.remove(pending_update_file)
            return
            
        # 更新待更新的文件
        for file in pending_files["files"]:
            src_path = os.path.join(source_dir, file)
            dst_path = os.path.join(root_dir, file)
            
            if os.path.exists(src_path):
                # 如果目标文件存在，先删除
                if os.path.exists(dst_path):
                    os.remove(dst_path)
                shutil.copy2(src_path, dst_path)
                print(f"完成更新文件: {file}")
                
        # 清理临时文件和标记文件
        shutil.rmtree(os.path.dirname(source_dir))
        os.remove(pending_update_file)
        
    except Exception as e:
        print(f"❌ 处理待更新文件时出错: {e}")

def main():
    """主函数"""
    try:
        # 检查并处理待更新的文件
        check_pending_updates()
        
        # 获取本地版本
        local_version = get_local_version()
        
        update_info = check_update()
        if update_info is None:
            return
            
        # 检查是否需要更新
        if update_info["last_version"] != local_version:
            print(f"发现新版本")
            print(f"当前版本: {local_version}")
            print(f"最新版本: {update_info['current_version']}")
            
            # 询问用户是否更新
            while True:
                choice = input("是否更新到最新版本？(y/n): ").lower().strip()
                if choice in ['y', 'yes']:
                    if download_and_update():
                        # 更新成功后，更新版本号
                        with open(VERSION_FILE, "w", encoding="utf-8") as f:
                            f.write(update_info['current_version'])
                        print("🎉 程序已更新完成，请重启程序！")
                    break
                elif choice in ['n', 'no']:
                    print("已取消更新")
                    break
                else:
                    print("无效的输入，请输入 y 或 n")

    except Exception as e:
        print(f"❌ 程序运行出错: {e}")

if __name__ == "__main__":
    main() 