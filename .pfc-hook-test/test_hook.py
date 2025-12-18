#!/usr/bin/env python3
"""
Hook 機制測試檔案

這個測試驗證了 Hook 系統的基本流程：
1. 任務建立時觸發 on_task_create 鉤子
2. 任務完成時觸發 on_task_done 鉤子

測試使用 mock 來驗證鉤子被正確呼叫。
"""

import sys
import os
from unittest.mock import Mock, patch, call
from typing import Dict, List


class HookSystem:
    """簡單的 Hook 系統實現"""

    def __init__(self):
        """初始化 Hook 系統"""
        self.hooks = {
            'on_task_create': [],
            'on_task_done': []
        }

    def register(self, event: str, callback):
        """註冊 Hook 回調函數"""
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)

    def trigger(self, event: str, data: Dict):
        """觸發 Hook 事件"""
        if event not in self.hooks:
            return

        for callback in self.hooks[event]:
            try:
                callback(data)
            except Exception as e:
                print(f"Error in {event} hook: {e}")

    def clear(self):
        """清除所有 Hook"""
        for event in self.hooks:
            self.hooks[event] = []


class Task:
    """簡單的任務類"""

    def __init__(self, task_id: str, description: str):
        self.id = task_id
        self.description = description
        self.status = 'pending'

    def complete(self):
        """完成任務"""
        self.status = 'done'


def test_hook_registration():
    """測試 Hook 註冊機制"""
    print("TEST: Hook Registration")

    hook_system = HookSystem()
    mock_callback = Mock()

    # 註冊 Hook
    hook_system.register('on_task_create', mock_callback)

    # 驗證 Hook 被註冊
    assert len(hook_system.hooks['on_task_create']) == 1
    assert hook_system.hooks['on_task_create'][0] == mock_callback

    print("✓ Hook 成功註冊\n")


def test_hook_trigger_on_task_create():
    """測試任務建立時的 Hook 觸發"""
    print("TEST: Hook Trigger - on_task_create")

    hook_system = HookSystem()
    mock_callback = Mock()

    # 註冊 on_task_create Hook
    hook_system.register('on_task_create', mock_callback)

    # 建立任務
    task = Task('task-001', '測試任務')
    task_data = {'id': task.id, 'description': task.description}

    # 觸發 Hook
    hook_system.trigger('on_task_create', task_data)

    # 驗證回調被呼叫且收到正確的資料
    mock_callback.assert_called_once_with(task_data)

    print("✓ on_task_create Hook 正確觸發\n")


def test_hook_trigger_on_task_done():
    """測試任務完成時的 Hook 觸發"""
    print("TEST: Hook Trigger - on_task_done")

    hook_system = HookSystem()
    mock_callback = Mock()

    # 註冊 on_task_done Hook
    hook_system.register('on_task_done', mock_callback)

    # 建立並完成任務
    task = Task('task-002', '另一個測試任務')
    task.complete()

    task_data = {'id': task.id, 'status': task.status}

    # 觸發 Hook
    hook_system.trigger('on_task_done', task_data)

    # 驗證回調被呼叫
    mock_callback.assert_called_once_with(task_data)
    assert task.status == 'done'

    print("✓ on_task_done Hook 正確觸發\n")


def test_multiple_hooks():
    """測試多個 Hook 回調"""
    print("TEST: Multiple Hook Callbacks")

    hook_system = HookSystem()
    mock_callback_1 = Mock()
    mock_callback_2 = Mock()

    # 註冊多個 Hook
    hook_system.register('on_task_create', mock_callback_1)
    hook_system.register('on_task_create', mock_callback_2)

    task_data = {'id': 'task-003', 'description': '多 Hook 測試'}

    # 觸發 Hook
    hook_system.trigger('on_task_create', task_data)

    # 驗證兩個回調都被呼叫
    mock_callback_1.assert_called_once_with(task_data)
    mock_callback_2.assert_called_once_with(task_data)

    print("✓ 多個 Hook 回調都被正確執行\n")


def test_hook_with_error_handling():
    """測試 Hook 的錯誤處理"""
    print("TEST: Hook Error Handling")

    hook_system = HookSystem()

    # 建立一個會丟出錯誤的回調
    def failing_callback(data):
        raise ValueError("模擬錯誤")

    # 建立一個正常的回調
    normal_callback = Mock()

    hook_system.register('on_task_create', failing_callback)
    hook_system.register('on_task_create', normal_callback)

    task_data = {'id': 'task-004'}

    # 觸發 Hook（應該不會因為第一個失敗而中斷）
    hook_system.trigger('on_task_create', task_data)

    # 驗證第二個回調仍然被呼叫
    normal_callback.assert_called_once()

    print("✓ Hook 錯誤被正確處理\n")


def run_all_tests():
    """執行所有測試"""
    print("=" * 50)
    print("Hook 機制測試套件")
    print("=" * 50 + "\n")

    try:
        test_hook_registration()
        test_hook_trigger_on_task_create()
        test_hook_trigger_on_task_done()
        test_multiple_hooks()
        test_hook_with_error_handling()

        print("=" * 50)
        print("✓ 所有測試通過！")
        print("=" * 50)
        return True

    except AssertionError as e:
        print(f"\n✗ 測試失敗: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 發生錯誤: {e}")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
