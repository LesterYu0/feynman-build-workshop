#!/usr/bin/env python3
"""
资产 #2：四层漏斗意图路由系统 — 代码骨架
改三个配置就能接入你的 Agent：
  1. RULES (L0 正则规则)
  2. ROUTE_DEFINITIONS (L1 意图 + 例句)
  3. SIMULATED_FC (L2 大模型回调)
"""

import re
import time
from typing import Optional, Any
from dataclasses import dataclass, field

# ============================================================
# CONFIG ①: L0 — 正则规则
# ============================================================
RULES = [
    (r'^/(help|帮助|start)', 'HELP'),
    (r'^/(weather|天气)', 'WEATHER'),
    (r'^/(cancel|取消)', 'CANCEL'),
    # 添加你自己的命令...
]

# 预编译正则 —— 必须模块级！
_L0_PATTERNS = [(re.compile(p, re.IGNORECASE), intent) for p, intent in RULES]
TRIE = {}  # 可选：Trie 加速长命令匹配


# ============================================================
# CONFIG ②: L1 — 向量路由例句
# ============================================================
@dataclass
class Route:
    name: str
    utterances: list[str]
    threshold: float = 0.65

    def embed(self, encoder: Any):
        """用编码器对例句批量编码"""
        self.vectors = [encoder.encode(u) for u in self.utterances]

ROUTE_DEFINITIONS = [
    Route('REFUND', ['退款', '退钱', '我要退货', '这个订单帮我取消', '钱退哪里', '不想要了能退吗', '怎么退', '申请退款']),
    Route('BOOKING', ['订票', '预订', '帮我订', '我要订', '订机票', '订酒店', '订火车票', '怎么订', '查航班', '查火车']),
    Route('ORDER_QUERY', ['查订单', '我的订单', '订单到哪了', '物流', '快递', '什么时候发货', '订单状态']),
    Route('COMPLAINT', ['投诉', '举报', '客服', '我要投诉', '服务太差', '态度不好']),
    Route('FAQ', ['怎么用', '怎么操作', '帮助', '使用说明', '教程', '常见问题', '收费标准']),
    # 添加你自己的业务意图...
]


# ============================================================
# CONFIG ③: L2 — 大模型回调
# ============================================================
async def SIMULATED_FC(query: str, context: dict) -> dict:
    """
    生产环境替换为真实 API 调用。
    返回：{ "intent": str, "confidence": float, "slots": dict }
    """
    # TODO: 替换为你的 LLM 调用
    # response = await client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=[...],
    #     response_format={"type": "json_schema", ...},
    #     temperature=0,  # 分类永远用 0
    # )
    return {"intent": "FAQ", "confidence": 0.92, "slots": {}}


# ============================================================
# 路由核心
# ============================================================
@dataclass
class RouteResult:
    intent: str
    confidence: float
    layer: str  # "L0" | "L1" | "L2" | "OOD" | "CLARIFY"
    slots: dict = field(default_factory=dict)
    fallback_needed: bool = False

class IntentRouter:
    def __init__(self):
        self.stats = {"L0": 0, "L1": 0, "L2": 0, "OOD": 0, "CLARIFY": 0}
        # 熔断状态
        self._low_confidence_streak = 0
        self._breaker_open = False
        self._breaker_rounds_remaining = 0

    def route(self, query: str, context: Optional[dict] = None) -> RouteResult:
        query = query.strip()

        # ── L0: 正则匹配 ──
        for pattern, intent in _L0_PATTERNS:
            if pattern.match(query):
                self.stats["L0"] += 1
                return RouteResult(intent=intent, confidence=1.0, layer="L0")

        # ── 熔断检查 ──
        if self._breaker_open:
            if self._breaker_rounds_remaining > 0:
                self._breaker_rounds_remaining -= 1
                return RouteResult(intent="FALLBACK", confidence=0.0, layer="BREAKER", fallback_needed=True)
            else:
                self._breaker_open = False

        # ── L1: 向量匹配 (简化版: 精确 + 包含匹配) ──
        for route in ROUTE_DEFINITIONS:
            for utterance in route.utterances:
                if utterance in query:
                    self.stats["L1"] += 1
                    return RouteResult(intent=route.name, confidence=0.85, layer="L1")

        # ── L2: 大模型 FC ──
        # 同步简化版；生产环境用 asyncio
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 运行中的 event loop — 用线程池模拟
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, SIMULATED_FC(query, context or {}))
                    result = future.result(timeout=3.0)
            else:
                result = loop.run_until_complete(SIMULATED_FC(query, context or {}))
        except RuntimeError:
            result = asyncio.run(SIMULATED_FC(query, context or {}))

        confidence = result.get("confidence", 0.0)
        intent = result.get("intent", "UNKNOWN")

        # ── Safe Net: 置信度分级 ──
        if confidence < 0.4:
            self.stats["OOD"] += 1
            self._low_confidence_streak += 1
            if self._low_confidence_streak >= 3:
                self._breaker_open = True
                self._breaker_rounds_remaining = 5
            return RouteResult(intent="OOD", confidence=confidence, layer="OOD")

        if confidence < 0.6:
            self.stats["CLARIFY"] += 1
            self._low_confidence_streak += 1
            return RouteResult(intent=intent, confidence=confidence, layer="CLARIFY",
                               slots={"missing": "需要反问澄清"})

        # 置信度 >= 0.6 → 正常
        self._low_confidence_streak = 0
        if confidence >= 0.8:
            self.stats["L2"] += 1
            return RouteResult(intent=intent, confidence=confidence, layer="L2", slots=result.get("slots", {}))
        else:
            # 0.6~0.8: 执行+复核
            self.stats["L2"] += 1
            return RouteResult(intent=intent, confidence=confidence, layer="L2",
                               slots=result.get("slots", {}),
                               fallback_needed=True)


# ============================================================
# 测试
# ============================================================
def run_tests():
    router = IntentRouter()
    tests = [
        # (输入, 期望意图, 期望层)
        ("/weather", "WEATHER", "L0"),
        ("/help", "HELP", "L0"),
        ("我要退款", "REFUND", "L1"),
        ("帮我退钱", "REFUND", "L1"),
        ("订机票", "BOOKING", "L1"),
        ("查一下订单", "ORDER_QUERY", "L1"),
        ("帮我写首诗", "OOD", "OOD"),
        ("哈哈哈哈", "OOD", "OOD"),
    ]

    passed = 0
    for query, expected_intent, expected_layer in tests:
        result = router.route(query)
        ok = result.intent == expected_intent and result.layer == expected_layer
        if ok:
            passed += 1
            print(f"  ✓ {query} → {result.intent} ({result.layer})")
        else:
            print(f"  ✗ {query} → {result.intent} ({result.layer})  expected {expected_intent} ({expected_layer})")

    print(f"\n  {passed}/{len(tests)} passed")
    print(f"  Stats: {router.stats}")
    return passed == len(tests)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        ok = run_tests()
        sys.exit(0 if ok else 1)
    else:
        # Interactive demo
        router = IntentRouter()
        print("四层漏斗意图路由系统 ready。输入 query 测试（exit 退出）：")
        while True:
            q = input("> ")
            if q.lower() == 'exit':
                break
            r = router.route(q)
            print(f"  → {r.intent} (confidence={r.confidence}, layer={r.layer})")
            if r.slots:
                print(f"    slots: {r.slots}")
