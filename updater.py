import os
import sys
import time
import json
import shutil
from pathlib import Path

def update_files():
    try:
        # 读取待更新文件信息
        with open("pending_update.json", "r", encoding="utf-8") as f:
            pending_files = json.load(f)
            
        # 等待主程序完全退出
        time.sleep(2)
        
        # 执行文件替换
        for file in pending_files["files"]:
            src_path = os.path.join(pending_files["source_dir"], file)
            dst_path = os.path.join(os.path.dirname(__file__), file)
            
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
                
        # 清理临时文件
        shutil.rmtree(os.path.dirname(pending_files["source_dir"]))
        os.remove("pending_update.json")
        
        # 重启主程序
        os.startfile("aigene.py")
        
    except Exception as e:
        with open("update_error.log", "w") as f:
            f.write(f"更新失败: {str(e)}")

if __name__ == "__main__":
    update_files() 