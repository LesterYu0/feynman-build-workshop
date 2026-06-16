# 造物车间 #04 — 6种切分×4种召回×3层架构

> 帮你选对RAG的知识切法

## 核心结论

**切分策略选错比换模型差距还大**——同一个embedding模型，6种切分策略recall差距41分（67%→91%）。更致命的是，LLM自由抽取的知识图谱关系有30%是幻觉——本体(Ontology)约束是终极解法。

## 三层架构

| Layer | 方法 | 类比 | 适用场景 |
|-------|------|------|---------|
| L1 平面切分 | 6种策略（Fixed→Contextual+RRF+Rerank） | 平面地图 | 标准RAG |
| L2 树+图 | RAPTOR(纵向) / GraphRAG(横向) | 等高线+交通图 | 跨chunk推理 |
| L3 本体驱动 | Ontology RAG（OWL schema约束一切） | 城市规划图 | 合规/法律/工业标准 |

## 选型决策树

```
文档有领域本体？
├─ 是 → Ontology RAG (Layer 3)
│   ├─ 已有OWL Schema → 直接导入
│   └─ 没有 → OntoRAG自动归纳
├─ 否 → 答案需跨chunk推理？
│   ├─ 纵向概览→细节 → RAPTOR
│   └─ 横向实体关系 → GraphRAG
└─ 否 → 标准RAG (Layer 1)
    ├─ 通用 → Recursive 512 token
    ├─ 长文档强引用 → Late Chunking
    └─ 召回极高 → Contextual+RRF+Rerank
```

## Benchmark数据来源

- Databricks 2025对照实验（同一embedding，6种切分）
- FloTorch semantic chunking benchmark（91.9% recall / 54% answer accuracy）
- OG-RAG论文（+40% correct QA vs vanilla RAG）
- Ontology-aware KG-RAG论文（表格F1 +93.7%）
- Cohere/BGE reranking production data（+12-25 pts top-3 precision）
- Stanford+Meta "Lost in the Middle"（mid-context -20 pts）

## 本期交付资产

| 文件 | 说明 |
|------|------|
| `decision-tree-three-layers.md` | 3层选型决策树（交互式Markdown） |
| `chunk-config-cheatsheet.md` | 文档类型→切分策略速查表 |
| `eval-toolkit-minimal.py` | 100条query+recall@k自动化评测脚本 |
| `ontology-template.owl` | 基础OWL本体模板（可直接改领域名使用） |
