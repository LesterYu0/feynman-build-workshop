# C10 · 安装速查表 — codebase-memory-mcp

> 给你的 AI 编程助手装「代码地图」，5 分钟搞定。

## 一行安装（推荐）

```sh
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
```

- 自动检测并配置 37 个 AI 编程客户端（Claude Code / Cursor / VS Code / Gemini CLI ...）
- 装完**重启你的 AI 编程工具**，然后对它说：`Index this project`
- 大部分项目几秒钟索引完毕

## 三步流程

```
1. 安装（curl | bash）
2. 重启你的 AI 编程助手
3. 说一句：Index this project
```

## 7 种安装方式（按需选用）

| 方式 | 命令 |
|---|---|
| curl 脚本（推荐） | `curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh \| bash` |
| npm | `npm install -g codebase-memory-mcp` |
| pip | `pip install codebase-memory-mcp` |
| Homebrew | `brew install codebase-memory-mcp` |
| cargo | `cargo install codebase-memory-mcp` |
| go | `go install github.com/DeusData/codebase-memory-mcp` |
| 源码 | 见仓库 README |

## 验证安装

```sh
codebase-memory-mcp --version
# 应输出 v0.x.x（纯 C 单文件二进制）
```

## 团队共享

索引产物提交 Git 即可全队复用：

```sh
# .codebase-memory/graph.db.zst 提交到仓库
git add .codebase-memory/graph.db.zst
```

## 反直觉点

- **纯 C 单文件、零依赖**：不装 Node / Python / JVM，一个二进制搞定
- **亚毫秒查询**：图谱查询走本地内存，无网络延迟
- **后台增量更新**：文件监听器自动维护图谱，改代码不用手动重建

---

📌 完整配置见 [`c10-mcp-config.md`](./c10-mcp-config.md) ｜ 查询语法见 [`c10-cypher-cheatsheet.md`](./c10-cypher-cheatsheet.md)