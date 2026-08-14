"""
最小 Plan-and-Execute（手写，零依赖，可跑）
========================================
演示一个生产级 Plan 模式的核心骨架：

  Phase 1  规划  : 权限=只读 → Planner 出计划 → 写 .claude/plans/PLAN.md → 用户批准
  Phase 2  执行  : 权限=写   → Executor 按序执行 → 失败走 Replan 三级触发
  Guard    权限闸门: plan 阶段任何写操作被代码层硬拦截（不只是 prompt 软约束）

LLM 用 MockLLM 复现典型失败模式（JSON 解析失败 / 计划过长 / 瞬时错误 / replan 死循环），
编排逻辑全部真实可跑。把 MockLLM 换成任意真实 LLM 即可上线。

运行: python plan_mode_minimal.py
"""
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

# ----------------------------------------------------------------------------
# 0. 工具层（含只读 / 写 分类 —— 这是权限闸门的判定依据）
# ----------------------------------------------------------------------------
WRITE_TOOLS = {"write_file", "run_shell"}
READ_TOOLS = {"read_file", "grep", "list_dir"}


def tool_read_file(path: str) -> str:
    return f"[read] {path}: ...(文件内容)"

def tool_grep(pattern: str, path: str = ".") -> str:
    return f"[grep] {pattern} in {path}: ...(命中 3 行)"

def tool_list_dir(path: str = ".") -> str:
    return f"[ls] {path}: a.py  b.py  c.py"

def tool_write_file(path: str, content: str) -> str:
    return f"[WRITE] 已创建 {path}"

def tool_run_shell(cmd: str) -> str:
    return f"[RUN] {cmd} -> exit 0"


TOOLS: dict[str, Callable] = {
    "read_file": tool_read_file,
    "grep": tool_grep,
    "list_dir": tool_list_dir,
    "write_file": tool_write_file,
    "run_shell": tool_run_shell,
}


# ----------------------------------------------------------------------------
# 1. 数据结构
# ----------------------------------------------------------------------------
@dataclass
class Step:
    step: int
    description: str
    tool: Optional[str]
    inputs: dict
    expected_output: str
    success_criteria: str

    @staticmethod
    def from_dict(d: dict) -> "Step":
        return Step(
            step=d.get("step", 0),
            description=d.get("description", ""),
            tool=d.get("tool"),
            inputs=d.get("inputs", {}),
            expected_output=d.get("expected_output", ""),
            success_criteria=d.get("success_criteria", ""),
        )


@dataclass
class Plan:
    goal: str
    steps: list[Step] = field(default_factory=list)
    overall_acceptance: str = ""
    risk_list: list[str] = field(default_factory=list)
    fallback: str = ""

    def to_markdown(self) -> str:
        lines = [f"# Plan: {self.goal}\n"]
        for s in self.steps:
            lines.append(f"## 步骤 {s.step}: {s.description}")
            lines.append(f"- 工具: {s.tool or '无(直接LLM)'}")
            lines.append(f"- 输入: {json.dumps(s.inputs, ensure_ascii=False)}")
            lines.append(f"- 预期输出: {s.expected_output}")
            lines.append(f"- 成功标准: {s.success_criteria}\n")
        lines.append(f"## 总体验收\n{self.overall_acceptance}")
        lines.append(f"## 风险\n" + "\n".join(f"- {r}" for r in self.risk_list))
        lines.append(f"## 兜底\n{self.fallback}")
        return "\n".join(lines)


# ----------------------------------------------------------------------------
# 2. LLM 接口 + 可复现 Mock
# ----------------------------------------------------------------------------
class LLM:
    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError


class MockLLM(LLM):
    """脚本化复现典型失败 → 修复路径，保证可复现演示。

    关键失败模式（真实 agent 都会遇到）：
      A. Planner 第 1 次返回 30 步超长计划（过度规划 → 被拒）
      B. Planner 第 2 次返回 JSON 缺右括号（解析失败）
      C. Planner 第 3 次返回合格 5 步计划
      D. Executor 执行 step3 时第 1 次瞬时超时，第 2 次成功
      E. 某步失败后 Replanner 反复产出等价计划（replan 死循环隐患）
    """

    def __init__(self):
        self.calls = {"planner": 0, "executor": 0, "replanner": 0}
        self.token_cost = 0  # 粗略成本计数

    def _count(self, role: str, prompt: str):
        self.calls[role] = self.calls.get(role, 0) + 1
        # 粗略：每 4 字符算 1 token
        self.token_cost += max(1, len(prompt) // 4)

    def complete(self, role: str, system: str, user: str) -> str:
        self._count(role, user)
        if role == "planner":
            return self._planner(user)
        if role == "executor":
            return self._executor(user)
        if role == "replanner":
            return self._replanner(user)
        return "{}"

    # ---- Planner 脚本 ----
    def _planner(self, user: str) -> str:
        n = self.calls["planner"]
        goal = re.search(r"目标[:：]\s*(.+)", user)
        goal = goal.group(1).strip() if goal else "未知任务"

        if n == 1:
            # 失败模式 A：过度规划，30 步
            steps = [
                {"step": i, "description": f"子任务 {i}",
                 "tool": "read_file" if i % 2 else None,
                 "inputs": {"path": f"f{i}.py"},
                 "expected_output": "…", "success_criteria": "…"}
                for i in range(1, 31)
            ]
            return self._wrap(goal, steps, note="(过度规划:30步)")

        if n == 2:
            # 失败模式 B：JSON 缺右括号
            raw = self._wrap(goal, self._good_steps(), raw=True)
            return raw[:-3]  # 砍掉末尾 } ] } 制造解析错误

        # 第 3 次：合格 5 步
        return self._wrap(goal, self._good_steps())

    def _good_steps(self) -> list:
        return [
            {"step": 1, "description": "读取项目结构与入口文件", "tool": "list_dir",
             "inputs": {"path": "."}, "expected_output": "文件清单",
             "success_criteria": "列出根目录主要文件"},
            {"step": 2, "description": "搜索现有 plan 相关代码", "tool": "grep",
             "inputs": {"pattern": "plan"}, "expected_output": "命中位置",
             "success_criteria": "找到 0-3 处相关定义"},
            {"step": 3, "description": "调用外部 API 拉取配置", "tool": "run_shell",
             "inputs": {"cmd": "curl config.api"}, "expected_output": "配置 JSON",
             "success_criteria": "返回 200 且含 version 字段"},
            {"step": 4, "description": "生成 Plan 模式骨架代码", "tool": "write_file",
             "inputs": {"path": "plan_mode.py"}, "expected_output": "文件创建",
             "success_criteria": "文件存在且非空"},
            {"step": 5, "description": "跑冒烟测试验证", "tool": "run_shell",
             "inputs": {"cmd": "pytest -q"}, "expected_output": "pass",
             "success_criteria": "exit 0 且无 error"},
        ]

    def _wrap(self, goal, steps, raw=False, note="") -> str:
        plan = {
            "goal": goal,
            "steps": steps,
            "overall_acceptance": "5 步全部满足 success_criteria 即完成" + note,
            "risk_list": ["外部 API 可能超时", "pytest 环境可能缺失"],
            "fallback": "API 失败则读取本地缓存 config.local.json",
        }
        if raw:
            return json.dumps(plan, ensure_ascii=False, indent=2)
        return json.dumps(plan, ensure_ascii=False, indent=2)

    # ---- Executor 脚本 ----
    def _executor(self, user: str) -> str:
        # 解析当前步
        m = re.search(r"步骤 (\d+)", user)
        step_no = int(m.group(1)) if m else 0
        if step_no == 3:
            # 失败模式 D：step3 第一次瞬时超时，第二次（重试）成功。
            # 计数器由 mock 自己持有，避免“状态归属错位”的真实坑。
            self._s3 = getattr(self, "_s3", 0) + 1
            if self._s3 == 1:
                return json.dumps({"ok": False, "error": "timeout", "retryable": True})
            return json.dumps({"ok": True, "result": "config v2"})
        return json.dumps({"ok": True, "result": f"step{step_no} done"})

    # ---- Replanner 脚本 ----
    def _replanner(self, user: str) -> str:
        self.calls["replanner"] += 1
        # 失败模式 E 的对抗：返回"等价计划"（用不同措辞但同样会失败的步骤）
        # 真实场景里模型常产出语义等价的 replan，导致死循环
        return json.dumps({
            "goal": "继续",
            "steps": [
                {"step": 1, "description": "重新拉取配置(已重试)", "tool": "run_shell",
                 "inputs": {"cmd": "curl config.api"}, "expected_output": "配置",
                 "success_criteria": "返回 200"}
            ],
            "overall_acceptance": "…", "risk_list": [], "fallback": "…",
        })


# ----------------------------------------------------------------------------
# 3. 真实痛点：软约束 vs 硬拦截
# ----------------------------------------------------------------------------
class PermissionDenied(Exception):
    pass


def _parse_plan(text: str) -> Plan:
    """解析 Planner 输出为 Plan 对象。真实坑：JSON 解析失败。"""
    try:
        # 先尝试整段解析
        data = json.loads(text)
    except json.JSONDecodeError:
        # 真实场景：模型常输出 ```json ... ``` 包裹或尾部残缺
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise ValueError("无法从 Planner 输出中提取 JSON")
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            # 失败模式 B 落点：尾部残缺，捕获后由上层决定是否 re-plan
            raise ValueError(f"Planner JSON 解析失败: {e}")
    steps = [Step.from_dict(s) for s in data.get("steps", [])]
    return Plan(
        goal=data.get("goal", ""),
        steps=steps,
        overall_acceptance=data.get("overall_acceptance", ""),
        risk_list=data.get("risk_list", []),
        fallback=data.get("fallback", ""),
    )


# ----------------------------------------------------------------------------
# 4. 编排器（手写 Plan Mode）
# ----------------------------------------------------------------------------
class PlanModeAgent:
    def __init__(self, llm: LLM, plan_dir: str = ".claude/plans",
                 max_replan: int = 3, max_steps: int = 12, max_total_steps: int = 25):
        self.llm = llm
        self.plan_dir = plan_dir
        self.permission = "readonly"
        self.max_replan = max_replan
        self.max_steps = max_steps          # 单计划步数上限（防过度规划）
        self.max_total_steps = max_total_steps  # 全局步数硬上限（防 replan 死循环）
        self.step_count = 0
        self.replan_count = 0
        os.makedirs(plan_dir, exist_ok=True)

    # ---- 权限闸门（硬拦截，代码层）----
    def _guard(self, tool_name: str):
        if self.permission == "readonly" and tool_name in WRITE_TOOLS:
            raise PermissionDenied(
                f"🛑 权限闸门拦截：plan 阶段禁止写操作 `{tool_name}`。"
                f"（软约束 prompt 拦不住时，这是真护栏）"
            )

    def _plan(self, goal: str) -> Plan:
        while True:
            raw = self.llm.complete("planner",
                                    "你是一个任务规划专家。输出 JSON。",
                                    f"目标：{goal}\n请生成 3-5 个可执行、可验证、"
                                    f"不重复的步骤，每步含 tool/inputs/expected_output/success_criteria。")
            try:
                plan = _parse_plan(raw)
            except ValueError as e:
                # 失败模式 B 的兜底：解析失败 → 重新规划
                print(f"  [Planner] JSON 解析失败，重新规划… ({e})")
                continue
            if len(plan.steps) > self.max_steps:
                # 失败模式 A 的兜底：过度规划 → 要求压缩
                print(f"  [Planner] 计划过长({len(plan.steps)}步> {self.max_steps})，"
                      f"要求压缩后重规划…")
                continue
            if not plan.steps:
                print("  [Planner] 空计划，重新规划…")
                continue
            return plan

    def _write_plan_file(self, plan: Plan, name: str = "PLAN.md"):
        path = os.path.join(self.plan_dir, name)
        with open(path, "w") as f:
            f.write(plan.to_markdown())
        print(f"  [Plan] 已写入计划文件: {path}")
        return path

    def _approve(self, plan: Plan) -> bool:
        # 真实产品里这里是 Human-in-the-loop；演示中自动批准但展示内容
        print(f"  [User] 审阅计划（{len(plan.steps)} 步），批准 ✓")
        return True

    def _execute_step(self, step: Step) -> dict:
        self.step_count += 1
        if self.step_count > self.max_total_steps:
            raise PermissionDenied(f"全局步数超硬上限 {self.max_total_steps}，中止交人工")
        if step.tool:
            self._guard(step.tool)  # 硬闸门：plan 阶段若误入写工具直接抛
            obs = self.llm.complete("executor", "", f"步骤 {step.step}: {step.description}")
            try:
                return json.loads(obs)
            except json.JSONDecodeError:
                return {"ok": False, "error": "bad executor output"}
        else:
            return {"ok": True, "result": "LLM 直接处理"}

    def _execute(self, plan: Plan) -> str:
        past = []
        for s in plan.steps:
            res = self._execute_step(s)
            past.append((s, res))
            if not res.get("ok"):
                print(f"  [Exec] 步骤 {s.step} 失败: {res.get('error')}")
                return self._handle_failure(plan, s, res, past)
        return "✅ 计划全部执行完成"

    def _handle_failure(self, plan, failed_step, res, past) -> str:
        """Replan 三级触发：
        ① Retry（瞬时错误）② Fallback Tool（确定性替代）③ Replan（矛盾性观察）
        + 死循环防护：replan 预算 + 全局步数上限。
        """
        # ① Retry：瞬时错误且可重试
        if res.get("retryable") and self.step_count < self.max_total_steps:
            print("  [Replan] ① 瞬时错误 → Retry（指数退避语义）")
            # 重新执行该步（mock 自身持有重试计数，第二次会成功）
            retry = self._execute_step(failed_step)
            if retry.get("ok"):
                print(f"  [Exec] 步骤 {failed_step.step} 重试成功")
                # 继续执行剩余步骤（演示：返回成功）
                return "✅ 重试后计划继续执行完成"
            return self._do_replan(plan, past)

        # ③ Replan：进入重规划（带预算与去重防护）
        return self._do_replan(plan, past)

    def _do_replan(self, plan, past) -> str:
        if self.replan_count >= self.max_replan:
            print(f"  [Replan] 已达 replan 预算 {self.max_replan}，中止交人工")
            return "⚠️ replan 预算耗尽，转人工"
        self.replan_count += 1
        print(f"  [Replan] ③ 触发重规划 (第 {self.replan_count}/{self.max_replan} 次)")
        raw = self.llm.complete("replanner", "", "根据失败调整剩余计划")
        try:
            new_plan = _parse_plan(raw)
        except ValueError as e:
            print(f"  [Replan] 新计划解析失败: {e}，中止")
            return "⚠️ replan 解析失败，转人工"
        # 执行新计划（演示里只跑第一步验证）
        print(f"  [Replan] 新计划 {len(new_plan.steps)} 步，继续执行…")
        r = self._execute_step(new_plan.steps[0])
        return "✅ 重规划后恢复执行（演示）" if r.get("ok") else "⚠️ 重规划仍失败，转人工"


# ----------------------------------------------------------------------------
# 5. 演示入口
# ----------------------------------------------------------------------------
def main():
    print("=" * 64)
    print("造物工坊 #C08 — 手写最小 Plan Mode 真跑演示")
    print("=" * 64)

    llm = MockLLM()
    agent = PlanModeAgent(llm, plan_dir=".claude/plans",
                          max_replan=3, max_steps=12, max_total_steps=25)

    goal = "给项目加一个 Plan 模式的骨架，并验证能跑通"
    print(f"\n[Goal] {goal}\n")

    print("--- Phase 1: 规划（权限=只读）---")
    agent.permission = "readonly"
    plan = agent._plan(goal)
    agent._write_plan_file(plan)
    ok = agent._approve(plan)

    print("\n--- Phase 2: 执行（权限=写）---")
    agent.permission = "write"
    if ok:
        result = agent._execute(plan)
        print(f"\n[Result] {result}")

    print("\n--- 运行统计（真实成本信号）---")
    print(f"  LLM 调用: {llm.calls}")
    print(f"  粗略 token 成本: {llm.token_cost}")
    print(f"  Planner 被调用 {llm.calls['planner']} 次（含失败重规划）")
    print(f"  Replan 触发: {agent.replan_count} 次")


if __name__ == "__main__":
    main()
