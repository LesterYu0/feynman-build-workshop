# 记忆脚手架迭代流程图

> 从C01手工版 → AutoMem自动版的演进路径

---

## C01手工版流程

```
v0 prompt → 跑episode → 发现翻车
     ↑                         ↓
  人工调prompt ← 凭经验找原因 ←┘
```

**问题**：
- 全凭经验，迭代慢
- 不同任务要重写prompt
- 轨迹太长人审不了

---

## AutoMem自动版流程

### Loop1：脚手架优化（老师改教案）

```
vN scaffold
    ↓
Agent跑 k 个 episode（用Base model或上一轮模型）
    ↓
收集完整轨迹 + 奖励信号
    ↓
meta-LLM审查：找记忆使用的问题
    ↓
输出 v(N+1) scaffold
    ↓
（重复直到收敛）
```

**要点**：
- meta-LLM看的是完整episode，不是单步
- 每次迭代生成新的system prompt / file schema / 动作偏好 / 示例
- 直到奖励/行为指标不再提升

---

### Loop2：能力训练（教练选好球）

```
Loop1收敛后的最终scaffold
    ↓
用该scaffold跑大量episode
    ↓
筛选"优质记忆决策"片段
    ↓
LoRA微调Base model
    ↓
得到 Memory Specialist（记忆专家模型）
```

**优质决策标准**（按AutoMem论文）：
- 低Write/Search比（先查后写）
- 低冗余写入
- 高任务奖励
- 上下文压缩率高

---

## 部署形态

```
                    ┌─────────────────┐
  任务输入 ──→     │  Memory Specialist │  ← 处理记忆动作 read/write/upsert
                    │    (LoRA微调)     │
                    └────────┬────────┘
                             │ 共享对话历史
                             ↓
                    ┌─────────────────┐
                    │   Task Model      │  ← 处理世界动作
                    │   (Base model)    │
                    └─────────────────┘
```

---

## 迁移到工程场景的简化版

1. ** scaffolding v0**：先写一版手工prompt + 文件schema
2. **跑10-20条轨迹**：收集Agent实际记忆行为
3. **用GPT-4/Claude做meta-LLM审查**：让它指出3个最大问题
4. **生成v1 scaffold**：修改prompt/schema/示例
5. **重复3-4轮**：直到行为指标稳定
6. **（可选）LoRA微调**：如果数据量够大，做记忆能力训练

---

## 关键指标看板

| 指标 | 基线 | 目标 | 含义 |
|:---|:---|:---|:---|
| Write/Search比 | >0.6 | <0.4 | 先查后写的习惯 |
| 每步新增字符 | >50 | <10 | 文件膨胀控制 |
| 冗余写入占比 | 高 | <20% | 不写重复信息 |
| 记忆token占比 | >40% | <25% | 上下文不溢出 |
| 任务奖励 | 基线 | +50%+ | 记忆真的有用 |
