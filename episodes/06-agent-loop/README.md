# 造物车间 #06 — Agent Loop：50行代码 × 4个控制点 × 1套Harness

> 扒开框架源码，手写一个不跑飞的Agent循环

📺 [B站视频](https://www.bilibili.com/video/BV1xxx/) | ⏱ 16:26 | 📅 2026-06-30

## 核心结论

**LangChain、OpenAI Assistants、Anthropic Tool Use——3个框架扒开来看，核心都是同一个while循环。** 50行Python就能手写一个完整的Agent Loop。但从"能跑"到"不跑飞"，需要4个控制点；从"不跑飞"到"能部署"，需要一套Harness。

## 四幕结构

| 幕 | 内容 | 交付物 |
|---|------|--------|
| 第一幕 | ReAct原理：3个框架1个秘密 | 认知：框架≠魔法 |
| 第二幕 | 50行Python手写Agent Loop | `agent_loop.py` |
| 第三幕 | 4个控制点让Loop不跑飞 | `control_points_checklist.md` |
| 第四幕 | Harness：从Demo到部署 | Harness架构模板 |

## 4个控制点 Checklist

```
✅ 1. Max Iterations = 10
   前5轮解决70%任务，超10轮基本跑飞
   
✅ 2. 错误恢复
   try/except → 包成Observation喂回去（恢复率87%）
   
✅ 3. Token Budget
   保留System + 最近3轮，旧的摘要或删
   
✅ 4. 终止条件（三重兜底）
   Final Answer关键词 + finish action + max_iter
   失败率: 12% → 0.3%
```

## 框架 vs 手写 决策树

```
任务简单，赶时间？
├─ 是 → 用框架（LangChain/LlamaIndex）
└─ 否 → 需要深度定制？
    ├─ 是 → 手写Loop
    └─ 否 → 想理解原理？
        ├─ 是 → 先手写一遍
        └─ 面试？→ 手写过的强10倍
```

## 资产清单

| 文件 | 用途 | 直接能用 |
|------|------|---------|
| [`agent_loop.py`](./agent_loop.py) | 完整Agent Loop代码（50行核心+4控制点） | ✅ `python agent_loop.py "你的问题"` |
| [`control_points_checklist.md`](./control_points_checklist.md) | 4个控制点完整Checklist | ✅ 可截图保存 |
| [`harness_template.py`](./harness_template.py) | Harness架构模板（System Prompt+Tool Schema+Tracing） | ✅ 改配置就能用 |

## 5分钟快速上手

```bash
# 1. 克隆仓库
git clone https://github.com/xxx/feynman-build-workshop.git
cd feynman-build-workshop/episodes/06-agent-loop

# 2. 安装依赖（只需要openai）
pip install openai

# 3. 设置API Key
export OPENAI_API_KEY=your_key

# 4. 运行Agent Loop
python agent_loop.py "北京今天天气怎么样"

# 5. 看Trace输出，理解每一轮在干什么
```

## 与C01-C05的关系

```
C01 记忆系统   ─┐
C02 意图识别   ─┤
C03 文档解析   ─┤── 数据平面（RAG Pipeline）
C04 切分召回   ─┤
C05 Rerank     ─┘
                 ↓ 
C06 Agent Loop ──── 控制平面（Agent执行引擎）
                 ↓
C07（下期）───── 组装整机：RAG + Agent Loop = 完整AI系统
```

## 真实踩坑记录

1. **47次死循环**：用户问"查最近10条新闻"，Agent换了47次关键词搜索，烧了¥200。原因：搜索API限流返回空结果，Agent以为没搜到。
2. **终止条件坑**：GPT-4有时输出"我的最终答案是..."而不是标准"Final Answer:"格式，单正则匹配不到。
3. **上下文爆炸**：Agent跑8轮后20k token，第9轮返回乱码。messages没有截断策略就是定时炸弹。
4. **错误恢复假象**：捕获异常后返回空字符串"" → Agent以为工具返回了空结果 → 继续用空信息推理 → 幻觉。正确做法是返回明确的错误描述。

---

> 系列进度：C01记忆 → C02意图 → C03解析 → C04切分 → C05重排 → **C06 Agent Loop** → C07 组装整机
