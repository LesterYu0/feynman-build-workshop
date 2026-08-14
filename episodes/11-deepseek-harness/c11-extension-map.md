# 扩展点地图：9 个注册点（C11 置顶资产 5/5）

> 想给 dsh 加任何东西，先查这张表找对扩展点。**官方扩展点地图**，按 "你想做什么" 检索。

## 9 个 ctx 注册点

| 你想做什么 | 注册到 | 说明 |
|---|---|---|
| 加模型工具 | `ctx.tools` | 模型可以调的工具，工具 schema 自动加入提示词组装 |
| 加模型提供方 | `ctx.llm` | 模型适配器（OpenAI / Anthropic / 自定义兼容端点） |
| 让某 agent 拥有不同能力集 | agent preset | 服务行需要 `isolate` realm |
| 加 shell 执行 | `ctx.shell` 后端 | 本地后端通过 `ctx.subprocess` spawn 进程 |
| 加持久化终端 | `ctx.terminals` 后端 + `dsh-tool-terminal` | 跨轮次保持的 PTY |
| 加用户命令 | `ctx.commands` | 无需模型轮次即可分派 |
| 加后台工作 | `ctx.jobs` | `job_*` 工具负责收集或停止 |
| 加文件系统访问或策略 | `ctx.fs` 提供方，或监听 `fs/*` 事件 | 本地 / 远程沙箱统一接口 |
| 限制所启动进程 | `ctx.sandbox` 后端 | 消费方在启动进程前包装 argv |

## 6 类事件拦截点

事件 = 扩展点 + 拦截 / 包装机制。4 种分发模式：

| 模式 | 调用方法 | 是否 await | 返回值 | 用途 |
|---|---|:---:|:---:|---|
| `emit` | `ctx.emit('event', args)` | ❌ | ❌ | 广播 / 通知 |
| `waterfall` | `ctx.waterfall('event', ...)` | ❌ | ✅ | **洋葱中间件**，必须 `next()` |
| `parallel` | `ctx.parallel('event', ...)` | ✅ | ❌ | 并行扇出 |
| `serial` | `ctx.serial('event', ...)` | ✅ | ✅ | 按顺序执行 |

### 关键 waterfall 事件（核心骨架）

| 事件 | 监听后能干嘛 | 必须调 next() |
|---|---|:---:|
| `agent/pre-step` | 改写 / 拒绝模型请求的消息 | ✅ |
| `agent/request` | 在请求发出前包装 | ✅ |
| `llm/stream` | 拦截 / 修改流式输出 | ✅ |
| `tools/pre-execute` | 工具调用前包装 / 拒绝 | ✅ |
| `tools/execute` | 工具调用中包装 / 拦截 | ✅ |
| `tools/post-execute` | 工具调用后包装 / 拦截 | ✅ |
| `agent/turn-stopping` | 停止一个轮次 | ❌（serial） |

### 其他事件域

- **会话事件**（持久）：`turn/*` / `step/*` / `user/message` / `assistant/*` / `tool/*` —— 重新加载后仍然存在
- **agent 事件**：`agent/*` —— 携带活跃 Agent（inbox / 步骤 / 状态 / 请求 / 验证 / 续跑）
- **能力事件**：`fs/*` / `tools/*` / `telemetry/*` —— 无需导入循环即可向 seam 附加策略和适配器

---

## 7 个高频操作映射表

| 目标 | 机制 |
|---|---|
| 添加模型提供方 | 在 `ctx.llm` 上注册适配器 |
| 添加面向模型的能力 | 在 `ctx.tools` 上注册；schema 加入提示词组装 |
| 添加 shell 执行 | 注册 `ctx.shell` 后端；本地通过 `ctx.subprocess` spawn |
| 添加持久化终端 | 注册 `ctx.terminals` 后端和 `dsh-tool-terminal` |
| 添加用户命令 | 在 `ctx.commands` 上注册 |
| 添加后台工作 | 在 `ctx.jobs` 上注册 |
| 添加文件系统访问 | 注册 `ctx.fs` 提供方，或监听 `fs/*` 事件 |
| 拦截请求 / 工具 / 轮次 | 用对应 `agent/*` 或 `tools/*` 事件 |
| 添加模型可见上下文 | `agent.inject()`；落到下一次获准请求 |
| 添加 UI 或编辑器集成 | 驱动 `ctx.agents` 并从 `session/event` 渲染 |
| 添加会话标题 | 注册唯一的 `ctx.sessionTitle` 提供方 |
| fork 活跃会话 | `ctx.sessions.fork(source, boundary?, childSessionId?)` |

📖 详见 `docs/architecture.zh.md` 和 `docs/cookbook/extension-cookbook.zh.md`