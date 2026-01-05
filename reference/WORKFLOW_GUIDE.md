# Neuromorphic Workflow Guide

詳細的工作流程指南。

## Task Recovery

### New Conversation (Unknown Task ID)

```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/skills/neuromorphic'))
from servers.memory import get_project_context, load_checkpoint

# Auto-detect project, find active tasks
project = os.path.basename(os.getcwd())
context = get_project_context(project)

if context['active_tasks']:
    task = context['active_tasks'][0]
    print(f"Found task: {task['description']} ({task['progress']})")
    # Load detailed state
    checkpoint = load_checkpoint(task['id'])
elif context['suggestion']:
    print(f"Suggestion: {context['suggestion']}")
```

### Known Task ID

```python
from servers.tasks import get_task_progress
from servers.memory import load_checkpoint

progress = get_task_progress('TASK_ID')
print(f"Progress: {progress['progress']} ({progress['percentage']}%)")

checkpoint = load_checkpoint('TASK_ID')
if checkpoint:
    print(f"Resume from: {checkpoint['summary']}")
```

---

## Starting New Tasks

```python
from servers.tasks import create_task, create_subtask

# Create main task
task_id = create_task(
    project="PROJECT_NAME",
    description="Task description",
    priority=8
)

# Decompose into subtasks
subtask_1 = create_subtask(task_id, "Subtask 1", assigned_agent='executor')
subtask_2 = create_subtask(task_id, "Subtask 2", depends_on=[subtask_1])
```

---

## Agent Dispatch Flow

### Complete Execution Cycle

```
PFC (plan) → Executor (do) → Critic (verify) → Memory (store)
     ↑                            │
     └────── REJECTED ────────────┘
```

### Dispatch via Task Tool

#### Executor

```python
Task(
    subagent_type='executor',
    prompt=f'''
TASK_ID = "{task_id}"

Task: [description]
Source: [file path]
Output: [expected output]

Steps:
1. Read source
2. Execute task
3. Verify result
'''
)
# Hook automatically: records agentId + calls finish_task()
```

#### Critic

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
'''
)
# Hook automatically: parses APPROVED/CONDITIONAL/REJECTED + calls finish_validation()
```

---

## Validation Cycle

### Hook Mechanism

```
Main conversation → Task(executor, TASK_ID=xxx)
                         ↓
                   Executor executes
                         ↓
                   Executor ends (outputs result)
                         ↓
              ┌─────────────────────────────┐
              │  PostToolUse Hook triggers  │
              │  • Records agentId          │
              │  • Calls finish_task()      │
              │  • Phase → validation       │
              └─────────────────────────────┘
                         ↓
Main conversation → Task(critic, ORIGINAL_TASK_ID=xxx)
                         ↓
              Critic outputs "Result: APPROVED/CONDITIONAL/REJECTED"
                         ↓
              ┌──────────────────────────────────────────────┐
              │  PostToolUse Hook triggers                   │
              │                                              │
              │  APPROVED:                                   │
              │  • finish_validation(approved=True)          │
              │  • Phase → documentation                     │
              │                                              │
              │  CONDITIONAL:                                │
              │  • finish_validation(approved=True)          │
              │  • Suggestions stored in working_memory      │
              │  • Outputs additionalContext reminder        │
              │                                              │
              │  REJECTED:                                   │
              │  • finish_validation(approved=False)         │
              │  • Phase → execution (retry)                 │
              └──────────────────────────────────────────────┘
```

### Handling CONDITIONAL

When Critic outputs CONDITIONAL:

```python
from servers.memory import get_working_memory

# 1. Read suggestions
suggestions = get_working_memory(original_task_id, 'critic_suggestions')

# 2. Choose how to handle
# a) Fix it yourself
# b) Dispatch new Executor
# c) Ignore (if LOW severity)
```

### Handling REJECTED (Resume Executor)

```python
from servers.tasks import get_task

task = get_task(original_task_id)

if task.get('executor_agent_id'):
    Task(
        subagent_type='executor',
        resume=task['executor_agent_id'],  # Resume original Executor
        prompt=f"""
        Rejected by Critic. Fix based on feedback:
        - Retry #{task.get('retry_count', 1)}
        """
    )
```

### PFC Validation Cycle

```python
from servers.facade import run_validation_cycle

validation = run_validation_cycle(
    parent_id=task_id,
    mode='normal'  # 'normal' | 'batch_approve' | 'batch_skip' | 'sample'
)

# PFC outputs dispatch instructions for main conversation
```

---

## Three-Layer Memory Query

Each Agent auto-queries relevant memory at startup:

| Layer | Query Type | Purpose |
|-------|------------|---------|
| **PFC** | strategy, procedure | Decide task decomposition |
| **Executor** | pattern, lesson | Avoid repeating mistakes |
| **Critic** | pattern, standard | Compare against best practices |

---

## Database Operations

### Task Management

```python
from servers.tasks import (
    create_task,          # Create main task
    create_subtask,       # Create subtask (can specify requires_validation)
    get_task,             # Get task details
    update_task_status,   # Update status
    get_next_task,        # Get next task
    get_task_progress,    # Get progress
    log_agent_action,     # Log action

    # Validation
    get_unvalidated_tasks,  # Get pending validation
    mark_validated,         # Mark validation status
    advance_task_phase,     # Advance phase
    get_validation_summary  # Get validation stats
)

# Status: pending, running, done, failed, blocked
# Validation: pending, approved, rejected, skipped
# Phase: execution, validation, documentation, completed
```

### Memory Management

```python
from servers.memory import (
    search_memory,        # Search long-term memory
    store_memory,         # Store memory
    get_working_memory,   # Read working memory
    set_working_memory,   # Set working memory
    save_checkpoint,      # Save checkpoint
    load_checkpoint,      # Load checkpoint
    add_episode           # Record event
)
```

---

## Micro-Nap Mechanism

When context is too long, trigger Micro-Nap:

```python
from servers.memory import save_checkpoint

state = {
    'task_id': task_id,
    'completed': completed_list,
    'pending': pending_list,
    'current_phase': 'phase_2'
}

save_checkpoint(
    project='PROJECT_NAME',
    task_id=task_id,
    agent='pfc',
    state=state,
    summary='Phase 1 complete, Phase 2 in progress'
)

print(f"""
## Micro-Nap Triggered

Suggest starting new conversation. Resume command: "Continue task {task_id}"
""")
```

---

## Project Initialization SOP

### Step 1: Run Init Script

```bash
python ~/.claude/skills/neuromorphic/scripts/init_project.py <project_name>
```

Creates `.claude/pfc/config.py` and registers project in database.

### Step 2: Create SSOT INDEX

Create `.claude/pfc/INDEX.md` as navigation map:

```yaml
# .claude/pfc/INDEX.md

## Technical Docs

docs:
  - id: doc.prd
    name: Product Requirements
    ref: docs/PRD.md             # Points to existing PRD

  - id: doc.architecture
    name: System Architecture
    ref: docs/ARCHITECTURE.md

## Main Code

code:
  - id: code.main
    name: Main Entry
    ref: src/main.py
```

**Key**: INDEX uses `ref` field to **point to existing docs**, not copy content.

### Step 3: Build Code Graph

```python
from servers.facade import sync

project = os.path.basename(os.getcwd())
result = sync(project)
print(f"Sync complete: {result['nodes_count']} nodes")
```

### Step 4: Import Knowledge to Memory (Optional)

```python
from servers.memory import store_memory

store_memory(
    category='sop',
    content='1. Run tests\n2. Build\n3. Deploy',
    title='Deployment SOP',
    project='my-project',
    importance=8
)
```

---

## Best Practices

1. **Parallel Dispatch** - Use multiple Task tools for independent tasks
2. **Validation Cycle** - Critic validates after each Executor
3. **Store Experience** - Save important discoveries to Memory
4. **DB Updates** - Update status after each task completion
5. **Checkpoint** - Regular saves to prevent context overflow
6. **Drift Check** - Run drift detection before major changes
