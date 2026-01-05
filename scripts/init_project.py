#!/usr/bin/env python3
"""
Neuromorphic System - 專案初始化腳本
在每個專案中執行，建立專案設定
"""

import os
import sys
import sqlite3

def init_project(project_name):
    base_dir = os.path.expanduser('~/.claude/skills/neuromorphic')
    db_path = os.path.join(base_dir, 'brain', 'brain.db')

    print(f"🚀 初始化專案: {project_name}")
    print("=" * 50)

    # 1. 確認資料庫存在
    if not os.path.exists(db_path):
        print(f"❌ 資料庫不存在: {db_path}")
        print(f"請先執行: python {os.path.join(base_dir, 'scripts', 'install.py')}")
        sys.exit(1)

    # 2. 建立專案記錄
    db = sqlite3.connect(db_path)
    cursor = db.cursor()

    cursor.execute('''
        INSERT INTO long_term_memory
        (category, project, title, content, importance)
        VALUES ('knowledge', ?, 'Project Initialized', ?, 8)
    ''', (project_name, f'專案 {project_name} 已初始化神經擬態系統'))

    cursor.execute('''
        INSERT INTO episodes
        (project, event_type, summary)
        VALUES (?, 'milestone', ?)
    ''', (project_name, f'專案 {project_name} 初始化'))

    db.commit()
    db.close()

    # 3. 建立本地設定檔（放在 .claude/pfc/ 目錄下）
    pfc_dir = os.path.join(os.getcwd(), '.claude', 'pfc')
    os.makedirs(pfc_dir, exist_ok=True)

    config_content = f'''# Neuromorphic System Configuration
# 專案: {project_name}

PROJECT_NAME = "{project_name}"
BRAIN_DB = "{db_path}"
NEUROMORPHIC_PATH = "{base_dir}"

# 使用方式:
# import sys
# sys.path.insert(0, NEUROMORPHIC_PATH)
# from servers.memory import search_memory, store_memory
# from servers.tasks import create_task, get_task_progress
'''

    config_path = os.path.join(pfc_dir, 'config.py')
    with open(config_path, 'w') as f:
        f.write(config_content)

    # 4. 完成
    print(f"✅ 專案記錄已建立")
    print(f"✅ 本地設定: {config_path}")
    print("\n" + "=" * 50)
    print("🎉 專案初始化完成！")
    print(f"\n專案: {project_name}")
    print(f"資料庫: {db_path}")
    print("\n使用方式:")
    print("  對 Claude Code 說：")
    print(f'  「這是 {project_name} 專案，使用 pfc agent 規劃重構任務」')
    print("\n專案設定位置:")
    print(f"  .claude/pfc/config.py")
    print(f"  .claude/pfc/INDEX.md  (SSOT 索引)")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方式: python init_project.py <project_name>")
        print("範例: python init_project.py my-awesome-app")
        sys.exit(1)

    init_project(sys.argv[1])
