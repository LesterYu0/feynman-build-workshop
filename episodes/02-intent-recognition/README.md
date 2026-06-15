# 02 · 意图识别：从 if-else 到生产级

> **4 层漏斗 + 1 套槽位机制：让 Agent 不再对你的请求"装死"**

📺 [B站视频](https://www.bilibili.com/video/BV1xx411c7mD/) | ⏱ 15:44 | 📅 2026-06-11

---

## 你会得到什么

本期交付 4 份可直接上手的资产，帮你把一个"识别了 100 种意图但 80% 请求都不在里面"的 Agent 改造成"装死率 < 5%"的生产级路由系统：

| # | 资产 | 类型 | 用途 |
|:--:|------|:---:|------|
| 1 | [意图三分类工作表](./worksheet-intent-classification.md) | 📝 工作表 | 5 步搞清楚你的 Agent 真实要识别什么 |
| 2 | [Python 路由代码骨架](./code-intent-router-core.py) | 🐍 代码 | 4 层漏斗 + 槽位 + 兜底，改三个配置接入 |
| 3 | [三层路由决策树](./decision-tree-router.md) | 🌲 决策树 | 选什么、不选什么、每层延迟/准确率对照 |
| 4 | [压测检查清单](./testcases-verification.md) | ✅ 检查清单 | 单元→集成→对抗→长尾四级必测 |

---

## 5 分钟快速上手

```
步骤                              时间     产物
─────────────────────────────────────────────────
1. 打开三分类工作表，填空30分钟   30min    搞清楚你的 Agent 真实意图
2. 复制代码骨架，改3个配置        10min    接入你的 Agent
3. 边改边对照决策树              持续     别走弯路
4. 每加一层跑压测清单            每层5min 验证不退化
```

### 最简接入

```python
# 1. 复制 code-intent-router-core.py 到项目
# 2. 改这三个配置：

# CONFIG ①: L0 正则规则
RULES = [
    (r'^/(help|帮助|start)', 'HELP'),
    (r'^/(weather|天气)', 'WEATHER'),
    # 添加你自己的命令...
]

# CONFIG ②: L1 向量例句
ROUTE_DEFINITIONS = {
    "REFUND": Route("REFUND", ["退款", "退钱", "我要退货", ...], threshold=0.65),
    # 添加你的业务意图...
}

# CONFIG ③: L2 大模型回调（替换为你的 GPT/Claude 调用）
def SIMULATED_FC(query, candidates):
    # return "REFUND"  # 实际接入时换成你的 LLM 调用
    return candidates[0][0] if candidates else "UNKNOWN"

# 3. 一行接入
from intent_router_core import IntentRouter
router = IntentRouter()
result = router.route("我要退货")
# → RouteResult(intent="REFUND", confidence=0.92, layer="L1", latency_ms=23)
```

---

## 架构全景

```
┌─────────────────────────────────────────────────┐
│            4 层漏斗意图路由架构                     │
├─────────────────────────────────────────────────┤
│ L3 Fallback 优雅降级（兜底不崩溃）                │
│   └─ 三层都挂？走通用 Chat 或 OOD 拒答             │
├─────────────────────────────────────────────────┤
│ L2 大模型 Function Call（复杂/长尾）              │
│   └─ L1 置信度 < 0.5 时触发，延迟 200-800ms       │
├─────────────────────────────────────────────────┤
│ L1 向量相似度（语义匹配，TOP 20 意图）             │
│   └─ 0.5-2ms 延迟，准确率 85-95%                  │
├─────────────────────────────────────────────────┤
│ L0 正则规则（高频固定命令 /help /cancel）         │
│   └─ < 0.1ms 延迟，准确率 100%                     │
└─────────────────────────────────────────────────┘
```

---

## 关键决策速查

| 你的情况 | 用这个 | 别用那个 |
|:---|:---|:---|
| 高频固定命令（/help /cancel） | L0 正则 | 走 L1 向量（杀鸡用牛刀） |
| TOP 20 业务意图（语义近） | L1 向量相似度 | L2 大模型（贵且慢） |
| 长尾/复杂/多意图 | L2 Function Call | L1 向量（容易误判） |
| 三层都挂 | L3 Fallback | 抛异常（线上崩溃） |
| 误判成本高（医疗/金融） | threshold 提到 0.8 | 默认 0.65（漏判） |
| 召回成本高 | L0 覆盖 60%+ 流量 | 全部走 L1（账本爆炸） |

---

## 社区

- 有问题？去 [B站视频评论区](https://www.bilibili.com/video/BV1xx411c7mD/) 聊
- 改进了代码？欢迎提 [PR](../../CONTRIBUTING.md)
- 踩了坑想分享？Issues 区见
