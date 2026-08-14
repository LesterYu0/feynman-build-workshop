"""
头条坑真跑：plan 阶段模型偷偷调写工具
======================================
paaatrick.com 拆解 Claude Code / Codex / OpenCode 后最深结论：
  Plan Mode 不是先有完美工程限制再让模型进去，
  而是先相信模型遵守"先别动手"的规则，再补工程兜底。

本 demo 复现：plan 阶段 LLM 违规吐出 write_file 调用。
  - 软约束（仅 system prompt 说"别写"）→ 写操作真的执行了（翻车）
  - 硬拦截（代码层权限闸门）→ 直接抛异常拦下（真护栏）
"""
from plan_mode_minimal import WRITE_TOOLS, PermissionDenied


class SoftGuardAgent:
    """只靠 prompt 约束：执行工具前不检查权限。"""
    def __init__(self): self.permission = "readonly"
    def run_tool(self, name, **kw):
        # ❌ 没有代码层检查，完全信任模型遵守 prompt
        return f"[执行] {name} -> 副作用已产生（文件被改/命令已跑）"


class HardGuardAgent:
    """代码层权限闸门：plan 阶段任何写操作硬拦截。"""
    def __init__(self): self.permission = "readonly"
    def run_tool(self, name, **kw):
        if self.permission == "readonly" and name in WRITE_TOOLS:
            raise PermissionDenied(f"🛑 权限闸门拦截：plan 阶段禁止写操作 `{name}`")
        return f"[执行] {name} -> ok"


def main():
    print("=" * 64)
    print("头条坑 demo：plan 阶段模型偷偷调写工具")
    print("=" * 64)

    # 模型在 plan 阶段违规吐出的工具调用（真实常见）
    rogue_call = ("write_file", {"path": "config.py", "content": "BREAK_EVERYTHING=True"})

    print("\n--- 软约束（仅 prompt 说'别写'）---")
    soft = SoftGuardAgent()
    out = soft.run_tool(rogue_call[0], **rogue_call[1])
    print(f"  结果: {out}")
    print("  ❌ 计划阶段就把文件改了——模型没遵守 prompt，副作用已发生")

    print("\n--- 硬拦截（代码层权限闸门）---")
    hard = HardGuardAgent()
    try:
        hard.run_tool(rogue_call[0], **rogue_call[1])
    except PermissionDenied as e:
        print(f"  {e}")
    print("  ✅ 写操作被代码层拦下，计划阶段零副作用")


if __name__ == "__main__":
    main()
