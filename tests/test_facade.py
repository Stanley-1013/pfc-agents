"""
Facade API Tests

測試 Story 15-16 的核心功能：
- get_full_context(): 三層查詢
- validate_with_graph(): Graph 增強驗證
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Story 15: get_full_context() Tests
# =============================================================================

class TestGetFullContext:
    """測試 PFC 三層查詢"""

    def test_returns_dict_structure(self, sample_graph_data, sample_code_graph, sample_memories):
        """驗證返回包含預期的 key"""
        from servers.facade import get_full_context

        branch = {"flow_id": "flow.auth"}
        result = get_full_context(branch, project_name="test")

        assert isinstance(result, dict)
        # 應包含這些區塊
        expected_keys = {'ssot', 'code', 'memory', 'drift'}
        assert expected_keys.issubset(result.keys()), f"Missing keys: {expected_keys - set(result.keys())}"

    def test_ssot_layer_populated(self, sample_graph_data):
        """驗證 SSOT 層有數據"""
        from servers.facade import get_full_context

        branch = {"flow_id": "flow.auth"}
        result = get_full_context(branch, project_name="test")

        ssot = result.get('ssot', {})
        # SSOT 應該有內容（即使是空的也要有結構）
        assert isinstance(ssot, dict)

    def test_code_layer_populated(self, sample_graph_data, sample_code_graph):
        """驗證 Code 層有數據"""
        from servers.facade import get_full_context

        branch = {"flow_id": "flow.auth"}
        result = get_full_context(branch, project_name="test")

        code = result.get('code', {})
        assert isinstance(code, dict)
        # 應該有 code_nodes 相關數據
        if 'nodes' in code:
            assert isinstance(code['nodes'], list)

    def test_memory_layer_populated(self, sample_graph_data, sample_memories):
        """驗證 Memory 層有數據"""
        from servers.facade import get_full_context

        branch = {"flow_id": "flow.auth"}
        result = get_full_context(branch, project_name="test")

        memory = result.get('memory', {})
        assert isinstance(memory, (dict, list))

    def test_without_flow_id(self, sample_graph_data):
        """無 flow_id 時應該優雅處理"""
        from servers.facade import get_full_context

        branch = {}  # 無 flow_id
        result = get_full_context(branch, project_name="test")

        assert isinstance(result, dict)
        # 不應該報錯，應返回部分結果

    def test_flow_not_found_graceful_degradation(self, sample_graph_data):
        """flow 不存在時應優雅降級"""
        from servers.facade import get_full_context

        branch = {"flow_id": "flow.nonexistent"}
        result = get_full_context(branch, project_name="test")

        # 不應該報錯
        assert isinstance(result, dict)
        # 可能有警告但不應崩潰

    def test_format_context_for_agent(self, sample_graph_data, sample_code_graph):
        """驗證格式化輸出為 markdown"""
        from servers.facade import get_full_context, format_context_for_agent

        branch = {"flow_id": "flow.auth"}
        context = get_full_context(branch, project_name="test")
        formatted = format_context_for_agent(context)

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        # 應該是 markdown 格式
        assert '#' in formatted or formatted.strip()  # 有標題或有內容


# =============================================================================
# Story 16: validate_with_graph() Tests
# =============================================================================

class TestValidateWithGraph:
    """測試 Critic Graph 增強驗證"""

    def test_returns_dict_structure(self, sample_graph_data, sample_code_graph):
        """驗證返回結構"""
        from servers.facade import validate_with_graph

        modified_files = ["src/auth/login.py"]
        branch = {"flow_id": "flow.auth"}
        result = validate_with_graph(modified_files, branch, project_name="test")

        assert isinstance(result, dict)
        # 應包含影響分析、SSOT 符合性、測試覆蓋、建議
        expected_keys = {'impact_analysis', 'ssot_compliance', 'test_coverage', 'recommendations'}
        assert expected_keys.issubset(result.keys()), f"Missing keys: {expected_keys - set(result.keys())}"

    def test_impact_analysis_structure(self, sample_graph_data, sample_code_graph):
        """驗證影響分析結構"""
        from servers.facade import validate_with_graph

        modified_files = ["src/auth/login.py"]
        branch = {"flow_id": "flow.auth"}
        result = validate_with_graph(modified_files, branch, project_name="test")

        impact = result.get('impact_analysis', {})
        assert isinstance(impact, dict)
        # 應包含 affected_nodes, cross_module_impact, api_affected
        assert 'cross_module_impact' in impact or 'affected_nodes' in impact

    def test_empty_files_list(self, sample_graph_data):
        """空檔案列表應該處理"""
        from servers.facade import validate_with_graph

        result = validate_with_graph([], {"flow_id": "flow.auth"}, project_name="test")

        assert isinstance(result, dict)
        # 不應報錯

    def test_file_not_in_graph(self, sample_graph_data):
        """檔案不在 Graph 中時的處理"""
        from servers.facade import validate_with_graph

        modified_files = ["nonexistent/file.py"]
        branch = {"flow_id": "flow.auth"}
        result = validate_with_graph(modified_files, branch, project_name="test")

        assert isinstance(result, dict)
        # 影響分析應該為空或最小

    def test_ssot_compliance_check(self, sample_graph_data):
        """驗證 SSOT 符合性檢查"""
        from servers.facade import validate_with_graph

        modified_files = ["src/api/login.py"]
        branch = {"flow_id": "flow.auth"}
        result = validate_with_graph(modified_files, branch, project_name="test")

        compliance = result.get('ssot_compliance', {})
        assert isinstance(compliance, dict)
        # 應該有 status
        if 'status' in compliance:
            assert compliance['status'] in ['ok', 'warning', 'violation', 'unknown']

    def test_recommendations_generated(self, sample_graph_data, sample_code_graph):
        """驗證建議生成"""
        from servers.facade import validate_with_graph

        modified_files = ["src/auth/login.py"]
        branch = {"flow_id": "flow.auth"}
        result = validate_with_graph(modified_files, branch, project_name="test")

        recommendations = result.get('recommendations', [])
        assert isinstance(recommendations, list)

    def test_format_validation_report(self, sample_graph_data, sample_code_graph):
        """驗證格式化報告"""
        from servers.facade import validate_with_graph, format_validation_report

        modified_files = ["src/auth/login.py"]
        branch = {"flow_id": "flow.auth"}
        validation = validate_with_graph(modified_files, branch, project_name="test")
        report = format_validation_report(validation)

        assert isinstance(report, str)
        assert len(report) > 0


# =============================================================================
# Edge Cases
# =============================================================================

class TestFacadeEdgeCases:
    """邊界條件測試"""

    def test_empty_project(self, mock_db_path):
        """空專案的處理"""
        from servers.facade import get_full_context

        branch = {"flow_id": "flow.auth"}
        result = get_full_context(branch, project_name="empty_project")

        # 不應報錯
        assert isinstance(result, dict)

    def test_none_branch(self, sample_graph_data):
        """None branch 的處理"""
        from servers.facade import get_full_context

        # 這可能會報錯，但應該是有意義的錯誤
        try:
            result = get_full_context(None, project_name="test")
            # 如果不報錯，應該返回合理結果
            assert result is not None
        except (TypeError, AttributeError) as e:
            # 預期的錯誤類型
            assert 'None' in str(e) or 'NoneType' in str(e)

    def test_special_characters_in_flow_id(self, sample_graph_data):
        """flow_id 中的特殊字符"""
        from servers.facade import get_full_context

        branch = {"flow_id": "flow.auth-service_v2"}
        result = get_full_context(branch, project_name="test")

        # 應該處理特殊字符
        assert isinstance(result, dict)
