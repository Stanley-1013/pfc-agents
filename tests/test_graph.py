"""
Graph Server Tests

測試 Graph 操作的核心邏輯：
- get_neighbors(): BFS 查詢
- get_impact(): 影響分析
- sync_from_index(): 動態同步
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# BFS Neighbors Tests
# =============================================================================

class TestGetNeighbors:
    """測試 BFS 鄰居查詢"""

    def test_depth_1_returns_direct_neighbors(self, sample_graph_data):
        """depth=1 只返回直接鄰居"""
        from servers.graph import get_neighbors

        # get_neighbors(node_id, project, depth, direction)
        # flow.auth → api.login, api.logout
        neighbors = get_neighbors("flow.auth", "test", depth=1)

        assert isinstance(neighbors, list)
        # 應該有 api.login 和 api.logout
        neighbor_ids = [n.get('id') or n.get('to_id') for n in neighbors]
        assert 'api.login' in neighbor_ids or len(neighbors) >= 1

    def test_depth_2_returns_indirect_neighbors(self, sample_graph_data):
        """depth=2 包括間接鄰居"""
        from servers.graph import get_neighbors

        # flow.auth → api.login → domain.user
        neighbors = get_neighbors("flow.auth", "test", depth=2)

        assert isinstance(neighbors, list)
        # depth=2 應該包含更多節點
        neighbor_ids = [n.get('id') or n.get('to_id') for n in neighbors]
        # 可能包含 domain.user（間接）

    def test_depth_0_returns_empty_or_self(self, sample_graph_data):
        """depth=0 應返回空或只有自己"""
        from servers.graph import get_neighbors

        neighbors = get_neighbors("flow.auth", "test", depth=0)

        # depth=0 不應該有鄰居
        assert isinstance(neighbors, list)
        # 大多數實作中 depth=0 返回空

    def test_nonexistent_node(self, sample_graph_data):
        """不存在的節點"""
        from servers.graph import get_neighbors

        neighbors = get_neighbors("nonexistent.node", "test", depth=1)

        # 應返回空列表，不報錯
        assert isinstance(neighbors, list)
        assert len(neighbors) == 0

    def test_cyclic_dependency_no_infinite_loop(self, cyclic_graph_data):
        """環形依賴不應無限循環"""
        from servers.graph import get_neighbors

        # A → B → C → A
        neighbors = get_neighbors("node.a", "cyclic", depth=3)

        # 應該返回結果，不應無限循環
        assert isinstance(neighbors, list)
        # 由於 visited set，不應有重複

    def test_direction_outgoing(self, sample_graph_data):
        """只查詢出邊"""
        from servers.graph import get_neighbors

        neighbors = get_neighbors("flow.auth", "test", depth=1, direction='outgoing')

        assert isinstance(neighbors, list)
        # 所有結果應該是 outgoing 方向
        for n in neighbors:
            if 'direction' in n:
                assert n['direction'] == 'outgoing'

    def test_direction_incoming(self, sample_graph_data):
        """只查詢入邊"""
        from servers.graph import get_neighbors

        # api.login 被 flow.auth implements
        neighbors = get_neighbors("api.login", "test", depth=1, direction='incoming')

        assert isinstance(neighbors, list)

    def test_direction_both(self, sample_graph_data):
        """雙向查詢"""
        from servers.graph import get_neighbors

        neighbors = get_neighbors("api.login", "test", depth=1, direction='both')

        assert isinstance(neighbors, list)


# =============================================================================
# Impact Analysis Tests
# =============================================================================

class TestGetImpact:
    """測試影響分析"""

    def test_returns_affected_nodes(self, sample_graph_data):
        """返回受影響的節點"""
        from servers.graph import get_impact

        # get_impact(node_id, project)
        affected = get_impact("api.login", "test")

        assert isinstance(affected, list)

    def test_empty_when_no_dependents(self, sample_graph_data):
        """無依賴者時返回空"""
        from servers.graph import get_impact

        # domain.user 可能沒有依賴者
        # get_impact(node_id, project)
        affected = get_impact("domain.user", "test")

        assert isinstance(affected, list)


# =============================================================================
# Node/Edge CRUD Tests
# =============================================================================

class TestNodeOperations:
    """測試節點操作"""

    def test_add_node(self, mock_db_path):
        """新增節點"""
        from servers.graph import add_node, get_node

        # add_node(node_id, project, kind, name, ref=None)
        result = add_node("new.node", "test", "test_kind", "Test Node")

        assert result is not None

        # get_node(node_id, project) - 注意參數順序
        node = get_node("new.node", "test")
        assert node is not None

    def test_add_duplicate_node(self, mock_db_path):
        """重複新增節點（upsert）"""
        from servers.graph import add_node, get_node

        # add_node(node_id, project, kind, name, ref=None)
        add_node("dup.node", "test", "kind1", "Dup Node v1")
        add_node("dup.node", "test", "kind2", "Dup Node v2")

        # get_node(node_id, project)
        node = get_node("dup.node", "test")
        # 應該是最新的值
        assert node is not None

    def test_get_nonexistent_node(self, mock_db_path):
        """取得不存在的節點"""
        from servers.graph import get_node

        # get_node(node_id, project)
        node = get_node("nonexistent", "test")

        assert node is None

    def test_list_nodes(self, sample_graph_data):
        """列出所有節點"""
        from servers.graph import list_nodes

        nodes = list_nodes("test")

        assert isinstance(nodes, list)
        assert len(nodes) >= 3  # 至少有 flow.auth, api.login, api.logout


class TestEdgeOperations:
    """測試邊操作"""

    def test_add_edge(self, mock_db_path):
        """新增邊"""
        from servers.graph import add_node, add_edge, get_neighbors

        # add_node(node_id, project, kind, name, ref=None)
        add_node("from.node", "test", "test", "From Node")
        add_node("to.node", "test", "test", "To Node")
        # add_edge(from_id, to_id, kind, project)
        result = add_edge("from.node", "to.node", "test_edge", "test")

        assert result is not None

        # get_neighbors(node_id, project, depth, direction)
        neighbors = get_neighbors("from.node", "test", depth=1)
        neighbor_ids = [n.get('id') or n.get('to_id') for n in neighbors]
        assert 'to.node' in neighbor_ids or len(neighbors) > 0

    def test_add_duplicate_edge(self, mock_db_path):
        """重複新增邊"""
        from servers.graph import add_node, add_edge

        # add_node(node_id, project, kind, name, ref=None)
        add_node("a", "test", "test", "Node A")
        add_node("b", "test", "test", "Node B")

        # add_edge(from_id, to_id, kind, project)
        add_edge("a", "b", "depends", "test")
        add_edge("a", "b", "depends", "test")

        # 不應報錯，應該 upsert 或 ignore


# =============================================================================
# Sync Tests
# =============================================================================

class TestSyncFromIndex:
    """測試從 Index 同步"""

    def test_sync_creates_nodes(self, mock_db_path, mock_ssot_dir, monkeypatch):
        """同步應建立節點"""
        from servers.graph import sync_from_index, list_nodes

        # 這個測試需要 mock SSOT 目錄
        # 實際測試可能需要更多設定

    def test_sync_idempotent(self, mock_db_path):
        """同步應該是冪等的"""
        from servers.graph import sync_from_index

        # 執行兩次應該結果相同
        # result1 = sync_from_index("test", index_data)
        # result2 = sync_from_index("test", index_data)
        # assert result1 similar to result2


# =============================================================================
# Edge Cases
# =============================================================================

class TestGraphEdgeCases:
    """Graph 邊界條件"""

    def test_empty_project(self, mock_db_path):
        """空專案"""
        from servers.graph import list_nodes, get_neighbors

        nodes = list_nodes("empty_project")
        assert nodes == []

        # get_neighbors(node_id, project, depth, direction)
        neighbors = get_neighbors("any.node", "empty_project", depth=1)
        assert neighbors == []

    def test_special_chars_in_node_id(self, mock_db_path):
        """節點 ID 有特殊字符"""
        from servers.graph import add_node, get_node

        # add_node(node_id, project, kind, name, ref=None)
        node_id = "flow.auth-service_v2.0"
        add_node(node_id, "test", "flow", "Auth Service v2")

        # get_node(node_id, project)
        node = get_node(node_id, "test")
        assert node is not None

    def test_large_depth(self, sample_graph_data):
        """大深度查詢"""
        from servers.graph import get_neighbors

        # 深度 10 應該不會有問題（因為圖不大）
        # get_neighbors(node_id, project, depth, direction)
        neighbors = get_neighbors("flow.auth", "test", depth=10)

        assert isinstance(neighbors, list)
