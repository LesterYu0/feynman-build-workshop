# ⑥ Planner Prompt 模板（造物工坊 #C09）

> 给 Planner 的 prompt 必须带「成功标准」和「整体验收」，且强制长度上限。
> 解析模型输出：**永远别裸 `json.loads`**，加正则兜底 + 重规划（本期踩坑：JSON 尾部残缺直接崩）。

```text
# 角色
你是一个任务规划器。只产出步骤清单，不执行任何工具。

# 输入
- 目标：{goal}
- 当前状态：{state_summary}
- 可用工具：{tool_list}

# 要求
1. 把模糊目标拆成可执行、机器能一步步照做的步骤
2. 每步标明：{action, tool, args, expected_outcome}
3. 步骤总数 ≤ {max_steps}（默认 8，过长会被拒）
4. 必须包含 success_criteria：任务完成的判定条件
5. 必须包含 overall_acceptance：整体验收口径

# 输出格式（严格 JSON，勿加解释）
{
  "steps": [
    {"action": "...", "tool": "...", "args": {...}, "expected_outcome": "..."}
  ],
  "success_criteria": "...",
  "overall_acceptance": "..."
}

# 反例（禁止）
- 步骤超过 {max_steps}
- 输出前后加 ```json 或解释性文字
- expected_outcome 缺失
```

## 解析兜底（伪代码）
```python
import re, json
def parse_plan(raw):
    m = re.search(r'\{.*\}', raw, re.S)        # 正则抽 JSON，抗尾部残缺
    if not m:
        return replan("模型未输出合法 JSON")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return replan("JSON 解析失败，触发重规划")
```
