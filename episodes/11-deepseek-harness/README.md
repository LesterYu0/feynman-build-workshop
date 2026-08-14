# 造物车间 #11 — DeepSeek Harness：DeepSeek 把自家跑第一的 Agent 引擎开源了

> 5 步跑通 + 10 行代码加第一个插件

📺 视频：待发布 ｜ ⏱ ~13.2 min ｜ 📅 2026-08-14

## 核心结论

**今年七月 DeepSeek 发布 V4-Flash，一夜拿下 9 项 Agent 任务全球第一。官方跑这些测试用的引擎——DeepSeek Harness（`dsh`）——整个开源了。** 它不是又一个 Agent 框架，而是"一切皆插件"的引擎：模型适配器、工具注册表、会话日志，连 agent 循环本身都是插件，**没有特权内核，每一块都能被替换**。

你也能搭出一套和 DeepSeek 官方同款的 Agent 引擎。这期从零把它跑起来，再 10 行代码加第一个插件。

## 七章结构

| 章 | 内容 | 交付物 |
|---|------|--------|
| 1 | Agent 装配的痛苦：5 件杂事（模型/工具/记忆/沙箱/审批） | 问题意识 |
| 2 | 一切皆插件：Cordis 五概念 + 4 种事件分发 | 架构理解 |
| 3 | 配置树：profile / bundle / patch 三层组装 | 架构理解 |
| 4 | 5 步跑起来：npx 一行 → 配模型 → 选工作区 → headless | `c11-commands-cheatsheet.md` |
| 5 | 加第一个插件：10 行 greet 工具 + `--patch` 挂载 | `c11-plugin-template.md` |
| 6 | 实测与避坑：4 个真实坑 | `c11-pitfalls-checklist.md` |
| 7 | 速查表：命令 / 环境变量 / 扩展点地图 | `c11-env-vars.md` + `c11-extension-map.md` |

## 5 个关键认知（速查）

| # | 认知 | 说明 |
|:--|:---|:---|
| 1 | 一切皆插件 | 没有特权内核，注册是副作用、卸载即撤销 |
| 2 | 配置树 = 代码插件树 | profile 定骨架、bundle 加零件、patch 做改装 |
| 3 | 默认模型就是 deepseek-v4-flash | 官方自测引擎 + 默认模型，开箱即用 |
| 4 | headless 无人值守 | 一条命令跑完打印回答退出，适合 CI |
| 5 | 10 行 = 一个工具 | name + inject + ctx.tools.register(defineTool) |

## 5 个文档没写的坑（速查）

| # | 坑 | 解法 |
|:--|:---|:---|
| 1 | Node 版本过低直接装不上 | 需 Node ≥22.19（`EBADENGINE` / engines 报错） |
| 2 | 源码跑必须先 build | `pnpm install` + `pnpm run build`，日常用 npx 一行即可 |
| 3 | Web UI 不选工作区输入框不可用 | 先点「选择工作区」添加启动目录（不是 bug） |
| 4 | headless 没 API key 直接报错 | `DEEPSEEK_API_KEY` 必填，否则 `MISSING_CREDENTIAL` |
| 5 | patch 层级错了配置被覆盖 | profile → home → `--patch` overlay，注意层级 |

> 完整排错见 [`c11-pitfalls-checklist.md`](./c11-pitfalls-checklist.md)

## 资产清单

| 文件 | 用途 | 直接能用 |
|------|------|---------|
| [`c11-commands-cheatsheet.md`](./c11-commands-cheatsheet.md) | 5 条核心命令速查表 | ✅ 抄走执行 |
| [`c11-plugin-template.md`](./c11-plugin-template.md) | 10 行 greet 插件骨架模板 | ✅ 复制改 execute 就能用 |
| [`c11-env-vars.md`](./c11-env-vars.md) | 7 个环境变量清单 | ✅ 对照配置 |
| [`c11-pitfalls-checklist.md`](./c11-pitfalls-checklist.md) | 5 个真实坑排错清单 | ✅ 出问题逐条查 |
| [`c11-extension-map.md`](./c11-extension-map.md) | 9 个 ctx 注册点 + 4 种事件分发 | ✅ 扩展前先查表 |

## 5 分钟快速上手

```bash
# 1. 一键启动 Web UI（无需 Node 以外的依赖）
npx @deepseek-ai/dsh web
# 打开 http://127.0.0.1:3080

# 2. 配置模型：设置 → 模型 → DeepSeek API key（路由立即生效）

# 3. 选择工作区 → 发任务：
#    "Summarize this repository and identify its main packages."

# 4. 无人值守（CI / 批量）：
export DEEPSEEK_API_KEY=sk-your-key-here
npx @deepseek-ai/dsh --profile headless "fix the failing test in this workspace"

# 5. 加第一个插件：按 c11-plugin-template.md 建 scratch-plugin，然后
npx @deepseek-ai/dsh web --patch ./scratch-plugin/cordis.yml
# 在 Web UI 问 "Use the greet tool to greet Ada." → Hello, Ada!
```

## 与 C01-C10 的关系

```
C06 Agent Loop ──┐
C08 多模型路由   ─┼── C11 拿到 DeepSeek 官方生产级引擎的完整架构
C09 Plan 模式    ─┤    （一切皆插件：模型/工具/记忆/沙箱/审批全可换）
C10 代码记忆     ─┘
```

## 关键数据

- 9 项 Agent 榜第一（DeepSeek 官方自测，极简/max/topp0.95/temp1.0）
- 5 步跑通 ｜ 10 行加第一个插件 ｜ 9 个扩展点
- 默认模型 deepseek-v4-flash（与 EP50 呼应）
- 开发者预览 v0.1.0-rc.5：官方明示"未来将出现破坏兼容性的变更"

## 诚实局限

- 9 项 Agent 榜是**官方自测**（无第三方复现），口径要注明
- 开发者预览版：适合学架构 / 跑实验 / 写玩具插件，**生产环境再等等**
- headless / 示例需要 DEEPSEEK_API_KEY（付费 API），注意成本
- Cordis 是 vendor 引入的底层框架（非 DeepSeek 原创，原创是产品化组装）