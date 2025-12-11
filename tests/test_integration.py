"""
Integration Tests

端到端測試：
- 完整的 PFC → Executor → Critic 流程
- 資料在各層之間的流動
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Full Workflow Tests
# =============================================================================

class TestFullWorkflow:
    """端到端流程測試"""

    def test_pfc_query_to_critic_validation(self, sample_graph_data, sample_code_graph, sample_memories):
        """
        模擬完整流程：
        1. PFC 查詢 context（get_full_context）
        2. Executor 執行修改（模擬）
        3. Critic 驗證影響（validate_with_graph）
        """
        from servers.facade import get_full_context, validate_with_graph

        # Step 1: PFC 查詢 context
        branch = {"flow_id": "flow.auth"}
        context = get_full_context(branch, project_name="test")

        assert isinstance(context, dict)
        assert 'ssot' in context or 'code' in context

        # Step 2: 模擬 Executor 修改了檔案
        modified_files = ["src/auth/login.py"]

        # Step 3: Critic 驗證影響
        validation = validate_with_graph(modified_files, branch, project_name="test")

        assert isinstance(validation, dict)
        assert 'impact_analysis' in validation or 'suggestions' in validation

    def test_task_lifecycle(self, mock_db_path):
        """
        任務生命週期：
        create → update status → get progress → complete
        """
        from servers.tasks import (
            create_task, create_subtask, get_task,
            update_task_status, get_task_progress
        )

        # 建立主任務
        task_id = create_task("test", "Test main task", priority=5)
        assert task_id is not None

        # 建立子任務
        sub1 = create_subtask(task_id, "Subtask 1")
        sub2 = create_subtask(task_id, "Subtask 2")
        assert sub1 is not None
        assert sub2 is not None

        # 更新狀態
        update_task_status(sub1, "running")
        update_task_status(sub1, "done")

        # 查看進度
        progress = get_task_progress(task_id)
        assert isinstance(progress, dict)
        assert 'percentage' in progress or 'subtasks' in progress

    def test_memory_store_and_retrieve(self, mock_db_path):
        """
        記憶存取流程：
        store → search → retrieve
        """
        from servers.memory import store_memory, search_memory

        # 存記憶
        content = "This is a test pattern for authentication"
        mem_id = store_memory(
            category="pattern",
            content=content,
            title="Auth Pattern",
            project="test"
        )
        assert mem_id is not None

        # 搜尋
        results = search_memory("authentication pattern", project="test", limit=5)
        assert isinstance(results, list)

        # 應該找到剛存的記憶
        if results:
            found_contents = [r.get('content', '') for r in results]
            assert any('authentication' in c.lower() for c in found_contents)


# =============================================================================
# Data Flow Tests
# =============================================================================

class TestDataFlow:
    """資料流動測試"""

    def test_ssot_to_graph_sync(self, mock_db_path):
        """SSOT 同步到 Graph"""
        from servers.graph import add_node, list_nodes

        # 模擬 SSOT 數據同步 - add_node(node_id, project, kind, name, ref=None)
        add_node("flow.payment", "test", "flow", "Payment Flow")
        add_node("api.charge", "test", "api", "Charge API")

        nodes = list_nodes("test")
        node_ids = [n['id'] for n in nodes]

        assert "flow.payment" in node_ids
        assert "api.charge" in node_ids

    def test_code_graph_to_validation(self, sample_graph_data, sample_code_graph):
        """Code Graph 用於驗證"""
        from servers.code_graph import get_code_nodes
        from servers.facade import validate_with_graph

        # Code Graph 有數據
        code_nodes = get_code_nodes("test", limit=100)
        assert len(code_nodes) > 0

        # 驗證能使用 Code Graph
        validation = validate_with_graph(
            ["src/auth/login.py"],
            {"flow_id": "flow.auth"},
            project_name="test"
        )
        assert isinstance(validation, dict)

    def test_memory_in_context(self, sample_graph_data, sample_memories):
        """記憶包含在 context 中"""
        from servers.facade import get_full_context

        branch = {"flow_id": "flow.auth"}
        context = get_full_context(branch, project_name="test")

        # context 應該包含 memory
        memory = context.get('memory')
        assert memory is not None or 'memory' in context


# =============================================================================
# Cross-Module Tests
# =============================================================================

class TestCrossModule:
    """跨模組測試"""

    def test_graph_and_code_graph_separate(self, sample_graph_data, sample_code_graph):
        """Graph 和 Code Graph 是分開的"""
        from servers.graph import list_nodes as list_project_nodes
        from servers.code_graph import get_code_nodes

        # 兩個不同的查詢
        project_nodes = list_project_nodes("test")
        code_nodes = get_code_nodes("test", limit=100)

        # 應該是不同的數據集
        project_ids = set(n['id'] for n in project_nodes)
        code_ids = set(n['id'] for n in code_nodes)

        # ID 格式應該不同
        # project: flow.xxx, api.xxx
        # code: file.xxx, func.xxx
        assert project_ids != code_ids or (not project_ids and not code_ids)

    def test_drift_uses_both_graphs(self, sample_graph_data, sample_code_graph):
        """Drift 偵測使用兩個 Graph"""
        from servers.drift import detect_all_drifts

        report = detect_all_drifts("test")

        # 應該能執行（即使沒有偏差）
        assert report is not None


# =============================================================================
# Edge Cases Integration
# =============================================================================

class TestIntegrationEdgeCases:
    """整合邊界條件"""

    def test_new_project_workflow(self, mock_db_path):
        """全新專案的工作流"""
        from servers.facade import get_full_context, validate_with_graph
        from servers.tasks import create_task

        project = "brand_new_project"

        # 建立任務
        task_id = create_task(project, "First task")
        assert task_id is not None

        # 查詢 context（應該大部分為空）
        context = get_full_context({}, project_name=project)
        assert isinstance(context, dict)

        # 驗證（應該不會崩潰）
        validation = validate_with_graph([], {}, project_name=project)
        assert isinstance(validation, dict)

    def test_concurrent_operations(self, mock_db_path):
        """模擬併發操作"""
        from servers.tasks import create_task, get_task
        from servers.memory import store_memory, search_memory

        # 快速連續操作
        tasks = []
        for i in range(5):
            t = create_task("test", f"Task {i}")
            tasks.append(t)

        memories = []
        for i in range(5):
            m = store_memory("test", f"Memory content {i}", f"Title {i}", "test")
            memories.append(m)

        # 所有操作應該成功
        assert all(t is not None for t in tasks)
        assert all(m is not None for m in memories)

        # 查詢應該返回結果
        results = search_memory("Memory content", project="test", limit=10)
        assert len(results) >= 1
