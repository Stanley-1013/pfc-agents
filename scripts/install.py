#!/usr/bin/env python3
"""
Neuromorphic System - 安裝腳本

功能：
1. 檢查系統依賴
2. 複製 agent 定義到 ~/.claude/agents/
3. 如果資料庫不存在，初始化資料庫
4. 不會覆蓋現有資料庫（保護跨專案記憶）
"""

import os
import sqlite3
import shutil
import sys

def check_dependencies():
    """檢查系統依賴"""
    errors = []
    warnings = []

    # 1. Python 版本檢查
    if sys.version_info < (3, 8):
        errors.append(f"Python 3.8+ 必須，目前版本: {sys.version}")

    # 2. sqlite3 模組檢查（Python 內建，但確認可用）
    try:
        import sqlite3
        # 測試是否能建立記憶體資料庫
        conn = sqlite3.connect(':memory:')
        conn.execute('SELECT 1')
        conn.close()
    except Exception as e:
        errors.append(f"sqlite3 模組無法使用: {e}")

    # 3. 目錄權限檢查
    claude_dir = os.path.expanduser('~/.claude')
    if os.path.exists(claude_dir):
        if not os.access(claude_dir, os.W_OK):
            errors.append(f"無寫入權限: {claude_dir}")
    else:
        # 嘗試建立
        try:
            os.makedirs(claude_dir, exist_ok=True)
        except Exception as e:
            errors.append(f"無法建立目錄 {claude_dir}: {e}")

    # 回報結果
    if errors:
        print("❌ 依賴檢查失敗:")
        for e in errors:
            print(f"   - {e}")
        print("\n請先解決上述問題再重新執行安裝。")
        sys.exit(1)

    if warnings:
        print("⚠️  警告:")
        for w in warnings:
            print(f"   - {w}")

    print("✅ 依賴檢查通過")
    return True

def install():
    base_dir = os.path.expanduser('~/.claude/neuromorphic')
    agents_dir = os.path.expanduser('~/.claude/agents')
    brain_dir = os.path.join(base_dir, 'brain')
    db_path = os.path.join(brain_dir, 'brain.db')
    schema_path = os.path.join(brain_dir, 'schema.sql')

    print("🧠 安裝 Neuromorphic Multi-Agent System")
    print("=" * 50)

    # 0. 依賴檢查
    check_dependencies()

    # 1. 確保目錄存在
    os.makedirs(agents_dir, exist_ok=True)
    print(f"✅ 確認 agents 目錄: {agents_dir}")

    # 2. 複製 agent 定義到 ~/.claude/agents/
    source_agents = os.path.join(base_dir, 'agents')
    if os.path.exists(source_agents):
        for agent_file in os.listdir(source_agents):
            if agent_file.endswith('.md'):
                src = os.path.join(source_agents, agent_file)
                dst = os.path.join(agents_dir, agent_file)
                shutil.copy2(src, dst)
                print(f"✅ 安裝 agent: {agent_file}")

    # 3. 初始化資料庫（只在不存在時）
    if os.path.exists(db_path):
        print(f"✅ 資料庫已存在: {db_path}")
        print("   （跨專案記憶會保留，不會重新初始化）")
    else:
        init_database(db_path, schema_path)

    # 4. 完成
    print("\n" + "=" * 50)
    print("🎉 安裝完成！")
    print("\n可用 Agents:")
    print("  pfc        - 任務規劃、分解子任務")
    print("  executor   - 執行單一任務")
    print("  critic     - 驗證結果品質")
    print("  memory     - 記憶管理")
    print("  researcher - 資訊收集")
    print("\n使用方式:")
    print("  對 Claude Code 說：「使用 pfc agent 規劃 [任務描述]」")
    print("\n文檔:")
    print(f"  README:       {os.path.join(base_dir, 'README.md')}")
    print(f"  協作指南:     {os.path.join(base_dir, 'SYSTEM_GUIDE.md')}")
    print(f"  Agent 指南:   {os.path.join(base_dir, 'AGENT_SELECTOR.md')}")

def init_database(db_path, schema_path):
    """初始化 SQLite 資料庫"""
    print(f"📦 初始化資料庫: {db_path}")

    db = sqlite3.connect(db_path)
    cursor = db.cursor()

    # 執行 schema
    if os.path.exists(schema_path):
        with open(schema_path) as f:
            cursor.executescript(f.read())
        print("✅ Schema 已載入")
    else:
        print(f"❌ 找不到 schema: {schema_path}")
        return

    # 插入初始記憶
    cursor.execute('''
        INSERT INTO long_term_memory (category, title, content, importance)
        VALUES ('knowledge', 'System Initialized',
                'Neuromorphic Multi-Agent System 已初始化。包含 PFC, Executor, Critic, Memory, Researcher 五個 agent。',
                10)
    ''')

    db.commit()
    db.close()
    print("✅ 資料庫初始化完成")

def reset_database():
    """強制重置資料庫（謹慎使用）"""
    base_dir = os.path.expanduser('~/.claude/neuromorphic')
    brain_dir = os.path.join(base_dir, 'brain')
    db_path = os.path.join(brain_dir, 'brain.db')
    schema_path = os.path.join(brain_dir, 'schema.sql')

    print("⚠️  警告：這會清空所有跨專案記憶！")
    response = input("確定要重置嗎？輸入 'RESET' 確認: ")
    if response == 'RESET':
        if os.path.exists(db_path):
            os.remove(db_path)
        init_database(db_path, schema_path)
        print("✅ 資料庫已重置")
    else:
        print("取消重置")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_database()
    else:
        install()
