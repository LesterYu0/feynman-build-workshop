#!/usr/bin/env python3
"""
C04 评估工具最小集 —— 文件切分与召回
测量两个核心指标：Recall@K 和 Answer Accuracy

用法：
  python eval-toolkit-minimal.py --chunks chunks.jsonl --queries queries.jsonl

输入格式：
  chunks.jsonl: 每行 {"id": "c1", "text": "...", "metadata": {}}
  queries.jsonl: 每行 {"id": "q1", "question": "...", "relevant_chunk_ids": ["c1","c3"], "expected_answer": "..."}

输出：
  - 控制台打印 Recall@K / Answer Accuracy
  - results.json 保存详细结果
"""

import json
import argparse
import statistics
from pathlib import Path
from typing import Any


def load_jsonl(path: str) -> list[dict[str, Any]]:
    """加载 JSONL 文件"""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def compute_recall_at_k(
    queries: list[dict],
    retrieved: dict[str, list[str]],
    k: int = 5,
) -> float:
    """
    计算 Recall@K

    retrieved: {query_id: [chunk_id_1, chunk_id_2, ...]} 按相关性排序
    """
    recalls = []
    for q in queries:
        qid = q["id"]
        relevant = set(q["relevant_chunk_ids"])
        if not relevant:
            continue
        top_k = set(retrieved.get(qid, [])[:k])
        hit = len(relevant & top_k)
        recalls.append(hit / len(relevant))

    return statistics.mean(recalls) if recalls else 0.0


def compute_answer_accuracy(
    queries: list[dict],
    answers: dict[str, str],
    judge_fn=None,
) -> float:
    """
    计算 Answer Accuracy

    judge_fn: 可选的自定义评判函数 (expected, actual) -> bool
    默认用子串匹配（极简版，生产环境建议用 LLM-as-Judge）
    """
    correct = 0
    total = 0
    for q in queries:
        qid = q["id"]
        expected = q.get("expected_answer", "")
        actual = answers.get(qid, "")
        if not expected:
            continue
        total += 1
        if judge_fn:
            if judge_fn(expected, actual):
                correct += 1
        else:
            # 极简子串匹配
            if expected.lower() in actual.lower():
                correct += 1

    return correct / total if total > 0 else 0.0


def compute_mrr(
    queries: list[dict],
    retrieved: dict[str, list[str]],
) -> float:
    """计算 MRR (Mean Reciprocal Rank)"""
    rr_list = []
    for q in queries:
        qid = q["id"]
        relevant = set(q["relevant_chunk_ids"])
        top_list = retrieved.get(qid, [])
        for rank, cid in enumerate(top_list, start=1):
            if cid in relevant:
                rr_list.append(1.0 / rank)
                break
        else:
            rr_list.append(0.0)
    return statistics.mean(rr_list) if rr_list else 0.0


def evaluate(chunks_path: str, queries_path: str, output_path: str = "results.json"):
    """完整评估流程"""
    chunks = load_jsonl(chunks_path)
    queries = load_jsonl(queries_path)

    print(f"加载完成: {len(chunks)} chunks, {len(queries)} queries")

    # ============================================================
    # 以下是需要你实现的检索接口
    # 替换为你自己的 embedder + vector store + reranker
    # ============================================================
    retrieved: dict[str, list[str]] = {}
    answers: dict[str, str] = {}

    # 简单的 TF-IDF 检索作为 baseline 示例
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        chunk_texts = [c["text"] for c in chunks]
        chunk_ids = [c["id"] for c in chunks]
        vectorizer = TfidfVectorizer(max_features=5000)
        chunk_vecs = vectorizer.fit_transform(chunk_texts)

        for q in queries:
            q_vec = vectorizer.transform([q["question"]])
            sims = cosine_similarity(q_vec, chunk_vecs)[0]
            top_indices = np.argsort(sims)[::-1][:10]
            retrieved[q["id"]] = [chunk_ids[i] for i in top_indices]
            # baseline: 直接返回 top-1 chunk text 作为答案
            answers[q["id"]] = chunk_texts[top_indices[0]] if len(top_indices) > 0 else ""

        print("使用 TF-IDF baseline 检索")
    except ImportError:
        print("⚠ sklearn 未安装，使用 dummy 数据")
        for q in queries:
            retrieved[q["id"]] = [c["id"] for c in chunks[:5]]
            answers[q["id"]] = chunks[0]["text"] if chunks else ""

    # 计算指标
    results = {
        "num_chunks": len(chunks),
        "num_queries": len(queries),
        "recall_at_1": round(compute_recall_at_k(queries, retrieved, k=1), 4),
        "recall_at_3": round(compute_recall_at_k(queries, retrieved, k=3), 4),
        "recall_at_5": round(compute_recall_at_k(queries, retrieved, k=5), 4),
        "recall_at_10": round(compute_recall_at_k(queries, retrieved, k=10), 4),
        "mrr": round(compute_mrr(queries, retrieved), 4),
        "answer_accuracy": round(compute_answer_accuracy(queries, answers), 4),
    }

    # 打印结果
    print("\n" + "=" * 50)
    print("  切分与召回评估结果")
    print("=" * 50)
    for k, v in results.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2%}" if v < 1 else f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")
    print("=" * 50)

    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n详细结果已保存至 {output_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="文件切分与召回评估工具")
    parser.add_argument("--chunks", required=True, help="chunks JSONL 路径")
    parser.add_argument("--queries", required=True, help="queries JSONL 路径")
    parser.add_argument("--output", default="results.json", help="输出路径")
    args = parser.parse_args()
    evaluate(args.chunks, args.queries, args.output)
