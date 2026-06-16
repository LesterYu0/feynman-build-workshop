# Chunking 配置速查表

> C04「文件切分与召回」配套资产 —— 一张表选对配置

## Layer 1：6 大扁平切分策略速选

| 策略 | 召回率 | 适用场景 | 关键参数 | 陷阱 |
|------|--------|---------|---------|------|
| Fixed-size | ~67% | 日志/无结构文本 | chunk=512, overlap=50 | 切断语义边界 |
| Recursive | 69-71% | 通用文档 | separators=["\n\n","\n"," "] | 需调分隔符优先级 |
| Semantic | 76% | 长文/论文 | breakpoint_threshold=percentile(75) | 小块均长仅43 token，答不准 |
| Late Chunking | 78% | 长上下文 LLM | 用 jina-embeddings-v3 | 需要 long-context embedder |
| Contextual Retrieval | 84% | 精度敏感场景 | context_model=Claude/GPT-4o-mini | 每 chunk 多 1 次 LLM 调用 |
| Contextual+RRF+Rerank | **91%** | 生产级推荐 | reranker=cross-encoder | 管线最长，延迟+200ms |

**黄金法则**：`Contextual Retrieval + Cohere Rerank` 是当前性价比最高的通用方案。

## 快速选型路径

```
你的文档是什么？
├── 纯文本/日志 → Recursive (快速上线) 或 Late Chunking (长上下文)
├── 结构化文档 ─→ Semantic (保语义边界) + Rerank
├── 高精度刚需 ─→ Contextual Retrieval + Rerank (91% recall)
└── 混合/不确定 → 先递归切分，再叠加 Contextual + Rerank
```

## Layer 2：结构化扩展选型

| 方案 | 核心动作 | 何时加？ | 成本 |
|------|---------|---------|------|
| RAPTOR | GMM 聚类 → LLM 摘要 → 递归建树 | 需要"概览级"回答（如"总结全书"） | +2x LLM 调用 |
| GraphRAG | LLM 提取实体/关系 → Leiden 社区 | 需要"跨文档关联"回答 | +5x LLM 调用，30% 幻觉率 |

**经验**：先跑通 Layer 1 再加 Layer 2。结构化扩展的 ROI 取决于"跨 chunk 推理"需求频率。

## Layer 3：本体约束层

| 约束位置 | 作用 | 模板 |
|---------|------|------|
| 切分边界 | 按 OWL 类边界切，不切半 | `owl:Class` → chunk 边界 |
| 提取 Schema | 只提取 Schema 内实体 | `owl:ObjectProperty` 白名单 |
| 检索优化 | 超图覆盖选 chunk | OG-RAG 算法 |

**本体层 ROI**：表结构 F1 +93.7%，正确问答 +40%（vs vanilla RAG）。

## Reranker 速选

| Reranker | Top-3 精度提升 | 延迟 | 推荐 |
|---------|--------------|------|------|
| Cohere Rerank | +12-25 pts | ~150ms | 通用首选 |
| BGE-Reranker (本地) | +15-20 pts | ~80ms | 隐私敏感 |
| FlashRank | +10-15 pts | ~30ms | 延迟敏感 |

## 上下文悬崖警戒

> Embedding 模型的有效上下文窗口约 2,500 token。
> 超过后，边界信息被"遗忘"，召回率断崖式下跌。
> **对策**：chunk 长度 ≤ 2,000 token，重叠加 Contextual。

---

*e04-chunking-retrieval | 费曼学AI*
