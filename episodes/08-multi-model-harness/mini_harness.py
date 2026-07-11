"""
mini_harness.py — 100 行级最小「多模型 Harness」
======================================================
造物工坊 C08 · 可收藏资产（单文件带走）

它做一件事：把多个模型组织成一支协作队伍，而不是把所有请求都丢给最贵的那个。

三个核心零件：
  1. Provider   —— 每个模型的统一接口（真实模型只要实现 .call()）
  2. Ensemble   —— 多样性采样：N 个 provider 并行各出一个提案
  3. Aggregator —— 共识聚合：把 N 个提案合成一个最终答案
  4. Router     —— token-efficient：先判难度，简单题走单模型，难题才组队

设计原则：贵的智能只花在难题上。
"""

from __future__ import annotations
import concurrent.futures as cf
import time
from dataclasses import dataclass, field
from collections import Counter


# ── 零件 1：Provider 抽象 ────────────────────────────────
@dataclass
class Proposal:
    """一个模型交上来的一份提案。"""
    model: str
    text: str
    cost: float          # 本次调用花掉的 token 成本（估算）
    ok: bool = True      # provider 是否成功返回
    latency: float = 0.0


class Provider:
    """模型的统一接口。接真实模型时，只需重写 _generate()。"""

    def __init__(self, name: str, price_per_1k: float):
        self.name = name
        self.price_per_1k = price_per_1k

    def _generate(self, prompt: str) -> str:
        raise NotImplementedError

    def call(self, prompt: str, timeout: float = 3.0) -> Proposal:
        t0 = time.time()
        try:
            text = self._generate(prompt)
            latency = time.time() - t0
            tokens = max(len(text.split()), 1)
            cost = tokens / 1000 * self.price_per_1k
            return Proposal(self.name, text, cost, ok=True, latency=latency)
        except Exception as e:
            # 坑③：一个 provider 挂了，绝不能拖垮整支队伍
            return Proposal(self.name, f"[FAILED:{e}]", 0.0, ok=False,
                            latency=time.time() - t0)


# ── 零件 2：Ensemble 多样性采样（并行） ──────────────────
def ensemble(providers: list[Provider], prompt: str,
             timeout: float = 3.0) -> list[Proposal]:
    """N 个 provider 并行各出一份提案。多样性来自不同模型本身。"""
    proposals: list[Proposal] = []
    with cf.ThreadPoolExecutor(max_workers=len(providers)) as pool:
        futures = {pool.submit(p.call, prompt, timeout): p for p in providers}
        # 坑①：必须给整体设超时，否则一个卡死的 provider 让你永远等下去
        for fut in cf.as_completed(futures, timeout=timeout + 1):
            try:
                proposals.append(fut.result())
            except Exception:
                pass
    # 坑②：过滤掉失败/空提案，否则聚合会被污染
    return [p for p in proposals if p.ok and p.text.strip()
            and not p.text.startswith("[FAILED")]


# ── 零件 3：Aggregator 共识聚合 ──────────────────────────
def aggregate(proposals: list[Proposal]) -> str:
    """
    共识聚合：多数投票。
    坑④：投票前必须归一化，否则 'Yes' / 'yes.' / ' YES' 会被当成 3 个不同答案。
    """
    if not proposals:
        return "[NO_VALID_PROPOSAL]"

    def norm(t: str) -> str:
        return t.strip().lower().rstrip(".!。！ ")

    votes = Counter(norm(p.text) for p in proposals)
    winner_key, n = votes.most_common(1)[0]
    # 回填成原始大小写的那一份
    for p in proposals:
        if norm(p.text) == winner_key:
            return p.text.strip()
    return proposals[0].text.strip()


# ── 零件 4：Router token-efficient 路由 ──────────────────
@dataclass
class Harness:
    cheap: Provider                       # 便宜模型：处理简单题
    team: list[Provider]                  # 组队模型：处理难题
    spent: float = 0.0
    log: list[str] = field(default_factory=list)

    def is_hard(self, prompt: str) -> bool:
        """
        难度判断（最小启发式）。
        坑⑤：这里绝不能再调一次大模型来判难度——那就白省了。
        用长度 + 关键词的廉价规则先兜住 80% 的场景。
        """
        hard_kw = ("为什么", "设计", "对比", "推导", "架构", "权衡",
                   "why", "design", "compare", "trade-off")
        return len(prompt) > 40 or any(k in prompt.lower() for k in hard_kw)

    def run(self, prompt: str) -> str:
        if not self.is_hard(prompt):
            p = self.cheap.call(prompt)
            self.spent += p.cost
            self.log.append(f"[单模型 {p.model}] 成本={p.cost:.4f}")
            return p.text
        # 难题：组队
        props = ensemble(self.team, prompt)
        cost = sum(p.cost for p in props)
        self.spent += cost
        ans = aggregate(props)
        self.log.append(
            f"[组队 {len(props)}/{len(self.team)} 家] 成本={cost:.4f} "
            f"聚合={'共识' if props else '空'}")
        return ans
