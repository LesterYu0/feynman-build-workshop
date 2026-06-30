# Agent Loop 4个控制点 Checklist

> 费曼学AI · 造物工坊 #06 · 从Demo到产品的分水岭

---

## ✅ 控制点1: Max Iterations（迭代上限）

**问题**：Agent卡在错误上反复调同一个工具，死循环烧Token
**解药**：`for i in range(10)` 替代 `while True`

| 参数 | 推荐值 | 依据 |
|------|--------|------|
| max_iterations | 8-12 | 前5轮解决70%任务，8轮解决90%，超10轮基本跑飞 |
| 返回方式 | partial result | 超限不报错，返回当前最佳结果让调用方决定 |

**真实案例**：用户问"查最近10条新闻"，Agent换了47次关键词搜索，烧了¥200

---

## ✅ 控制点2: 错误恢复（Error Recovery）

**问题**：工具报错，Agent直接crash
**解药**：`try/except` → 把error包成Observation喂回去

| 错误类型 | 处理方式 | 恢复率 |
|---------|---------|--------|
| Timeout超时 | 告诉Agent换工具 | 87% |
| 参数格式错 | 告诉Agent修正参数重试 | 92% |
| RateLimit限流 | 等几秒后重试，不告诉Agent | 99% |

**关键**：错误也是Observation，不是crash的理由

---

## ✅ 控制点3: Token Budget（令牌预算）

**问题**：每轮往messages加内容，第8轮context window满了
**解药**：滑动窗口 — 保留System + 最近3轮

| 策略 | 优点 | 缺点 | 推荐场景 |
|------|------|------|---------|
| 滑动窗口 | 稳定可控 | 丢失早期信息 | 生产环境首选 |
| 摘要压缩 | 保留信息 | 多花1次API调用 | 信息密集任务 |
| 向量检索 | 按需召回 | 实现复杂 | 超长对话 |

**安全线**：System + 最近3轮，旧的摘要后保留

---

## ✅ 控制点4: 终止条件（Termination）

**问题**：LLM不说Final Answer，一直Act下去
**解药**：三重条件互相兜底

```python
should_stop = (
    "Final Answer" in response or   # 条件1: 关键词匹配
    action == "finish" or            # 条件2: 解析结果
    iteration >= MAX_ITERATIONS      # 条件3: 硬上限
)
```

| 方案 | 终止失败率 |
|------|-----------|
| 单条件（只看finish） | 12% |
| 双条件 | 3.2% |
| 三重兜底 | **0.3%** |

---

## 优先级排序

```
1. Max Iterations  ← 安全网，必须第一个加
2. 错误恢复        ← 工具一定会出错
3. 终止条件        ← 防止无限Act
4. Token Budget    ← 前3个解决后再管
```

**Trade-off**：控制越严，Agent能力越受限。不是越多越好，是刚刚好。

---

## 框架 vs 手写 决策树

| 场景 | 选择 |
|------|------|
| 任务简单，赶时间 | 用框架（LangChain/LlamaIndex） |
| 需要深度定制和可控性 | 手写Loop |
| 想理解Agent原理 | 先手写一遍 |
| 面试展示能力 | 手写过的比只用过框架的强10倍 |

**建议**：先手写理解，再用框架提效。

---

> 费曼学AI · 造物工坊 #06
> 下期：把RAG装进Agent Loop，Agent自己决定何时检索、何时回答
