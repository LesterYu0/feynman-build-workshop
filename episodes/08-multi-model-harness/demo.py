"""
demo.py — 用 mock 模型跑通 mini_harness
=========================================
没有真实 API key 也能跑：mock provider 模拟延迟、偶发超时、失败。
换成真实模型：把 MockProvider 换成你自己实现 _generate() 的 Provider 即可。
"""

import random
import time
from mini_harness import Provider, Harness, ensemble, aggregate

random.seed(7)


class MockProvider(Provider):
    """模拟一个国产模型：有延迟、偶尔超时、偶尔给出不同答案。"""

    def __init__(self, name, price, answers, fail_rate=0.0, slow=0.0):
        super().__init__(name, price)
        self.answers = answers
        self.fail_rate = fail_rate
        self.slow = slow

    def _generate(self, prompt: str) -> str:
        time.sleep(random.uniform(0.05, 0.2) + self.slow)
        if random.random() < self.fail_rate:
            raise RuntimeError("timeout")
        return random.choice(self.answers)


def line(title):
    print("\n" + "=" * 54 + f"\n {title}\n" + "=" * 54)


# 4 个「国产模型」组成的队伍（对难题各出提案）
deepseek = MockProvider("DeepSeek-v4", 1.0,
                        ["用 MoE + 长上下文，先拆子任务再并行检索。"], slow=0.0)
glm      = MockProvider("GLM-5.2", 1.2,
                        ["用 MoE + 长上下文，先拆子任务再并行检索。"], slow=0.0)
kimi     = MockProvider("Kimi-K2.7", 0.9,
                        ["先做多路检索，再用长上下文一次性推理。"], fail_rate=0.5)
qwen     = MockProvider("Qwen3.7", 0.8,
                        ["用 MoE + 长上下文，先拆子任务再并行检索。"], slow=0.0)

# 便宜模型：处理简单题
cheap = MockProvider("Qwen3.7-Flash", 0.2, ["北京。"])

harness = Harness(cheap=cheap, team=[deepseek, glm, kimi, qwen])

# ── 场景 1：简单题 → 单模型（省钱） ──
line("场景 1｜简单题：中国的首都是？")
print("答案:", harness.run("中国的首都是？"))

# ── 场景 2：难题 → 组队 + 共识聚合 ──
line("场景 2｜难题：为什么多模型组队能超过单个旗舰模型？请给设计思路")
q = "为什么多模型组队能超过单个旗舰模型？请给出核心设计思路与权衡"
print("答案:", harness.run(q))

# ── 场景 3：直接看组队内部：4 家并行提案 + 聚合 ──
line("场景 3｜掀开引擎盖：看 4 家并行提案")
props = ensemble(harness.team, q)
for p in props:
    print(f"  · {p.model:<14} lat={p.latency:.2f}s cost={p.cost:.4f}  {p.text}")
print(f"  → 成功 {len(props)}/4 家（其余超时被降级过滤）")
print("  → 共识聚合结果:", aggregate(props))

# ── 账单：证明省了钱 ──
line("账单")
for l in harness.log:
    print(" ", l)
print(f"\n  本轮总成本: {harness.spent:.4f}")
print("  对照：若每题都无脑丢给整支队伍，成本会翻数倍。")
