# 造物车间 #08 — 国产模型拼个团：100 行手写多模型路由 Harness

> 拼多多砍价 × AI 大模型：4 家弱模型组团，咬住旗舰还省八成 token

📺 视频：即将发布 ｜ ⏱ 11:40 ｜ 📅 2026-07-11

## 核心结论

**买智能跟拼团砍价是一个道理。** 单个国产模型单挑打不过海外旗舰，但把它们「拼个团」——用 ensemble routing 把 DeepSeek、GLM、Kimi、Qwen 四家叫到一起各出一份答案、共识聚合——就能在深度研究榜咬住旗舰，token 还砍掉八成。

关键不是「换更强的模型」，而是「换更好的组织方式」：路由把贵的智能只花在难题上，简单题走便宜模型，钱包才保得住。

## 六段结构

| 段 | 内容 | 交付物 |
|---|------|--------|
| S0 | 痛点钩子：拼团意外组合 | 问题意识 |
| S1 | 问题定义：ensemble routing = 路由 + 多样性采样 + 共识聚合 | 知识卡片① |
| S2 | 四零件拆解：Provider / Ensemble / Aggregator / Router | 架构图 |
| S3 | 写代码 + 坑①②：Provider 异常降级 → Ensemble 超时卡死 → 过滤失败提案 | 知识卡片③ |
| S4 | 坑③④⑤：归一化平局 → 判难度悖论 → 账单验证（简单题 ×60 倍） | 知识卡片④ |
| S5 | 体系总结 + 选型决策表 | `c08-routing-decision-table.md` |
| S6 | 收藏引导：把 mock provider 换成你的模型就能上 | 资产链接 |

## 5 个文档没写的坑（速查）

| # | 坑 | 解法 |
|:--|:---|:---|
| 1 | 单 provider 抛异常 → 整队崩溃 | 每个 provider 失败就地降级成「失败提案」，不 throw |
| 2 | Ensemble 不设超时 → 一家卡死全队死 | `as_completed(futures, timeout=...)` 超时降级过滤 |
| 3 | 不过滤失败提案 → 垃圾也有一票，污染共识 | 聚合前过滤掉 `[FAILED]` / 空提案 |
| 4 | 不归一化 → 同答案永远平局选不出共识 | 投票前 `strip().lower()` + 去结尾标点，再回填原始答案 |
| 5 | 判难度用大模型 / 简单题无脑组队 → 成本 ×60 | 用廉价规则（长度 / 关键词）判难度；Router 阈值调严 |

> 完整踩坑细节与解法代码见 [`c08-pitfalls-checklist.md`](./c08-pitfalls-checklist.md)

## 资产清单

| 文件 | 用途 | 直接能用 |
|------|------|---------|
| [`mini_harness.py`](./mini_harness.py) | 100 行多模型 ensemble routing Harness（Provider / Ensemble / Aggregator / Router） | ✅ 换 provider 就能跑 |
| [`demo.py`](./demo.py) | 用 mock provider 跑通的示例 | ✅ 直接 `python demo.py` |
| [`c08-pitfalls-checklist.md`](./c08-pitfalls-checklist.md) | 5 个真实踩坑清单（附解法代码） | ✅ 截图保存 |
| [`c08-routing-decision-table.md`](./c08-routing-decision-table.md) | 选型决策表 + 生产环境 checklist | ✅ 对照执行 |

## 5 分钟快速上手

```bash
git clone https://github.com/xxx/feynman-build-workshop.git
cd feynman-build-workshop/episodes/08-multi-model-harness

# 1. 用 mock provider 先把链路跑通
python demo.py

# 2. 打开 mini_harness.py，把 MockProvider 换成你的真实模型接口（只需实现 _generate）
# 3. 按 c08-routing-decision-table.md 选路由策略
# 4. 跑账单验证：简单题应走单模型，成本远低于组队
```

## 与 C01-C07 的关系

```
C01 记忆系统    ─┐
C06 Agent Loop  ─┼── C08 给 Agent 装配「多模型协作」能力
C07 记忆即技能  ─┤    （路由 + 并行采样 + 共识聚合）
C02-C05 RAG    ─┘
```

## 关键数据

- 简单题单模型成本：0.0002 ｜ 难题组队 3 家：0.0120
- 组队一次 ≈ 单模型 5 倍成本 → 路由决定钱包
- 简单题无脑组队 → 成本 ×60（坑⑤反面教材）
- OpenSquilla：DRACO 深度研究榜咬住 Fable 5，token 砍八成

## 诚实局限

- demo 用 mock provider 验证链路，真实模型需自行接入（实现 `_generate`）
- 路由用廉价规则（长度 / 关键词），复杂业务可升级为轻量分类器
- ensemble 不保证永远优于单模型，取决于题目多样性与模型互补性
