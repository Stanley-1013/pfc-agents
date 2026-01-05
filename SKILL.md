---
name: neuromorphic
description: |
  Neuroscience-inspired multi-agent task management system for complex multi-step
  tasks. Provides three-layer truth architecture (SSOT + Code Graph + Memory),
  task lifecycle with validation cycles, semantic search, and SSOT-Code drift
  detection. Use when: user requests PFC agent, complex task planning requiring
  decomposition, multi-agent coordination, or mentions neuromorphic system.
allowed-tools: Read, Write, Bash, Glob, Grep, Task
---

# Neuromorphic Multi-Agent System

神經擬態多代理任務管理系統，靈感來自人類前額葉皮質功能。

## Quick Start

### Import System

```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/skills/neuromorphic'))

# Core APIs (facade.py)
from servers.facade import (
    get_full_context,        # 三層查詢
    validate_with_graph,     # Graph 增強驗證
    check_drift,             # SSOT-Code 偏差檢測
    sync,                    # Code Graph 同步
    sync_ssot_graph,         # SSOT Graph 同步
    finish_task,             # 任務結束
    finish_validation,       # 驗證結束
    run_validation_cycle     # 驗證循環
)

# Task management
from servers.tasks import create_task, create_subtask, get_task_progress

# Memory operations
from servers.memory import (
    search_memory_semantic,  # 語義搜尋
    store_memory,            # 儲存記憶
    save_checkpoint,         # Micro-Nap checkpoint
    load_checkpoint          # 恢復 checkpoint
)
```

### Database Location

```
~/.claude/skills/neuromorphic/brain/brain.db
```

---

## When to Use This System

### Use PFC Multi-Agent System

- Complex tasks requiring 3+ steps
- Tasks needing planning, coordination, validation
- When user explicitly requests agents (pfc, executor, critic)
- Tasks requiring SSOT-Code consistency checks
- Long-running tasks needing checkpoint/restore

### Direct Execution (Skip PFC)

- Simple single-step tasks
- Quick fixes, typos, small edits
- Read-only queries
- Tasks with clear, specific instructions

---

## Core Workflow

### Agent Roles

| Agent | subagent_type | Purpose | Tools |
|-------|---------------|---------|-------|
| **PFC** | `pfc` | Task planning, decomposition, coordination | Read, Write, Bash |
| **Executor** | `executor` | Single task execution, code writing | Read, Write, Bash |
| **Critic** | `critic` | Result validation, Graph-enhanced review | Read, Grep |
| **Memory** | `memory` | Knowledge storage and retrieval | Read, Bash |
| **Researcher** | `researcher` | Deep research, information gathering | WebSearch, Read |
| **Drift Detector** | `drift-detector` | SSOT-Code drift detection | Read, Bash |

### Execution Flow

```
(Optional) Drift Detector
         ↓
PFC (plan) → Executor (do) → Critic (verify) → Memory (store)
                                  ↓
                            REJECTED → Executor (fix) → Critic (re-verify)
```

### 1. Task Planning (PFC)

```python
# Define branch context
branch = {'flow_id': 'flow.auth', 'domain_ids': ['domain.user']}

# Get three-layer context
context = get_full_context(branch, project_name="PROJECT")

# Create task hierarchy
task_id = create_task(
    project="PROJECT",
    description="Task description",
    priority=8
)

subtask_1 = create_subtask(task_id, "Step 1", assigned_agent='executor')
subtask_2 = create_subtask(task_id, "Step 2", depends_on=[subtask_1])
```

### 2. Task Execution (Executor)

Dispatch via Task tool:

```python
Task(
    subagent_type='executor',
    prompt=f'''
TASK_ID = "{subtask_id}"

Task: [description]
Source: [file path]
Output: [expected output]

Steps:
1. Read source
2. Execute task
3. Verify result
'''
)
```

### 3. Validation (Critic)

```python
Task(
    subagent_type='critic',
    prompt=f'''
TASK_ID = "{critic_task_id}"
ORIGINAL_TASK_ID = "{original_task_id}"

Validation target: [file path]

Criteria:
- Coverage >= 80%
- Edge cases covered
- No security issues
'''
)
```

### 4. Store Experience (Memory)

```python
store_memory(
    category='pattern',      # pattern, lesson, procedure, knowledge
    title='Auth Token Refresh Pattern',
    content='When token expires, use refresh token...',
    project='my-project',
    importance=8
)
```

---

## Three-Layer Architecture

| Layer | Purpose | Tables | Query |
|-------|---------|--------|-------|
| **L0: SSOT** | Intent (what SHOULD be) | project_nodes, project_edges | Doctrine, specs |
| **L1: Code Graph** | Reality (what IS) | code_nodes, code_edges | Files, dependencies |
| **L2: Memory** | Evidence (what was LEARNED) | long_term_memory, episodes | Patterns, lessons |

### Three-Layer Query

```python
branch = {'flow_id': 'flow.auth', 'domain_ids': ['domain.user']}
context = get_full_context(branch, project_name="PROJECT")

# context structure:
# {
#   'ssot': {'doctrine': {...}, 'flow_spec': {...}, 'related_nodes': [...]},
#   'code': {'related_files': [...], 'dependencies': [...]},
#   'memory': [...],
#   'drift': {'has_drift': bool, 'drifts': [...]}
# }
```

---

## Key APIs

### Sync Operations

```python
# Sync Code Graph
result = sync('/path/to/project', 'project-name', incremental=True)
# {'files_processed': 10, 'nodes_added': 50, 'duration_ms': 1200}

# Sync SSOT Graph
result = sync_ssot_graph('project-name')
# {'nodes_added': 15, 'edges_added': 20}
```

### Drift Detection

```python
report = check_drift('project-name', 'flow.auth')
if report['has_drift']:
    for d in report['drifts']:
        print(f"[{d['type']}] {d['description']}")
        # Types: missing_implementation, missing_spec, mismatch
```

### Semantic Search

```python
result = search_memory_semantic(
    "authentication pattern",
    limit=5,
    rerank_mode='claude'  # 'fts5_only', 'claude', 'hybrid'
)

if result['mode'] == 'claude_rerank':
    # Agent selects best matches from candidates
    print(result['rerank_prompt'])
```

### Checkpoint (Micro-Nap)

```python
# Save checkpoint before context overflow
save_checkpoint(
    project='PROJECT',
    task_id=task_id,
    agent='pfc',
    state={'completed': [...], 'pending': [...]},
    summary='Phase 1 complete'
)

# Restore in new conversation
checkpoint = load_checkpoint(task_id)
# {'state': {...}, 'summary': '...', 'agent': 'pfc'}
```

---

## Task Recovery

When resuming a task in a new conversation:

```python
from servers.memory import get_project_context, load_checkpoint

# Find active tasks
project = os.path.basename(os.getcwd())
context = get_project_context(project)

if context['active_tasks']:
    task = context['active_tasks'][0]
    checkpoint = load_checkpoint(task['id'])
    print(f"Resuming: {task['description']}")
```

---

## Utility Scripts

```bash
# System diagnostics
python ~/.claude/skills/neuromorphic/scripts/doctor.py

# Graph sync
python ~/.claude/skills/neuromorphic/scripts/sync.py /path/to/project

# Project initialization
python ~/.claude/skills/neuromorphic/scripts/init_project.py <project_name>
```

---

## Reference Documentation

### Architecture & Design
- [ARCHITECTURE.md](reference/ARCHITECTURE.md) - System design principles
- [API_REFERENCE.md](reference/API_REFERENCE.md) - Complete Facade API

### Usage Guides
- [WORKFLOW_GUIDE.md](reference/WORKFLOW_GUIDE.md) - Detailed workflow guide
- [MEMORY_GUIDE.md](reference/MEMORY_GUIDE.md) - Memory operations
- [GRAPH_GUIDE.md](reference/GRAPH_GUIDE.md) - Graph operations
- [TROUBLESHOOTING.md](reference/TROUBLESHOOTING.md) - Common issues

### Agent Definitions
- [reference/agents/pfc.md](reference/agents/pfc.md) - PFC agent
- [reference/agents/executor.md](reference/agents/executor.md) - Executor agent
- [reference/agents/critic.md](reference/agents/critic.md) - Critic agent
- [reference/agents/memory.md](reference/agents/memory.md) - Memory agent
- [reference/agents/researcher.md](reference/agents/researcher.md) - Researcher agent
- [reference/agents/drift-detector.md](reference/agents/drift-detector.md) - Drift Detector agent

---

## Quick Commands

| Command | Action |
|---------|--------|
| 「使用 pfc agent 規劃 {task}」 | Start task planning with PFC |
| 「繼續之前的任務」 | Resume interrupted task |
| 「查看進度 {task_id}」 | Show task progress |
| 「存這個經驗」 | Store learning to memory |
| 「檢查偏差」 | Run drift detection |
