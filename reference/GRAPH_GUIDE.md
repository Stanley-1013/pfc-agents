# Graph Operations Guide

Graph 操作詳細指南。

## Overview

Neuromorphic uses two graph layers:

| Layer | Purpose | Tables |
|-------|---------|--------|
| **SSOT Graph** | Intent (what SHOULD be) | project_nodes, project_edges |
| **Code Graph** | Reality (what IS) | code_nodes, code_edges |

---

## Import

```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/skills/neuromorphic'))

# Facade (recommended)
from servers.facade import sync, sync_ssot_graph, check_drift

# Low-level (if needed)
from servers.graph import (
    add_node, add_edge,
    get_neighbors, get_impact,
    list_nodes
)
from servers.code_graph import (
    sync_from_directory,
    get_code_nodes, get_code_edges
)
```

---

## Code Graph Sync

### Sync Project

```python
from servers.facade import sync

result = sync(
    project_path='/path/to/project',
    project_name='my-project',
    incremental=True  # Only process changed files
)

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

### Incremental vs Full

| Mode | When to Use |
|------|-------------|
| `incremental=True` | Normal development, git pull |
| `incremental=False` | First sync, major restructure |

### Supported Languages

- TypeScript / JavaScript
- Python
- Go

### Node Types (Code Graph)

| Kind | Description |
|------|-------------|
| `file` | Source file |
| `class` | Class definition |
| `function` | Function definition |
| `interface` | Interface/Protocol |
| `variable` | Module-level variable |
| `import` | Import statement |

### Edge Types (Code Graph)

| Kind | Description |
|------|-------------|
| `imports` | File imports another |
| `calls` | Function calls function |
| `extends` | Class extends class |
| `implements` | Class implements interface |
| `contains` | File contains class/function |

---

## SSOT Graph Sync

### Sync from INDEX.md

```python
from servers.facade import sync_ssot_graph

result = sync_ssot_graph('my-project')

# {
#   'nodes_added': 15,
#   'edges_added': 20,
#   'types_found': ['flows', 'domains', 'docs']
# }
```

### INDEX.md Format

```yaml
## Flows

flows:
  - id: flow.auth
    name: Authentication Flow
    ref: docs/flows/auth.md
    required: true              # PFC must read this

  - id: flow.payment
    name: Payment Flow
    ref: docs/flows/payment.md

## Domains

domains:
  - id: domain.user
    name: User Domain
    ref: docs/domains/user.md

  - id: domain.order
    name: Order Domain
    ref: docs/domains/order.md

## Dependencies

edges:
  - from: flow.auth
    to: domain.user
    kind: uses
```

### Node Types (SSOT Graph)

| Kind | Description |
|------|-------------|
| `flow` | Business flow |
| `domain` | Domain model |
| `doc` | Documentation |
| `api` | API endpoint |
| `component` | UI component |

---

## Graph Queries

### Get Neighbors

```python
from servers.graph import get_neighbors

neighbors = get_neighbors(
    node_id='flow.auth',
    project='my-project',
    depth=2  # How many hops
)

# [
#   {'id': 'domain.user', 'kind': 'domain', 'distance': 1},
#   {'id': 'api.login', 'kind': 'api', 'distance': 2}
# ]
```

### Get Impact

Find what depends on a node:

```python
from servers.graph import get_impact

impact = get_impact(
    node_id='api.login',
    project='my-project'
)

# {
#   'direct_dependents': ['flow.auth', 'test.auth'],
#   'indirect_dependents': ['flow.onboarding'],
#   'total': 3
# }
```

### List Nodes

```python
from servers.graph import list_nodes

# All flows
flows = list_nodes('my-project', kind='flow')

# All nodes
all_nodes = list_nodes('my-project')
```

---

## Drift Detection

### Check Drift

```python
from servers.facade import check_drift

report = check_drift('my-project', 'flow.auth')

if report['has_drift']:
    for d in report['drifts']:
        print(f"[{d['type']}] {d['description']}")
        print(f"  SSOT: {d.get('ssot_node')}")
        print(f"  Code: {d.get('code_node')}")
        print(f"  Severity: {d['severity']}")
```

### Drift Types

| Type | Description | Example |
|------|-------------|---------|
| `missing_implementation` | SSOT defines, code missing | Spec has refreshToken, no code |
| `missing_spec` | Code exists, SSOT missing | Code has feature, no doc |
| `mismatch` | Both exist but differ | Different parameter names |

### Drift Severity

| Severity | Meaning |
|----------|---------|
| `critical` | Breaking change, must fix |
| `high` | Important, fix soon |
| `medium` | Should address |
| `low` | Minor inconsistency |

### Conflict Resolution

| Scenario | Action |
|----------|--------|
| SSOT says X, Code does Y | Mark as "implementation drift" → human decision |
| Code has X, SSOT missing | Mark as "undocumented" → add to SSOT |
| SSOT says X, Test fails | Mark as "broken promise" → high priority fix |
| Code + Test match, SSOT differs | SSOT outdated → update SSOT |

---

## Type Registry

### Add Node Kind

```python
from servers.registry import register_node_kind

register_node_kind(
    kind='component',
    display_name='元件',
    description='React/Vue component',
    icon='🧩',
    color='#42A5F5',
    source='user'
)
```

### Add Edge Kind

```python
from servers.registry import register_edge_kind

register_edge_kind(
    kind='renders',
    display_name='渲染',
    description='Component renders component',
    source='user'
)
```

### List Registered Types

```python
from servers.registry import list_node_kinds, list_edge_kinds

node_kinds = list_node_kinds()
edge_kinds = list_edge_kinds()
```

---

## Code Graph Extractor

### Direct Usage

```python
from tools.code_graph_extractor import extract_file

nodes, edges = extract_file('/path/to/file.ts')

for node in nodes:
    print(f"{node['kind']}: {node['name']}")
```

### Supported Extensions

| Extension | Language |
|-----------|----------|
| `.ts`, `.tsx` | TypeScript |
| `.js`, `.jsx` | JavaScript |
| `.py` | Python |
| `.go` | Go |

### Adding Language Support

1. Add to `SUPPORTED_EXTENSIONS` in `extractor.py`
2. Implement `extract_{language}()` method
3. (Optional) Add Tree-sitter grammar for accuracy

---

## Database Schema

### Code Graph Tables

```sql
code_nodes (
    id TEXT PRIMARY KEY,
    project TEXT,
    kind TEXT,      -- file, class, function, etc.
    name TEXT,
    path TEXT,
    metadata JSON,
    created_at, updated_at
)

code_edges (
    id TEXT PRIMARY KEY,
    project TEXT,
    source TEXT,    -- node id
    target TEXT,    -- node id
    kind TEXT,      -- imports, calls, extends, etc.
    metadata JSON,
    created_at
)

file_hashes (
    path TEXT PRIMARY KEY,
    project TEXT,
    hash TEXT,
    updated_at
)
```

### SSOT Graph Tables

```sql
project_nodes (
    id TEXT PRIMARY KEY,
    project TEXT,
    kind TEXT,      -- flow, domain, doc, etc.
    name TEXT,
    ref TEXT,       -- reference to file
    required BOOLEAN,
    metadata JSON,
    created_at, updated_at
)

project_edges (
    id TEXT PRIMARY KEY,
    project TEXT,
    source TEXT,
    target TEXT,
    kind TEXT,      -- uses, depends_on, etc.
    metadata JSON,
    created_at
)
```

---

## Best Practices

1. **Sync after git pull** - Keep Code Graph up to date
2. **Use incremental sync** - Faster for normal development
3. **Check drift regularly** - Before major changes
4. **Keep SSOT updated** - Update specs when code changes
5. **Use required: true** - For critical specs PFC must read
6. **Use ref, not copy** - INDEX points to existing docs
