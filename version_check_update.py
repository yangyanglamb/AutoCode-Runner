'''version_check_update'''
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
import subprocess

# 添加日志文件
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_log.txt")

def log_error(message):
    """记录错误信息到文件"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except:
        pass

# 版本信息文件路径
VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.txt")
# API基础URL
BASE_URL = "http://43.242.201.140:5000"

def ensure_version_file():
    """确保版本文件存在"""
    try:
        if not os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "w", encoding="utf-8") as f:
                f.write("0" * 40)  # 写入初始版本号
            print(f"✅ 已创建版本文件: {VERSION_FILE}")
    except Exception as e:
        print(f"❌ 创建版本文件失败: {e}")

def get_local_version():
    """获取本地版本号（hash）"""
    try:
        ensure_version_file()  # 确保文件存在
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ 读取本地版本失败: {e}")
        return "0" * 40

def check_update(show_detail=True):  # 默认显示详细信息
    """检查更新"""
    try:
        # 获取本地版本
        local_version = get_local_version()
        if show_detail:
            print(f"当前本地版本: {local_version}")
            print(f"正在连接服务器 {BASE_URL}/check_update ...")
        
        # 设置超时时间和重试次数
        session = requests.Session()
        session.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
        
        try:
            response = session.get(f"{BASE_URL}/check_update", timeout=5)
        except requests.exceptions.Timeout:
            print("❌ 连接服务器超时，请检查网络连接")
            log_error("连接服务器超时")
            return None
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到服务器，请检查网络连接")
            log_error("无法连接到服务器")
            return None
            
        if show_detail:
            print(f"服务器响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                update_info = response.json()
            except json.JSONDecodeError:
                print("❌ 服务器返回的数据格式不正确（非JSON格式）")
                log_error(f"服务器返回非JSON数据: {response.text}")
                return None
                
            if show_detail:
                print(f"服务器返回数据: {update_info}")
                
            # 确保返回的数据包含所需的字段
            required_fields = ['github版本', '可以下载', '服务器版本']
            missing_fields = [field for field in required_fields if field not in update_info]
            
            if missing_fields:
                print(f"❌ 服务器返回的数据缺少必要字段: {', '.join(missing_fields)}")
                log_error(f"服务器返回数据缺少字段: {missing_fields}")
                return None
                
            # 构建返回的更新信息
            update_info = {
                'current_version': local_version,
                'last_version': update_info['github版本'],
                'has_update': local_version != update_info['github版本'] and update_info['可以下载'],
                'error': None
            }
                
            if show_detail:
                print(f"\n当前版本: {local_version}")
                print(f"最新版本: {update_info['last_version']}")
                if update_info['has_update']:
                    print("\n[发现新版本]")
                else:
                    print("\n✅ 当前已是最新版本")
                    
            return update_info
            
        elif response.status_code == 404:
            print("❌ 远程仓库不存在")
            log_error("远程仓库不存在")
        else:
            print(f"❌ 检查更新失败: HTTP {response.status_code}")
            if show_detail:
                print(f"响应内容: {response.text}")
            log_error(f"检查更新失败: HTTP {response.status_code}, 响应: {response.text}")
        return None
        
    except Exception as e:
        print(f"❌ 检查更新时发生错误: {e}")
        if show_detail:
            print("错误详细信息:")
            import traceback
            traceback.print_exc()
        log_error(f"检查更新异常: {str(e)}\n{traceback.format_exc()}")
        return None

def download_and_update():
    """下载并更新程序"""
    temp_dir = None
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        temp_dir = Path(current_dir) / "temp_update"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        update_zip = temp_dir / "update.zip"
        
        # 下载更新包
        print("正在下载更新...")
        response = requests.get(f"{BASE_URL}/download", stream=True)
        if response.status_code != 200:
            print(f"❌ 下载失败: HTTP {response.status_code}")
            return False

        # 保存更新包到临时目录
        with open(update_zip, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # 解压更新包
        print("正在解压更新包...")
        with zipfile.ZipFile(str(update_zip), 'r') as zip_ref:
            # 解压到临时目录
            extract_dir = temp_dir / "extracted"
            if extract_dir.exists():
                shutil.rmtree(str(extract_dir))
            extract_dir.mkdir(parents=True, exist_ok=True)
            zip_ref.extractall(str(extract_dir))

        # 复制更新文件
        def copy_files(src_dir, dst_dir):
            # 获取当前运行的Python文件的绝对路径
            current_file = os.path.abspath(__file__)
            aigene_file = os.path.join(current_dir, "aigene.py")
            
            for item in os.listdir(src_dir):
                src_path = os.path.join(src_dir, item)
                dst_path = os.path.join(dst_dir, item)
                
                if os.path.isfile(src_path):
                    # 跳过正在运行的文件
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

        # 从临时目录复制文件到当前目录
        print("正在更新文件...")
        copy_files(str(extract_dir), current_dir)

        # 将正在运行的文件标记为待更新
        pending_update_file = os.path.join(current_dir, "pending_update.json")
        pending_files = {
            "files": [
                os.path.basename(__file__),
                "aigene.py"
            ],
            "source_dir": str(extract_dir),
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
        
    finally:
        # 在函数结束时清理临时目录
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(str(temp_dir))
                print("已清理临时文件")
            except Exception as e:
                print(f"清理临时文件失败: {e}")

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
        print("开始检查更新...")
        
        # 检查并处理待更新的文件
        print("检查待更新文件...")
        check_pending_updates()
        
        # 确保版本文件存在
        print("检查版本文件...")
        ensure_version_file()
        
        print("连接服务器检查更新...")
        update_info = check_update(show_detail=True)  # 在这里启用详细输出
        if update_info is None:
            print("无法获取更新信息，程序将退出")
            input("按回车键退出...") 
            return
            
        # 检查是否需要更新
        if update_info["has_update"]:  # 修改判断条件
            print(f"\n[发现新版本]")

            
            # 询问用户是否更新
            while True:
                choice = input("检查到更新，是否更新到最新版本？(y/n): ").lower().strip()
                if choice in ['y', 'yes']:
                    if download_and_update():
                        # 更新成功后，更新版本号为最新版本号
                        with open(VERSION_FILE, "w", encoding="utf-8") as f:
                            f.write(update_info['last_version'])  # 使用last_version
                        print("🎉 程序已更新完成，请重启程序！")
                    input("按回车键退出...") 
                    break
                elif choice in ['n', 'no']:
                    print("已取消更新")
                    input("按回车键退出...") 
                    break
                else:
                    print("无效的输入，请输入 y 或 n")
        else:
            print("✅ 当前已是最新版本")
            input("按回车键退出...") # 添加结束提示

    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        print("错误详细信息:")
        import traceback
        traceback.print_exc()
        input("按回车键退出...") 

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"程序运行出错: {str(e)}\n"
        import traceback
        error_msg += traceback.format_exc()
        log_error(error_msg)
        print(error_msg)
        input("按回车键退出...") 