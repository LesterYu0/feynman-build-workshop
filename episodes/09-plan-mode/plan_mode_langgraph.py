"""
Plan-and-Execute 的 LangGraph 生产落地版
========================================
对照手写版 plan_mode_minimal.py：框架替你管好了
  - 循环（while 不用自己写）
  - 状态（past_steps / plan 自动传递）
  - 条件边（should_end：继续还是收尾）
  - 重规划（replanner 节点）

依赖: pip install langgraph
运行: python plan_mode_langgraph.py   （LLM 用 MockLLM，可替换为真实模型）

设计要点（与手写版一致，但更省样板代码）：
  - Planner 出计划（List[str]）
  - Executor 取计划第 1 步执行，结果 append 到 past_steps，并从 plan 弹出
  - Replanner 判断是否继续（返回新 plan）还是直接给最终答案
  - should_end 条件边决定流向
"""
from typing import TypedDict, List, Optional, Annotated
import operator
from langgraph.graph import StateGraph, END


# ----------------------------------------------------------------------------
# 0. 状态
# ----------------------------------------------------------------------------
class PlanExecuteState(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[tuple], operator.add]
    response: Optional[str]


# ----------------------------------------------------------------------------
# 1. Mock LLM（与手写版同款失败模式：步骤3首次瞬时超时）
# ----------------------------------------------------------------------------
class MockLLM:
    """LangGraph 版 mock：清晰跑完 5 步，重点演示「框架替你管循环/状态」。
    （失败重试的故事交给手写版 plan_mode_minimal.py 讲，这里保持干净。）"""

    def plan(self, goal: str) -> List[str]:
        return [
            "读取项目结构与入口文件",
            "搜索现有 plan 相关代码",
            "调用外部 API 拉取配置",
            "生成 Plan 模式骨架代码",
            "跑冒烟测试验证",
        ]

    def act(self, step: str) -> str:
        return f"done: {step[:12]}"

    def replan(self, state: PlanExecuteState) -> List[str]:
        # 演示用：正常不会走到（除非某步失败）
        return ["重新拉取配置(已重试)"]


# ----------------------------------------------------------------------------
# 2. 节点（纯函数：输入 state，返回 state 增量）
# ----------------------------------------------------------------------------
llm = MockLLM()


def planner(state: PlanExecuteState) -> dict:
    """生成完整计划。真实场景里换成 LLM 调用。"""
    print(f"  [Planner] 生成计划（{len(llm.plan(state['input']))} 步）")
    return {"plan": llm.plan(state["input"])}


def executor(state: PlanExecuteState) -> dict:
    """执行计划第 1 步，结果记入 past_steps，并从 plan 弹出该步。"""
    task = state["plan"][0]
    print(f"  [Executor] 执行: {task}")
    result = llm.act(task)
    if result.startswith("ERROR:"):
        # 失败：把错误也记入 past_steps，交给 replanner 判断
        print(f"  [Executor] 失败: {result}")
        return {"past_steps": [(task, result)], "plan": state["plan"][1:]}
    return {"past_steps": [(task, result)], "plan": state["plan"][1:]}


def replanner(state: PlanExecuteState) -> dict:
    """判断流向（关键：只有「计划真的空了」才收尾，否则继续 executor）。
    注意：这里曾踩坑——最初写成「上一步成功就收尾」，导致只跑 1 步就结束。
    正确条件必须看 state['plan'] 是否为空。"""
    last_task, last_result = state["past_steps"][-1]
    if last_result.startswith("ERROR:"):
        print("  [Replanner] 检测到失败 → 调整计划")
        return {"plan": llm.replan(state)}
    if not state["plan"]:  # 计划已空 → 汇总最终答案
        summary = " | ".join(f"{t}→{r}" for t, r in state["past_steps"])
        print("  [Replanner] 计划执行完毕 → 生成最终答案")
        return {"response": f"✅ 完成: {summary}"}
    # 计划还有步骤且上一步成功 → 不返回 response，should_end 会继续 executor
    return {}


def should_end(state: PlanExecuteState) -> str:
    """条件边：有 response 就结束，否则继续 executor。"""
    return "executor" if not state.get("response") else "end"


# ----------------------------------------------------------------------------
# 3. 组装图
# ----------------------------------------------------------------------------
def build_graph():
    g = StateGraph(PlanExecuteState)
    g.add_node("planner", planner)
    g.add_node("executor", executor)
    g.add_node("replanner", replanner)
    g.set_entry_point("planner")
    g.add_edge("planner", "executor")
    g.add_edge("executor", "replanner")
    g.add_conditional_edges("replanner", should_end, {"executor": "executor", "end": END})
    return g.compile()


def main():
    print("=" * 64)
    print("造物工坊 #C08 — LangGraph 版 Plan-and-Execute")
    print("=" * 64)
    app = build_graph()
    goal = "给项目加一个 Plan 模式的骨架，并验证能跑通"
    result = app.invoke({"input": goal, "plan": [], "past_steps": [], "response": None})
    print(f"\n[Final] {result['response']}")


if __name__ == "__main__":
    main()
