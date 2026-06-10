# 资产 #4：5个压测用例

> 造物车间 #01 · 7步设计Agent记忆系统
>
> 每加一层跑一次。不知道通过标准就是不知道你走到哪了。

---

## 使用说明

每完成一个 Step，跑对应的用例。全部通过才进入下一步。

---

## 测试 0：基线（不加记忆系统时）

**目的**：记录 Agent 在完全不用记忆系统时的表现，作为对比基线。

**步骤**：
1. 关掉所有记忆注入
2. 让 Agent 回答 20 个它理论上能从记忆里回答的问题
3. 记录 Top-1 命中率和平均响应时间

**记录**：
- 基线 Top-1 命中率: ____%
- 基线响应时间: ____ms
- 所有测试完成后对比

---

## 测试 1：精确召回测试

**对应 Step**：Step 2 (SQLite FTS5)

**问题**："上次那个 [具体 bug 名称] 是怎么修的？"

**准备**：
- 在记忆库中写入一条明确的 bug 修复记录（你确定内容的事）
- 记录这条记忆的 ID

**执行**：
1. 让 Agent 搜索记忆回答这个问题
2. 检查 Top-1 结果的内容是否匹配你写的那条

**通过标准**：
- ✅ Top-1 结果内容 100% 匹配目标记录
- ✅ 返回时间 < 500ms

**未通过 → 检查**：
- FTS5 索引是否正确建立？
- 关键词是否在查询和记忆中一致？
- 是否被 valid_until 提前过滤？

---

## 测试 2：时效性测试

**对应 Step**：Step 3 (时效系统)

**问题**："这个项目现在用什么框架？"

**准备**：
- 写入一条 3 个月前的记忆："项目当前使用 Framework A"
- 写入一条最近 1 周的记忆："项目已迁移到 Framework B"
- 将旧记忆的 valid_until 设为迁移日期

**执行**：
1. 让 Agent 搜索记忆回答
2. 检查它是否识别出 Framework B 是当前答案
3. 检查它是否提到旧框架已迁移

**通过标准**：
- ✅ 主回答是 Framework B
- ✅ 没有从旧记忆中引用 Framework A
- ✅ 可选：提到"从 Framework A 迁移"但明确标注已过时

**未通过 → 检查**：
- 旧记忆的 valid_until 是否正确设置？
- search 是否使用了 include_expired=False？
- 旧记忆的 superseded_by 是否指向了新记录？

---

## 测试 3：信噪比测试

**对应 Step**：Step 4 (Frozen Snapshot + 记忆注入量控制)

**操作**："删除 /tmp 下的临时文件。"

**准备**：
- 你的记忆系统处于正常注入状态
- 不修改任何记忆内容

**执行**：
1. 让 Agent 执行这个简单文件操作
2. 观察它是否正确执行（只删 /tmp 下的临时文件）
3. 观察它有没有做额外的事（误删、多删、报告与记忆相关的无关信息）

**通过标准**：
- ✅ 正确删除目标文件
- ✅ 没有多删其他目录的文件
- ✅ 没有输出与当前任务无关的记忆内容

**未通过 → 检查**：
- 记忆注入量是否过多？（> 2000 token）
- 是否有记忆内容语义上与当前任务"相关"但实际应被过滤？
- Frozen Snapshot 的核心规则是否被记忆内容淹没？（跑测试 0 对比指令遵从率）

---

## 测试 4：时间旅行测试

**对应 Step**：Step 5 (归纳层)

**问题**："我 3 个月前做的那个决策现在还适用吗？"

**准备**：
- 写入一条 3 个月前的决策："选用方案 X，因为当时方案 Y 不支持功能 Z"
- 同时确保系统中有足够上下文让 Agent 知道"现在的情况"（功能 Z 已被方案 Y 支持）

**执行**：
1. 让 Agent 搜索记忆回答
2. 检查它是否同时引用了"当时的约束"和"现在的变化"
3. 检查它的最终判断是否基于当前情况

**通过标准**：
- ✅ 引用了原始决策（方案 X）及其当时约束
- ✅ 指出了当时约束已发生变化
- ✅ 给出了基于当前情况的更新判断

**未通过 → 检查**：
- 归纳层是否在工作？（新的事实是否沉淀为可检索的记忆？）
- 是否有两条冲突记录且未被检测？
- superseded_by 关系是否建立？

---

## 测试 5：经济账测试（Prefix Cache 命中率）

**对应 Step**：Step 4 + Step 7

**目的**：验证记忆系统的经济运行

**步骤**：
1. 连续发送 100 次 Agent 请求（可以是简单回复，但需保持 system prompt 不变）
2. 查看 API 用量报表
3. 计算 Cache Read Tokens ÷ Total Input Tokens

**通过标准**：
- ✅ 缓存命中率 > 80%
- ✅ 单次请求 Token 消耗无明显波动

**如果命中率 < 60%**：
- 检查 system prompt 头部是否有动态内容（日期、时间、用户名）
- 按 Step 4 修复：冻结核心前缀，动态信息后置

**如果命中率在 60-80%**：
- 系统可用，但仍有优化空间
- 检查是否有间歇性的前缀变化

---

## 全量自检清单

跑完所有测试后，对照检查：

- [ ] 测试 1 (精确召回)：Top-1 命中，< 500ms
- [ ] 测试 2 (时效性)：正确答案是最新记忆
- [ ] 测试 3 (信噪比)：简单操作不被记忆干扰
- [ ] 测试 4 (时间旅行)：能同时看当时和现在
- [ ] 测试 5 (经济账)：Cache 命中率 > 80%
- [ ] 基线对比：Top-1 命中率相比测试 0 提升了多少？

---

## 进阶：自动化压测脚本框架

```python
#!/usr/bin/env python3
"""auto_test.py — 自动化压测"""

from agent_memory import search_memory, add_memory, CONFIG, search_memory

TEST_CASES = [
    {
        "name": "测试1-精确召回",
        "query": "EP.35 chunk3 渲染崩溃 怎么修",
        "expected_id": 42,  # 替换为你的真实记忆ID
        "check": lambda results: results[0]['id'] == 42 if results else False,
    },
    {
        "name": "测试2-时效性",
        "query": "项目 现在 什么 框架",
        "check": lambda results: any("Framework B" in r['content'] for r in results),
    },
    {
        "name": "测试3-信噪比",
        "query": "删除 /tmp 临时文件",
        "check": lambda results: len(results) <= 2,  # 不应返回过多记忆
    },
    {
        "name": "测试4-时间旅行",
        "query": "三个月前 决策 还适用",
        "check": lambda results: all(
            r.get('category', '') != 'archived' or '过时' in r.get('content', '')
            for r in results
        ),
    },
]

def run_all():
    passed = 0
    failed = 0
    for tc in TEST_CASES:
        results = search_memory(CONFIG["db_path"], tc["query"])
        ok = tc["check"](results)
        status = "✅" if ok else "❌"
        print(f"{status} {tc['name']}: Top result = {results[0]['content'][:60] if results else 'N/A'}")
        if ok:
            passed += 1
        else:
            failed += 1
    print(f"\n📊 通过: {passed}/{passed + failed}")

if __name__ == "__main__":
    run_all()
```
