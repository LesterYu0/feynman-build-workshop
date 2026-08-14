# C10 · MCP 配置速查 — codebase-memory-mcp

> 手动配置 MCP 服务器的标准 JSON 模板。

## 通用 MCP 配置 JSON

```json
{
  "mcpServers": {
    "codebase-memory-mcp": {
      "command": "npx",
      "args": ["-y", "codebase-memory-mcp"]
    }
  }
}
```

## 常用客户端配置位置

| 客户端 | 配置文件 |
|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code | `~/.claude.json` / 项目 `.mcp.json` |
| Cursor | 设置 → MCP → Add new MCP server |
| VS Code (Copilot) | 设置 → MCP Servers |
| Cline / Roo Code | 各自设置面板 → MCP |

## 手动给 Claude Code 加（示例）

```json
// .mcp.json（项目根目录）
{
  "mcpServers": {
    "codebase-memory-mcp": {
      "command": "npx",
      "args": ["-y", "codebase-memory-mcp"]
    }
  }
}
```

## 团队共享配置

- 索引产物：`.codebase-memory/graph.db.zst`（提交 Git）
- 每个成员 clone 后无需重新索引，直接用共享图谱

## 验证 MCP 已生效

在 AI 客户端里问一句：

```
你有哪些工具？列出所有以 search_graph / trace_path / get_architecture 开头的。
```

能看到这 3 个工具（及其余 12 个），说明 MCP 已接通。

---

📌 安装步骤见 [`c10-install-cheatsheet.md`](./c10-install-cheatsheet.md) ｜ 查询语法见 [`c10-cypher-cheatsheet.md`](./c10-cypher-cheatsheet.md)