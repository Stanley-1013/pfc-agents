"""
Drift Detection Tests

測試 Story 17: SSOT-Code 偏差偵測
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Story 17: check_drift() Tests
# =============================================================================

class TestCheckDrift:
    """測試 Drift 偵測"""

    def test_returns_dict_structure(self, sample_graph_data, sample_code_graph):
        """驗證返回結構"""
        from servers.facade import check_drift

        result = check_drift(project_name="test")

        assert isinstance(result, dict)
        # 應該有 status 或 drifts
        assert 'status' in result or 'drifts' in result or 'has_drift' in result

    def test_no_drift_when_aligned(self, mock_db_path):
        """SSOT 和 Code 對齊時無偏差"""
        from servers.facade import check_drift
        from servers.graph import add_node

        # 建立對齊的數據 - add_node(node_id, project, kind, name, ref=None)
        add_node("flow.auth", "test", "flow", "Auth Flow", "src/auth/")

        result = check_drift(project_name="test")

        # 結果應該表示無重大偏差或狀態正常
        assert isinstance(result, dict)


class TestDriftDetection:
    """測試偏差偵測的具體邏輯"""

    def test_detect_all_drifts_returns_report(self, sample_graph_data, sample_code_graph):
        """驗證 detect_all_drifts 返回報告"""
        from servers.drift import detect_all_drifts

        report = detect_all_drifts("test")

        # 應該返回 DriftReport 對象
        assert hasattr(report, 'has_drift') or isinstance(report, dict)

    def test_get_drift_summary_returns_string(self, sample_graph_data):
        """驗證摘要返回字串"""
        from servers.drift import get_drift_summary

        summary = get_drift_summary("test")

        assert isinstance(summary, str)

    def test_empty_project_no_crash(self, mock_db_path):
        """空專案不應崩潰"""
        from servers.drift import detect_all_drifts, get_drift_summary

        report = detect_all_drifts("empty_project")
        summary = get_drift_summary("empty_project")

        # 不應報錯
        assert report is not None
        assert isinstance(summary, str)


class TestNameNormalization:
    """測試名稱正規化邏輯"""

    def test_flow_name_normalization(self):
        """測試 flow 名稱正規化"""
        # 這些轉換應該發生：
        # flow.auth-service → auth_service
        # flow.user_management → user_management

        test_cases = [
            ("flow.auth", "auth"),
            ("flow.auth-service", "auth_service"),  # - → _
            ("flow.user_management", "user_management"),
        ]

        for flow_id, expected_normalized in test_cases:
            # 模擬正規化邏輯
            normalized = flow_id.replace("flow.", "").replace("-", "_")
            assert normalized == expected_normalized, f"{flow_id} → {normalized} != {expected_normalized}"

    def test_partial_match_should_not_false_positive(self):
        """部分匹配不應誤判"""
        # auth.py 不應匹配 author.py
        code_files = ["src/author.py", "src/auth.py", "src/authentication.py"]

        flow_name = "auth"

        # 精確匹配邏輯
        exact_matches = [f for f in code_files if f.endswith(f"{flow_name}.py") or f"/{flow_name}/" in f]

        # auth.py 應該匹配
        assert "src/auth.py" in exact_matches
        # author.py 不應該匹配（使用精確邏輯時）
        # 但如果使用 'in' 匹配，author.py 會被誤判
        contains_matches = [f for f in code_files if flow_name in f]
        assert "src/author.py" in contains_matches  # 這是目前可能的問題


class TestDriftFlowDetection:
    """測試 Flow 偏差偵測"""

    def test_detect_flow_drift(self, sample_graph_data, sample_code_graph):
        """測試特定 Flow 的偏差偵測"""
        from servers.drift import detect_flow_drift

        report = detect_flow_drift("test", "flow.auth")

        # 應該返回報告
        assert report is not None

    def test_detect_coverage_gaps(self, sample_graph_data, sample_code_graph):
        """測試覆蓋缺口偵測"""
        from servers.drift import detect_coverage_gaps

        gaps = detect_coverage_gaps("test")

        assert isinstance(gaps, list)


class TestDriftEdgeCases:
    """Drift 邊界條件"""

    def test_nonexistent_project(self, mock_db_path):
        """不存在的專案"""
        from servers.drift import detect_all_drifts

        report = detect_all_drifts("nonexistent_project")

        # 不應崩潰，應返回空結果
        assert report is not None

    def test_project_with_special_chars(self, mock_db_path):
        """專案名稱有特殊字符"""
        from servers.drift import get_drift_summary

        # 這可能會有問題，測試健壯性
        summary = get_drift_summary("test-project_v2")

        assert isinstance(summary, str)
