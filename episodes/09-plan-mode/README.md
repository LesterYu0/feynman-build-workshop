# 造物车间 #09 — 6 杠杆造出生产级 Plan 模式

> Agent 先别动手，反而更可控更省 token

📺 视频：待发布 ｜ ⏱ ~15 min ｜ 📅 2026-07-16

## 核心结论

**Agent 翻车就两种姿势：方向错了还疯改十个文件，或者原地绕八圈死活搞不定。** Plan 模式让 Agent 先把计划交出来、你审核放行后它再动手——方向错了在计划阶段就被拦住，副作用被闸门隔离。

关键不是「换更聪明的模型」，而是「换 Agent 的工作流」：Planner（大脑）规划 → 用户/闸门放行 → Executor（双手）执行 → Replanner（纠错脑）盯偏差 → State（记忆）记录全程。

## 六段结构

| 段 | 内容 | 交付物 |
|---|------|--------|
| S0 | 痛点钩子：Agent 翻车两种姿势 | 问题意识 |
| S1 | 问题定义：Plan 模式 = 4 组件 + 2 关键设计 | 知识卡片① |
| S2 | 4 组件拆解：Planner / Executor / Replanner / State | 架构图 |
| S3 | 手写最小实现 + 坑①②：计划文件外化 / 权限闸门 | `plan_mode_minimal.py` |
| S4 | 6 优化杠杆 + 坑③④⑤：Replan 触发 / 死循环 / 成本控制 | `demo_guard.py` |
| S5 | 3 种规划架构选型 + 评测 | `04-selection-table.md` |
| S6 | 收藏引导：抄走 7 件资产 | 资产链接 |

## 6 个优化杠杆（速查）

| # | 杠杆 | 解决什么 |
|:--|:---|:---|
| 1 | 职责分离（Planner / Executor / Replanner / State） | 一个 Agent 啥都干 → 各司其职可替换 |
| 2 | Replan 三级触发（工具失败 / 目标偏离 / 环境变化） | 死磕一个错误方向 |
| 3 | 死循环防护（最大步骤数 / 重复动作检测） | 原地绕八圈 |
| 4 | 成本控制（计划先行省 token / 预算上限） | 烧钱 |
| 5 | 计划质量（外化计划文件，可审计可回滚） | 方向错了疯改十个文件 |
| 6 | 副作用管理（权限闸门：读 / 写 / 执行分级） | 不该动的文件被改了 |

## 5 个文档没写的坑（速查）

| # | 坑 | 解法 |
|:--|:---|:---|
| 1 | 计划存在内存 → 重启丢计划、无法审计 | 计划文件外化（可审计根） |
| 2 | 无权限闸门 → Agent 改到不该动的文件 | 副作用隔离：读 / 写 / 执行分级放行 |
| 3 | Replan 不设触发 → 错方向一路死磕 | 三级触发树：失败 / 偏离 / 环境变化 |
| 4 | 无死循环防护 → 重复动作无限绕 | 最大步骤 + 重复检测 |
| 5 | 计划不可量化 → 好坏全靠感觉 | 3 层评测：推理 / 行动 / 执行层硬指标 |

> 完整触发树见 [`05-replan-trigger-tree.md`](./05-replan-trigger-tree.md)

## 资产清单

| 文件 | 用途 | 直接能用 |
|------|------|---------|
| [`plan_mode_minimal.py`](./plan_mode_minimal.py) | 手写最小 Plan 模式（4 组件 + 2 关键设计） | ✅ 换模型就能跑 |
| [`demo_guard.py`](./demo_guard.py) | 权限闸门对比 demo（有 / 无闸门对照） | ✅ 直接 `python demo_guard.py` |
| [`plan_mode_langgraph.py`](./plan_mode_langgraph.py) | LangGraph 落地版（生产级） | ✅ 按需选用 |
| [`04-selection-table.md`](./04-selection-table.md) | 3 种规划架构选型决策表 | ✅ 对照选择 |
| [`05-replan-trigger-tree.md`](./05-replan-trigger-tree.md) | Replan 三级触发树 | ✅ 抄走接入 |
| [`06-planner-prompt-template.md`](./06-planner-prompt-template.md) | Planner Prompt 模板 | ✅ 直接填 |
| [`07-eval-checklist.md`](./07-eval-checklist.md) | 3 层评测 Checklist + 硬指标 | ✅ 逐项跑 |

## 5 分钟快速上手

```bash
git clone https://github.com/LesterYu0/feynman-build-workshop.git
cd feynman-build-workshop/episodes/09-plan-mode

# 1. 跑最小实现（默认 mock planner，无需 API key）
python plan_mode_minimal.py

# 2. 跑权限闸门对比 demo
python demo_guard.py

# 3. 换你的模型：实现 plan() / execute() 两个函数即可
# 4. 对照 04-selection-table.md 决定是否上 LangGraph 版
# 5. 用 07-eval-checklist.md 逐项评测
```

## 与 C01-C08 的关系

```
C06 Agent Loop ──┐
C08 多模型路由   ─┼── C09 给 Agent 装配「先计划后动手」的纪律
C07 记忆即技能   ─┘    （控制平面：Loop → Plan → 执行）
```

## 关键数据

- 计划先行 vs 直接动手：省 token（方向错了不再烧执行成本）
- 权限闸门：副作用隔离根，生产环境必装
- 3 层评测：推理层 / 行动层 / 执行层 + 硬指标阈值

## 诚实局限

- demo 用 mock planner，真实模型需自行接入
- LangGraph 版适合生产；最小版适合学习与快速验证
- Plan 模式不适用所有任务（简单任务直接执行更省），选型见决策表