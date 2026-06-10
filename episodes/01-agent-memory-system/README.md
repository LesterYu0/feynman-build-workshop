# 01 · Agent 记忆系统

> **7步设计Agent记忆系统：从LLM先天失忆到生产级上下文管理**

📺 [B站视频](https://www.bilibili.com/video/BV1uiEM6xE9s/) | ⏱ 17:41 | 📅 2026-06-08

---

## 你会得到什么

本期交付 4 份可直接上手的资产，帮你把一个裸奔的 Agent 改造成具备多层记忆的生产级系统：

| # | 资产 | 类型 | 用途 |
|:--:|------|:---:|------|
| 1 | [三分类记忆工作表](./worksheet-memory-classification.md) | 📝 工作表 | 搞清楚 Agent 该记什么、不该记什么 |
| 2 | [Python 代码骨架](./code-agent-memory-core.py) | 🐍 代码 | SQLite FTS5 + 时间戳 + Frozen Snapshot，改三个配置接入 |
| 3 | [七步架构决策树](./decision-tree-architecture.md) | 🌲 决策树 | 做技术决策时逐项对照，每个岔路口都有标注 |
| 4 | [五个压测检查清单](./testcases-verification.md) | ✅ 检查清单 | 每加一层跑一次，六个维度全覆盖 |

---

## 5 分钟快速上手

```
步骤                              时间     产物
─────────────────────────────────────────────────
1. 打开三分类工作表，填空30分钟   30min    搞清楚你的 Agent 产生哪些信息
2. 复制代码骨架，改3个配置        10min    接入你的 Agent  
3. 边改边对照决策树              持续     别走弯路
4. 每加一层跑压测清单            每层5min 验证不退化
```

### 最简接入

```python
# 1. 复制 code-agent-memory-core.py 到项目
# 2. 改这三个配置：
MEMORY_DB_PATH = "/your/path/memory.db"
AGENT_NAME = "my_agent"
SESSION_ID = "session_001"

# 3. 初始化并写入记忆
from agent_memory_core import MemoryManager
mm = MemoryManager(MEMORY_DB_PATH)
mm.store("session_001", "user_prefers_dark_mode", "system", 7)
mm.store("session_001", "fixed_null_pointer_in_auth", "fix", 30)

# 4. 搜索记忆
results = mm.search("dark mode")
```

---

## 架构全景

```
┌─────────────────────────────────────────────┐
│              Agent 记忆系统 4层架构            │
├─────────────────────────────────────────────┤
│ Layer 4: 知识图谱 (Neo4j)                    │
│   └─ 按需接入，< 10 万条不用加                 │
├─────────────────────────────────────────────┤
│ Layer 3: 向量库 (ChromaDB/Qdrant)            │
│   └─ 语义搜索，配合 FTS5 做混合召回            │
├─────────────────────────────────────────────┤
│ Layer 2: Frozen Snapshot (前缀缓存保护)      │
│   └─ 锁定 3 天内不变动的记忆，防 Token 账单爆炸 │
├─────────────────────────────────────────────┤
│ Layer 1: SQLite + FTS5 + 时间戳              │
│   └─ 全文搜索 + 时效衰减 + 归纳脚本           │
└─────────────────────────────────────────────┘
```

---

## 关键决策速查

| 你的情况 | 用这个 | 别用那个 |
|:---|:---|:---|
| 记忆量 < 10 万条 | FTS5 | 向量库（过度设计）|
| 需要精确关键词搜索 | FTS5 | 向量库（语义不准） |
| 记忆需要过期 | 时间戳字段 + 归纳脚本 | 手动清理 |
| Prefix Cache 总失效 | Frozen Snapshot | 频繁更新 System Prompt |
| 需要按主题归纳 | 定时归纳脚本 | 实时归纳（太慢）|

---

## 社区

- 有问题？去 [B站视频评论区](https://www.bilibili.com/video/BV1uiEM6xE9s/) 聊
- 改进了代码？欢迎提 [PR](../../CONTRIBUTING.md)
- 踩了坑想分享？Issues 区见
