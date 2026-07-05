# 造物车间 #07 — Agent 记忆不是存储，是技能

> 5 个信号诊断你的记忆系统 + 1 套 AutoMem 双循环优化框架

📺 [B站视频](https://www.bilibili.com/video/BV1kSMM6nEhV/) | ⏱ 7:47 | 📅 2026-07-05

![封面](./cover.png)

## 核心结论

**给 Agent 加记忆文件只是起点。让 Agent 学会管理记忆，才是从「能记」到「会用」的跨越。**

斯坦福 AutoMem（arXiv:2607.01224）的核心洞察：记忆不是存储模块，而是一种可训练的认知技能——知道记什么、何时查、怎么组织。32B 的 Qwen 2.5 只优化记忆管理，就能在 NetHack 上超越 Claude Opus 4.5。

## 六段结构

| 段 | 内容 | 交付物 |
|---|------|--------|
| S0 | 痛点钩子：Agent 记了不查、查了不用 | 问题意识 |
| S1 | 3 个文档不会写的坑 | 坑清单 |
| S2 | 元记忆 → 文件系统记忆 → 双循环架构 | 认知框架 |
| S3 | Loop1：meta-LLM 自动迭代记忆脚手架 | `decision-tree-scaffold-iteration-flow.md` |
| S4 | Loop2：LoRA 微调记忆能力 | `code-automem-lite-harness.py` |
| S5 | 5 个信号诊断你的记忆系统 | `worksheet-memory-diagnostic-checklist.md` |
| S6 | 收藏引导 + 下期预告 | 资产链接 |

## 5 个诊断信号速查

| 信号 | 症状 | 根因 | 解法 |
|:---|:---|:---|:---|
| 1. 文件膨胀 | 记忆文件线性增长，1000 步后 MB 级 | 无界追加 | UPSERT/去重 |
| 2. 写了不查 | Write/Search 比 > 0.6 | 模型没学过「先查后写」 | LoRA 微调 |
| 3. 策略僵化 | 换任务类型 prompt 就失效 | 策略写死在 prompt 里 | meta-LLM 自动迭代 |
| 4. 上下文溢出 | 记忆 token 占比 > 40% | 记忆全部塞进上下文 | 按需检索 |
| 5. 延迟后果 | 第 50 步漏记，第 800 步翻车 | 轨迹太长人审不了 | meta-LLM 全轨迹审查 |

## 资产清单

| 文件 | 用途 | 直接能用 |
|------|------|---------|
| [`code-automem-lite-harness.py`](./code-automem-lite-harness.py) | 简化版 AutoMem 记忆系统 Harness（文件系统记忆动作 + meta-LLM 审查循环） | ✅ 改配置就能跑 |
| [`worksheet-memory-diagnostic-checklist.md`](./worksheet-memory-diagnostic-checklist.md) | 5 信号诊断清单 | ✅ 截图保存 |
| [`decision-tree-scaffold-iteration-flow.md`](./decision-tree-scaffold-iteration-flow.md) | 记忆脚手架迭代流程图（C01 手工版 → AutoMem 自动版） | ✅ 对照执行 |

## 5 分钟快速上手

```bash
# 1. 克隆仓库
git clone https://github.com/xxx/feynman-build-workshop.git
cd feynman-build-workshop/episodes/07-agent-memory-as-skill

# 2. 运行简化版 AutoMem Harness 示例
python code-automem-lite-harness.py

# 3. 先看 worksheet-memory-diagnostic-checklist.md，给现有 Agent 打分
# 4. 再用 decision-tree-scaffold-iteration-flow.md 规划你的 v1→vN 迭代
```

## 与 C01-C06 的关系

```
C01 记忆系统    ─┐
C06 Agent Loop  ─┼── C07 让 Agent 自己学会管理记忆
C02 意图识别    ─┤    （元记忆 + 双循环优化）
C03-C05 RAG    ─┘
```

## 关键数据

- Write/Search 比：0.84 → 0.39（-54%）
- 地图文件增长：138 字符/步 → 6 字符/步（-95%）
- 每步上下文：-25%
- 冗余写入：-68%
- NetHack：32B Qwen 2.5 达 51.4%，超越 Claude Opus 4.5 的 27.5%

## 诚实局限

- 仅在游戏环境（Crafter / MiniHack / NetHack）验证
- 每个环境独立优化，跨环境共享尚未探索
- 情景记忆每 episode 重置
- 真实世界任务适用性待验证
