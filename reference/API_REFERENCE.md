# Neuromorphic Facade API Reference

統一入口，使用者/Agent 只需要這些 API。

## Import

```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/skills/neuromorphic'))

from servers.facade import (
    # Basic operations
    init, sync, status,

    # Three-layer query
    get_full_context, format_context_for_agent,

    # Validation
    validate_with_graph, format_validation_report,

    # Task lifecycle
    finish_task, finish_validation, run_validation_cycle, manual_validate,

    # Drift detection
    check_drift,

    # SSOT sync
    sync_ssot_graph
)
```

---

## Basic Operations

### init(project_path, project_name=None) -> InitResult

初始化專案（首次使用時呼叫）

```python
result = init('/path/to/project', 'my-project')
# {
#   'project_name': 'my-project',
#   'project_path': '/path/to/project',
#   'schema_initialized': True,
#   'types_initialized': (10, 8),
#   'code_graph_synced': True,
#   'sync_result': {...}
# }
```

### sync(project_path=None, project_name=None, incremental=True) -> SyncResult

同步專案 Code Graph（主要 API）
- 自動偵測變更檔案
- 增量更新 Code Graph（或完整重建）

```python
result = sync('/path/to/project', 'my-project')
# {
#   'files_processed': 10,
#   'files_skipped': 5,
#   'nodes_added': 50,
#   'nodes_updated': 10,
#   'edges_added': 80,
#   'duration_ms': 1200,
#   'errors': []
# }
```

### status(project_name=None) -> StatusReport

取得專案狀態總覽

```python
result = status('my-project')
# {
#   'project_name': 'my-project',
#   'code_graph': {
#     'node_count': 150,
#     'edge_count': 300,
#     'file_count': 25,
#     'kinds': {'file': 25, 'function': 80, 'class': 20},
#     'last_sync': '2025-01-05T10:30:00'
#   },
#   'ssot': {
#     'has_doctrine': True,
#     'has_index': True,
#     'flow_count': 5,
#     'domain_count': 3
#   },
#   'registry': {
#     'node_kinds': 10,
#     'edge_kinds': 8
#   },
#   'health': 'ok',
#   'messages': []
# }
```

---

## PFC Three-Layer Query

### get_full_context(branch, project_name=None) -> Dict

取得 Branch 完整三層 context（結構化版本）
- L0: SSOT 層（意圖）- doctrine, flow_spec, related_nodes
- L1: Code Graph 層（現實）- related_files, dependencies
- L2: Memory 層（經驗）- 相關記憶
- Drift: 偏差檢測

**Args:**
- `branch`: `{'flow_id': 'flow.auth', 'domain_ids': ['domain.user']}`

```python
ctx = get_full_context({'flow_id': 'flow.auth'}, project_name='my-project')
# {
#   'branch': {'flow_id': 'flow.auth', 'domain_ids': ['domain.user']},
#   'ssot': {
#     'doctrine': {...},
#     'flow_spec': {...},
#     'related_nodes': [...]
#   },
#   'code': {
#     'related_files': [...],
#     'dependencies': [...]
#   },
#   'memory': [...],
#   'drift': {'has_drift': False, 'drifts': []}
# }
```

### format_context_for_agent(context) -> str

將 get_full_context 結果格式化為 Agent 可讀的 Markdown

```python
formatted = format_context_for_agent(context)
print(formatted)  # Markdown string
```

---

## Critic Enhanced Validation

### validate_with_graph(modified_files, branch, project_name=None) -> Dict

使用 Graph 做增強驗證
- 修改影響分析
- SSOT 符合性檢查
- 測試覆蓋檢查

**Args:**
- `modified_files`: `['src/api/auth.py', 'src/models/user.py']`
- `branch`: `{'flow_id': 'flow.auth'}`

```python
validation = validate_with_graph(
    modified_files=['src/api/auth.py'],
    branch={'flow_id': 'flow.auth'},
    project_name='my-project'
)
# {
#   'impact_analysis': {
#     'direct_dependents': [...],
#     'indirect_dependents': [...],
#     'risk_level': 'medium'
#   },
#   'ssot_compliance': {
#     'compliant': True,
#     'violations': []
#   },
#   'test_coverage': {
#     'covered': True,
#     'missing_tests': []
#   },
#   'recommendations': ['Consider updating auth.md spec']
# }
```

### format_validation_report(validation) -> str

將 validate_with_graph 結果格式化為 Markdown 報告

---

## Task Lifecycle Management

### finish_task(task_id, success, result=None, error=None, skip_validation=False) -> Dict

Executor 結束任務時必須呼叫
- 自動更新 status, phase
- 回傳 next_action 建議

```python
result = finish_task(task_id, success=True, result='完成')
# {
#   'status': 'done',
#   'phase': 'validation',
#   'next_action': 'await_validation'
# }
```

### finish_validation(task_id, original_task_id, approved, issues=None, suggestions=None) -> Dict

Critic 結束驗證時必須呼叫
- 自動更新驗證狀態
- rejected 時回傳 resume 指令

```python
result = finish_validation(
    critic_id,
    original_task_id,
    approved=False,
    issues=['覆蓋率不足']
)
# {
#   'status': 'rejected',
#   'next_action': 'resume_executor',
#   'resume_agent_id': 'xxx'
# }
```

### run_validation_cycle(parent_id, mode='normal', sample_count=3) -> Dict

PFC 執行驗證循環
- mode: `'normal'` | `'batch_approve'` | `'batch_skip'` | `'sample'`

```python
result = run_validation_cycle(
    parent_id=task_id,
    mode='sample',
    sample_count=3
)
# {
#   'total': 10,
#   'pending_validation': ['task1', 'task2', 'task3'],
#   'approved': 5,
#   'message': 'Sampling 3 of 10 tasks'
# }
```

| Mode | Description |
|------|-------------|
| `normal` | 每個任務派發 Critic |
| `batch_approve` | 全部標記 approved |
| `batch_skip` | 全部標記 skipped |
| `sample` | 只驗證前 N 個 |

### manual_validate(task_id, status, reviewer) -> Dict

人類手動驗證（繞過 Critic）

```python
manual_validate(
    task_id=TASK_ID,
    status='approved',  # 'approved' | 'rejected' | 'skipped'
    reviewer='human:alice'
)
```

---

## Drift Detection

### check_drift(project_name, flow_id=None) -> DriftReport

檢查 SSOT vs Code 偏差

```python
report = check_drift('my-project', 'flow.auth')
# {
#   'has_drift': True,
#   'drifts': [
#     {
#       'type': 'missing_implementation',
#       'description': 'SSOT defines refreshToken but not found in code',
#       'ssot_node': 'flow.auth.refreshToken',
#       'severity': 'high'
#     }
#   ]
# }
```

**Drift Types:**
- `missing_implementation`: SSOT 有定義但程式碼沒實作
- `missing_spec`: 程式碼有實作但 SSOT 沒記載
- `mismatch`: 兩者定義不一致

---

## SSOT Graph Sync

### sync_ssot_graph(project_name=None) -> SyncResult

同步 SSOT Index 到 project_nodes/project_edges
- 從 PROJECT_INDEX.md 解析所有節點
- 建立節點和關係到 Graph
- 動態支援任何類型（不寫死）

```python
result = sync_ssot_graph('my-project')
# {
#   'nodes_added': 15,
#   'edges_added': 20,
#   'types_found': ['flows', 'domains', 'docs']
# }
```

---

## Error Classes

```python
from servers.facade import (
    FacadeError,           # 基類
    ProjectNotFoundError,  # 專案路徑不存在
    NotInitializedError,   # 系統未初始化
    CodeGraphEmptyError    # Code Graph 為空
)
```

All errors include actionable messages telling users how to fix the issue.
