# C08 · 5 个文档没写的真实踩坑清单

> 这 5 个坑都是我写 `mini_harness.py` 时真撞上的。文档里永远只给 happy path。

## 坑 1：单个 Provider 抛异常 → 整支队伍崩溃

**现象**：你以为 4 个模型是「1 个挂了还有 3 个顶上」，真相是——如果不 catch，1 个挂 = 全挂。

**解法**：把整个调用包进 try/except，失败就地降级成一份「失败提案」，绝不 throw 出 `call()`。

```python
def call(self, prompt):
    try:
        return self._generate(prompt)
    except Exception:
        return Proposal(text="[FAILED]", cost=0.0, ok=False)
```

## 坑 2：Ensemble 不设超时 → 一家卡死全队死

**现象**：第一次跑 demo 直接卡死——Kimi 模拟成会超时，程序永远停在那等，光标一直闪。

**解法**：`as_completed(futures, timeout=...)`，超时的自动放弃、降级过滤。

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=len(providers)) as ex:
    futures = {ex.submit(p.call, q): p for p in providers}
    for fut in as_completed(futures, timeout=8):
        prop = fut.result()
        ...
```

## 坑 3：不过滤失败提案 → 垃圾也有一票

**现象**：超时被降级的那份提案文本是 `[FAILED]`，不过滤直接扔进投票器，一份垃圾也占一票，共识被污染。

**解法**：聚合前 `filter` 掉 `ok == False` 或空文本。

```python
valid = [p for p in proposals if p.ok and p.text.strip()]
```

## 坑 4：不归一化 → 同一答案永远选不出共识

**现象**：3 个模型给的是同一个答案，可投票器每次都退回第一个。原因：`"用MoE。"` / `"用 MoE"` / `"用MoE"` 标点空格不一样，被当成三个不同答案，各得一票永远平局。

**解法**：投票前归一化（strip / lower / 去结尾标点），再回填原始答案。

```python
def _norm(t): return t.strip().lower().rstrip(".。!！?？")
counts = {}
for p in valid:
    counts.setdefault(_norm(p.text), []).append(p)
winner_norm, group = max(counts.items(), key=lambda kv: len(kv[1]))
winner = group[0].text  # 回填原始答案
```

## 坑 5：判难度用大模型 / 简单题无脑组队 → 成本 ×60

**现象 5a（判难度悖论）**：想「让一个大模型判断这题难不难」，但这次调用本身就烧掉了你想省的钱，绕一圈白省。

**现象 5b（账单暴击）**：简单题「中国首都」走单模型成本 0.0002；如果无脑组队，涨到 0.0120——**60 倍**。

**解法**：难度判断用廉价规则（长度超阈值 / 命中「为什么 / 设计 / 对比 / 权衡」等关键词），一分钱模型调用都不花；Router 阈值调严，少组队。

```python
HARD_KW = ["为什么", "设计", "对比", "权衡", "分析", "评估"]
def is_hard(q):
    return len(q) > 40 or any(k in q for k in HARD_KW)
```
