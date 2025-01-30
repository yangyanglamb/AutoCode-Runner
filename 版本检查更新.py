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
    """获取本地版本号"""
    try:
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "0.0.0"  # 如果文件不存在，返回初始版本
    except Exception as e:
        print(f"❌ 读取本地版本失败: {e}")
        return "0.0.0"

def check_update():
    """检查更新"""
    try:
        response = requests.get(f"{BASE_URL}/check_update")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print("❌ 远程仓库不存在")
        else:
            print(f"❌ 检查更新失败: HTTP {response.status_code}")
        return None
    except Exception as e:
        print(f"❌ 检查更新时发生错误: {e}")
        return None

def download_and_update():
    """下载并更新程序"""
    try:
        # 获取项目根目录
        root_dir = os.path.dirname(os.path.abspath(__file__))
        
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
            for item in os.listdir(src_dir):
                src_path = os.path.join(src_dir, item)
                dst_path = os.path.join(dst_dir, item)
                
                if os.path.isfile(src_path):
                    # 如果目标文件存在，先删除
                    if os.path.exists(dst_path):
                        os.remove(dst_path)
                    shutil.copy2(src_path, dst_path)
                elif os.path.isdir(src_path):
                    if not os.path.exists(dst_path):
                        os.makedirs(dst_path)
                    copy_files(src_path, dst_path)

        # 从临时目录复制文件到项目目录
        print("正在更新文件...")
        copy_files(extract_dir, root_dir)

        # 清理临时文件
        print("正在清理临时文件...")
        shutil.rmtree(temp_dir)

        print("✅ 更新完成！")
        return True

    except Exception as e:
        print(f"❌ 更新过程中发生错误: {e}")
        return False

def main():
    """主函数"""
    try:
        # 获取本地版本
        local_version = get_local_version()
        print(f"当前版本: {local_version}")

        # 检查更新
        print("正在检查更新...")
        update_info = check_update()
        
        if update_info is None:
            return
        
        if not update_info["has_update"]:
            print("✅ 已是最新版本")
            return
            
        print(f"发现新版本: {update_info['current_version']}")
        
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