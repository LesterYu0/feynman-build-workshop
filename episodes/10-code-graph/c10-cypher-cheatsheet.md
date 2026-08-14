# C10 · Cypher 查询速查表 — 代码知识图谱

> 图谱底层是图数据库，15 个 MCP 工具里 `query_graph` 支持 Cypher 风格模式匹配。**收藏这张表，下次直接抄。**

## 4 个高频查询

### 1. 找调用者（谁调用了这个函数）

```cypher
MATCH (caller)-[:CALLS]->(target)
WHERE target.name = 'myFunc'
RETURN caller
```

### 2. 找完整调用链（深度 1-3）

```cypher
MATCH path = (a)-[:CALLS*1..3]->(b)
WHERE a.name = 'entry'
RETURN path
```

### 3. 找死代码（无人调用的函数）

```cypher
MATCH (f:Function)
WHERE NOT (f)<-[:CALLS]-()
RETURN f
```

### 4. 找循环依赖

```cypher
MATCH (a)-[:IMPORTS]->(b)-[:IMPORTS]->(a)
RETURN a, b
```

## 常用边类型

| 边 | 含义 |
|---|---|
| `CALLS` | 调用（语法级） |
| `RESOLVED_CALLS` | 已解析调用（Hybrid LSP 精确到行） |
| `IMPORTS` | 导入依赖 |
| `DATA_FLOWS` | 数据流 |
| `EMITS` | 事件发射 |
| `SIMILAR_TO` | 相似代码 |

## 自然语言 > 手写 Cypher

**大多数时候你不需要手写 Cypher**——直接用自然语言问 AI，它会自动选择合适的 MCP 工具：

```
"这个函数被谁调用了？"
"从入口函数到数据库之间经过了哪些层？"
"这个项目里有哪些死代码？"
"帮我找一下循环依赖。"
```

---

📌 安装步骤见 [`c10-install-cheatsheet.md`](./c10-install-cheatsheet.md) ｜ MCP 配置见 [`c10-mcp-config.md`](./c10-mcp-config.md)