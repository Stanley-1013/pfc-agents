"""
Skill-Code Drift Detection Server
==================================

偵測專案 Skill（意圖層）與 Code Graph（現實層）之間的偏差。

新架構：讀取專案 .claude/skills/<project>/SKILL.md

偏差類型：
1. missing_implementation - Skill 定義了但 Code 沒實作
2. missing_spec - Code 存在但 Skill 沒文檔化
3. mismatch - 兩者都有但內容不一致
4. stale_spec - Skill 文檔過時

設計原則：
- 偵測偏差，但不自動修正
- 偏差需要人類決策
- 提供可行動的建議
"""

import os
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# =============================================================================
# SCHEMA（供 Agent 參考）
# =============================================================================

SCHEMA = """
=== Drift Detection API ===

get_drift_context(project, project_dir) -> Dict
    取得 Drift 偵測所需的 context 資料（供 Drift Agent 使用）
    Args:
        project: 專案名稱（用於 Code Graph 查詢）
        project_dir: 專案目錄路徑（用於讀取專案 Skill）
    Returns: {
        'skill_content': str,       # SKILL.md 完整內容
        'skill_links': {            # parse_skill_links() 結果
            'links': [...],         # 所有連結
            'sections': {...}       # 按 heading 分組
        },
        'code_nodes': [...],        # Code Graph 節點
        'code_files': [...],        # 檔案節點
        'code_stats': {...},        # Code Graph 統計
        'error': str | None
    }

detect_all_drifts(project, project_dir) -> DriftReport
    基本存在性檢查（檔案連結是否有效）
    深入語義分析應由 Drift Agent 執行
    Returns: {
        'has_drift': bool,
        'drift_count': int,
        'drifts': [DriftItem],
        'summary': str,
        'checked_at': datetime
    }

detect_coverage_gaps(project) -> List[CoverageGap]
    偵測測試覆蓋缺口
    Returns: [{
        'node_id': str,
        'node_kind': str,
        'name': str,
        'file_path': str,
        'has_test': bool
    }]

get_drift_summary(project, project_dir) -> str
    取得偏差摘要（Markdown 格式）
"""

# =============================================================================
# Data Models
# =============================================================================

@dataclass
class DriftItem:
    """單一偏差項目"""
    id: str                              # 唯一識別符
    type: str                            # missing_implementation, missing_spec, mismatch, stale_spec
    severity: str                        # critical, high, medium, low
    ssot_item: Optional[str] = None      # SSOT 側的項目
    code_item: Optional[str] = None      # Code 側的項目
    description: str = ""
    suggestion: str = ""                 # 建議的修復方式
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'type': self.type,
            'severity': self.severity,
            'ssot_item': self.ssot_item,
            'code_item': self.code_item,
            'description': self.description,
            'suggestion': self.suggestion,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None
        }


@dataclass
class DriftReport:
    """偏差報告"""
    has_drift: bool = False
    drift_count: int = 0
    drifts: List[DriftItem] = field(default_factory=list)
    summary: str = ""
    checked_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'has_drift': self.has_drift,
            'drift_count': self.drift_count,
            'drifts': [d.to_dict() for d in self.drifts],
            'summary': self.summary,
            'checked_at': self.checked_at.isoformat()
        }


# =============================================================================
# Detection Logic
# =============================================================================

def get_drift_context(project: str, project_dir: str) -> Dict:
    """
    取得 Drift 偵測所需的 context 資料

    供 Drift Agent 使用，不做判斷，只提供資料。
    Agent 負責判斷哪些是真正的 drift。

    Args:
        project: 專案名稱（用於 Code Graph 查詢）
        project_dir: 專案目錄路徑（用於讀取專案 Skill）

    Returns:
        {
            'skill_content': str,           # SKILL.md 完整內容
            'skill_links': {...},           # parse_skill_links() 結果
            'code_nodes': [...],            # Code Graph 節點
            'code_files': [...],            # 檔案節點
            'code_stats': {...},            # Code Graph 統計
            'error': str | None             # 錯誤訊息
        }
    """
    from servers.ssot import parse_skill_links, load_skill, find_skill_dir
    from servers.code_graph import get_code_nodes, get_code_graph_stats

    result = {
        'skill_content': '',
        'skill_links': {'links': [], 'sections': {}},
        'code_nodes': [],
        'code_files': [],
        'code_stats': {'node_count': 0, 'edge_count': 0},
        'error': None
    }

    # 1. 確認專案 Skill 存在
    skill_dir = find_skill_dir(project_dir)
    if not skill_dir:
        result['error'] = f"No Skill found in {project_dir}/.claude/skills/"
        return result

    # 2. 取得 Skill 定義
    try:
        skill_content = load_skill(project_dir)
        if not skill_content:
            result['error'] = "SKILL.md is empty"
            return result

        result['skill_content'] = skill_content
        result['skill_links'] = parse_skill_links(skill_content)
    except Exception as e:
        result['error'] = f"Failed to parse Skill: {str(e)}"
        return result

    # 3. 取得 Code Graph
    try:
        code_nodes = get_code_nodes(project, limit=1000)
        code_stats = get_code_graph_stats(project)

        result['code_nodes'] = code_nodes
        result['code_stats'] = code_stats
        result['code_files'] = [n for n in code_nodes if n['kind'] == 'file']

        if code_stats['node_count'] == 0:
            result['error'] = "Code Graph is empty. Run sync first."
    except Exception as e:
        result['error'] = f"Failed to get Code Graph: {str(e)}"

    return result


def detect_all_drifts(project: str, project_dir: str) -> DriftReport:
    """
    偵測專案所有 Skill-Code 偏差（簡化版）

    此函數提供基本的存在性檢查。
    更深入的語義分析應由 Drift Agent 執行。

    Args:
        project: 專案名稱（用於 Code Graph 查詢）
        project_dir: 專案目錄路徑（用於讀取專案 Skill）
    """
    context = get_drift_context(project, project_dir)

    if context['error']:
        return DriftReport(
            has_drift=False,
            summary=f"Cannot detect drift: {context['error']}"
        )

    drifts = []
    drift_id = 0

    def make_drift_id():
        nonlocal drift_id
        drift_id += 1
        return f"drift-{project}-{drift_id:04d}"

    # 基本檢查：連結指向的檔案是否存在
    from servers.ssot import find_skill_dir
    skill_dir = find_skill_dir(project_dir)

    for link in context['skill_links'].get('links', []):
        path = link.get('path', '')
        if not path:
            continue

        # 檢查檔案是否存在（相對於 skill_dir）
        full_path = os.path.join(skill_dir, path)
        if not os.path.exists(full_path):
            # 也嘗試相對於 project_dir
            alt_path = os.path.join(project_dir, path)
            if not os.path.exists(alt_path):
                drifts.append(DriftItem(
                    id=make_drift_id(),
                    type='missing_file',
                    severity='medium',
                    ssot_item=path,
                    description=f"Link '{link['name']}' points to non-existent file: {path}",
                    suggestion=f"Create the file or update the link in SKILL.md"
                ))

    # 建立報告
    if drifts:
        summary = f"Found {len(drifts)} broken link(s). Run Drift Agent for deeper analysis."
    else:
        summary = "No broken links. Run Drift Agent for semantic drift detection."

    return DriftReport(
        has_drift=len(drifts) > 0,
        drift_count=len(drifts),
        drifts=drifts,
        summary=summary
    )


def detect_flow_drift(project: str, flow_name: str, project_dir: str) -> DriftReport:
    """偵測特定 Flow 的偏差"""
    from servers.ssot import load_flow_spec
    from servers.code_graph import get_code_nodes

    drifts = []
    drift_id = 0

    def make_drift_id():
        nonlocal drift_id
        drift_id += 1
        return f"drift-{project}-{flow_name}-{drift_id:04d}"

    # 1. 取得 Flow Spec
    flow_spec = None
    try:
        flow_spec = load_flow_spec(flow_name, project_dir)
    except:
        pass

    if not flow_spec:
        return DriftReport(
            has_drift=True,
            drift_count=1,
            drifts=[DriftItem(
                id=make_drift_id(),
                type='missing_spec',
                severity='high',
                ssot_item=flow_name,
                description=f"Flow spec for '{flow_name}' not found",
                suggestion=f"Create .claude/skills/<project>/flows/{flow_name}.md"
            )],
            summary=f"Flow '{flow_name}' has no Skill specification"
        )

    # 2. 取得相關 Code
    flow_name_lower = flow_name.lower()
    code_nodes = get_code_nodes(project, limit=500)

    related_code = []
    for node in code_nodes:
        if flow_name_lower in node.get('file_path', '').lower():
            related_code.append(node)
        elif flow_name_lower in node.get('name', '').lower():
            related_code.append(node)

    # 3. 檢查一致性
    # 從 Spec 中提取預期的 API endpoints
    api_pattern = re.compile(r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)', re.IGNORECASE)
    expected_apis = set(api_pattern.findall(flow_spec))

    # 檢查是否有對應的 Code
    if not related_code and expected_apis:
        drifts.append(DriftItem(
            id=make_drift_id(),
            type='missing_implementation',
            severity='high',
            ssot_item=flow_name,
            description=f"Flow '{flow_name}' specifies APIs but no related code found",
            suggestion="Implement the APIs defined in the flow spec"
        ))

    # 4. 檢查測試覆蓋
    has_test = any('test' in n.get('file_path', '').lower() for n in related_code)

    if not has_test:
        drifts.append(DriftItem(
            id=make_drift_id(),
            type='missing_implementation',
            severity='medium',
            ssot_item=flow_name,
            description=f"Flow '{flow_name}' has no test coverage",
            suggestion=f"Create test file for {flow_name}"
        ))

    # 6. 建立報告
    if drifts:
        summary = f"Flow '{flow_name}' has {len(drifts)} drift(s)"
    else:
        summary = f"Flow '{flow_name}' is in sync with code"

    return DriftReport(
        has_drift=len(drifts) > 0,
        drift_count=len(drifts),
        drifts=drifts,
        summary=summary
    )


def detect_coverage_gaps(project: str) -> List[Dict]:
    """
    偵測測試覆蓋缺口

    找出沒有對應測試的重要程式碼。
    """
    from servers.code_graph import get_code_nodes, get_code_edges

    # 取得所有 nodes
    nodes = get_code_nodes(project, limit=1000)
    edges = get_code_edges(project, kind='tests', limit=500)

    # 找出被測試覆蓋的 nodes
    covered_ids = set(e['to_id'] for e in edges)

    # 找出重要但未覆蓋的 nodes
    gaps = []
    important_kinds = {'function', 'class', 'api'}

    for node in nodes:
        if node['kind'] not in important_kinds:
            continue

        # 跳過測試檔案本身
        if 'test' in node.get('file_path', '').lower():
            continue

        # 跳過 private 函式
        if node.get('visibility') == 'private':
            continue

        # 檢查是否有測試
        has_test = node['id'] in covered_ids

        # 也用檔案名稱啟發式檢查
        if not has_test:
            file_path = node.get('file_path', '')
            file_stem = os.path.splitext(os.path.basename(file_path))[0]
            test_patterns = [
                f"{file_stem}.test",
                f"{file_stem}.spec",
                f"test_{file_stem}",
            ]
            for test_node in nodes:
                if test_node['kind'] == 'file' and 'test' in test_node.get('file_path', '').lower():
                    test_file = os.path.basename(test_node.get('file_path', '')).lower()
                    if any(p.lower() in test_file for p in test_patterns):
                        has_test = True
                        break

        if not has_test:
            gaps.append({
                'node_id': node['id'],
                'node_kind': node['kind'],
                'name': node['name'],
                'file_path': node.get('file_path'),
                'line_start': node.get('line_start'),
                'has_test': False
            })

    return gaps


# =============================================================================
# Reporting
# =============================================================================

def get_drift_summary(project: str, project_dir: str = None) -> str:
    """取得偏差摘要（Markdown 格式）

    Args:
        project: 專案名稱
        project_dir: 專案目錄路徑（用於讀取專案級 SSOT）
    """
    report = detect_all_drifts(project, project_dir)

    lines = [
        "# SSOT-Code Drift Report",
        "",
        f"**Project**: {project}",
        f"**Checked at**: {report.checked_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Status**: {'⚠️ Drift detected' if report.has_drift else '✅ In sync'}",
        "",
    ]

    if not report.has_drift:
        lines.append("No drift detected. SSOT and Code are in sync.")
        return "\n".join(lines)

    lines.append(f"## Summary")
    lines.append("")
    lines.append(report.summary)
    lines.append("")

    # 按嚴重程度分組
    by_severity = {'critical': [], 'high': [], 'medium': [], 'low': []}
    for drift in report.drifts:
        by_severity.get(drift.severity, by_severity['medium']).append(drift)

    severity_icons = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🟢'
    }

    for severity in ['critical', 'high', 'medium', 'low']:
        items = by_severity[severity]
        if not items:
            continue

        lines.append(f"## {severity_icons[severity]} {severity.title()} ({len(items)})")
        lines.append("")

        for drift in items:
            lines.append(f"### [{drift.type}] {drift.id}")
            lines.append("")
            lines.append(f"**Description**: {drift.description}")
            if drift.ssot_item:
                lines.append(f"**SSOT**: `{drift.ssot_item}`")
            if drift.code_item:
                lines.append(f"**Code**: `{drift.code_item}`")
            lines.append(f"**Suggestion**: {drift.suggestion}")
            lines.append("")

    return "\n".join(lines)


def get_coverage_summary(project: str) -> str:
    """取得測試覆蓋缺口摘要"""
    gaps = detect_coverage_gaps(project)

    lines = [
        "# Test Coverage Gaps",
        "",
        f"**Project**: {project}",
        f"**Gaps found**: {len(gaps)}",
        "",
    ]

    if not gaps:
        lines.append("All important code has test coverage. ✅")
        return "\n".join(lines)

    lines.append("## Uncovered Code")
    lines.append("")
    lines.append("| Kind | Name | File | Line |")
    lines.append("|------|------|------|------|")

    for gap in gaps[:50]:  # 限制顯示數量
        lines.append(
            f"| {gap['node_kind']} | `{gap['name']}` | {gap['file_path']} | {gap['line_start']} |"
        )

    if len(gaps) > 50:
        lines.append(f"\n... and {len(gaps) - 50} more")

    return "\n".join(lines)
