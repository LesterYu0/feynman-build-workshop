# 资产 #4：六条单测用例

> 每次改路由规则、加新意图、换 embedding 模型后，跑完这六条再上线。

---

## 环境准备

```bash
# 安装依赖
pip install semantic-router sentence-transformers

# 跑测试
python asset-2-intent-router-skeleton.py test
```

---

## 测试用例

### 用例 1：L0 精确命中

```
输入: /weather
期望层: L0
期望意图: WEATHER
期望延迟: < 0.5ms
```

### 用例 2：L1 向量模糊匹配

```
输入: 帮我退钱
期望层: L1
期望意图: REFUND
期望延迟: < 100ms
注意: "退钱" ≠ 精确匹配，但语义≈退款
```

### 用例 3：走快路径的绝不走 L2

```
输入: 我要退款
期望: layer IN {L0, L1}
验证: router.stats["L2"] == 0 (整个 session 不该触发一次 LLM)
原因: "退款" 是高频意图，L0 或 L1 必须覆盖
```

### 用例 4：OOD 不瞎执行

```
输入: 帮我写首诗
期望层: OOD
期望意图: OOD
验证: 没有调用任何业务工具/API
原因: 全意图置信度 < 0.4 必须判定 OOD
```

### 用例 5：低置信反问

```
场景: 构造一个让 L2 返回 confidence < 0.6 的输入
期望层: CLARIFY
验证: 反问用户，不执行任何动作
```

### 用例 6：熔断触发

```
场景: 连续 3 次输入 OOD/CLARIFY 的 query
验证:
  1. 第 4 次请求 layer = BREAKER
  2. 第 4-8 次请求只走 L0/L1，不调 L2
  3. 第 9 次请求恢复（half-open 试探 L2）
```

---

## 测试运行

```bash
python asset-2-intent-router-skeleton.py test

# 期望输出：
#   ✓ /weather → WEATHER (L0)
#   ✓ /help → HELP (L0)
#   ✓ 我要退款 → REFUND (L1)
#   ✓ 帮我退钱 → REFUND (L1)
#   ✓ 订机票 → BOOKING (L1)
#   ✓ 查一下订单 → ORDER_QUERY (L1)
#   ✓ 帮我写首诗 → OOD (OOD)
#   ✓ 哈哈哈哈 → OOD (OOD)
#
#   8/8 passed
```

---

## 回归测试 Checklist

每次修改路由规则后：

- [ ] 用例 1-8 全部通过
- [ ] L0 命中率 > 60%（测试集上）
- [ ] L1 命中率 > 15%（测试集上）
- [ ] L0+L1 合计命中率 > 75%
- [ ] OOD 准确率 > 90%（混入 10 条闲聊/其他领域）
- [ ] 熔断逻辑：连续 3 次低置信→第 4 次 breaker=True
