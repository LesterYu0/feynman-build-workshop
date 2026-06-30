"""
费曼学AI · 造物工坊 #06 · Agent Loop 完整代码
50行核心 + 4个控制点 + Harness模板

使用方法：
1. pip install openai
2. export OPENAI_API_KEY=your_key
3. python agent_loop.py "北京今天多少度"
"""

import re
import sys
import json
import time
from typing import Callable

# ═══════════════════════════════════════════════════════════
# Step 1: 定义工具
# ═══════════════════════════════════════════════════════════

TOOLS: dict[str, Callable] = {
    "search": lambda query: f"[模拟搜索结果] {query}: 32度，晴天",
    "calculator": lambda expr: str(eval(expr)),
    "finish": lambda answer: answer,
}

TOOL_DESCRIPTIONS = """
Available tools:
- search(query): 搜索互联网获取实时信息
- calculator(expression): 数学计算
- finish(answer): 返回最终答案（必须调用此工具结束）
"""

# ═══════════════════════════════════════════════════════════
# Step 2: System Prompt — 签合同，不是聊天
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""You are a helpful agent that can use tools to answer questions.

{TOOL_DESCRIPTIONS}

To use a tool, output EXACTLY this format:
Thought: <your reasoning about what to do next>
Action: <tool_name>
Action Input: <tool_input>

When you have the final answer, use:
Thought: I have enough information to answer.
Action: finish
Action Input: <your final answer>

IMPORTANT: Always output Thought before Action. Always end with finish."""

# ═══════════════════════════════════════════════════════════
# Step 3: 解析器 — parse失败不crash，兜底返回
# ═══════════════════════════════════════════════════════════

def parse_action(response: str) -> tuple[str, str]:
    """从LLM输出中提取Action和Action Input"""
    action_match = re.search(r"Action:\s*(.+)", response)
    input_match = re.search(r"Action Input:\s*(.+)", response, re.DOTALL)
    
    if not action_match:
        # 兜底：没有Action格式，当作Final Answer
        return "finish", response.strip()
    
    action = action_match.group(1).strip()
    action_input = input_match.group(1).strip() if input_match else ""
    
    return action, action_input

# ═══════════════════════════════════════════════════════════
# Step 4: Agent Loop + 4个控制点
# ═══════════════════════════════════════════════════════════

MAX_ITERATIONS = 10          # 控制点1: 迭代上限
MAX_TOKENS = 4000            # 控制点3: Token预算（简化版用消息数代替）
MAX_MESSAGES_KEEP = 8        # 保留最近N条消息

def count_messages_tokens(messages: list) -> int:
    """简化版token计数：按字符数估算"""
    return sum(len(str(m.get("content", ""))) for m in messages)

def trim_context(messages: list) -> list:
    """控制点3: Token Budget — 滑动窗口"""
    if len(messages) <= MAX_MESSAGES_KEEP:
        return messages
    # 保留system + 最近N条
    system = [m for m in messages if m["role"] == "system"]
    recent = messages[-MAX_MESSAGES_KEEP:]
    return system + recent

def agent_loop(user_query: str, verbose: bool = True) -> dict:
    """
    Agent Loop主体 — 50行核心 + 4个控制点
    
    Returns: {"answer": str, "iterations": int, "complete": bool, "trace": list}
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    
    trace = []  # Harness组件: Tracing
    
    for i in range(MAX_ITERATIONS):  # 控制点1: Max Iterations
        # ─── Reason: LLM决定下一步 ───
        # 这里用模拟LLM响应（实际替换为openai.chat.completions.create）
        response = simulate_llm(messages, i)
        messages.append({"role": "assistant", "content": response})
        
        # ─── Parse: 提取action ───
        action, action_input = parse_action(response)
        
        # ─── 控制点4: 终止条件（三重兜底）───
        if action == "finish":                    # 条件1: action是finish
            trace.append({"iter": i+1, "action": "finish", "result": action_input})
            return {"answer": action_input, "iterations": i+1, "complete": True, "trace": trace}
        
        if "Final Answer" in response:            # 条件2: 含Final Answer关键词
            answer = response.split("Final Answer")[-1].strip().lstrip(":").strip()
            trace.append({"iter": i+1, "action": "final_answer_keyword", "result": answer})
            return {"answer": answer, "iterations": i+1, "complete": True, "trace": trace}
        
        # ─── Act: 调用工具 ───
        try:                                      # 控制点2: 错误恢复
            if action not in TOOLS:
                result = f"Tool Error: Unknown tool '{action}'. Available: {list(TOOLS.keys())}"
            else:
                result = TOOLS[action](action_input)
        except Exception as e:
            result = f"Tool Error: {str(e)}. Try a different approach."
        
        # ─── Observe: 喂回结果 ───
        messages.append({"role": "user", "content": f"Observation: {result}"})
        
        # ─── Tracing ───
        trace.append({
            "iter": i+1,
            "action": action,
            "input": action_input,
            "result": str(result)[:200],
            "tokens": count_messages_tokens(messages),
        })
        
        if verbose:
            print(f"  [Iter {i+1}] Action: {action}({action_input}) → {str(result)[:80]}")
        
        # ─── 控制点3: Token Budget ───
        messages = trim_context(messages)
    
    # 控制点1触发: 达到上限
    return {
        "answer": "达到最大迭代次数，返回部分结果",
        "iterations": MAX_ITERATIONS,
        "complete": False,
        "trace": trace,
    }

# ═══════════════════════════════════════════════════════════
# 模拟LLM（替换为真实API调用）
# ═══════════════════════════════════════════════════════════

def simulate_llm(messages: list, iteration: int) -> str:
    """模拟LLM响应 — 实际使用时替换为OpenAI API"""
    user_query = messages[1]["content"]
    
    if iteration == 0:
        return f"Thought: 用户问了'{user_query}'，我需要搜索获取信息。\nAction: search\nAction Input: {user_query}"
    else:
        # 找到上一轮的observation
        last_obs = ""
        for m in reversed(messages):
            if m["role"] == "user" and "Observation:" in m.get("content", ""):
                last_obs = m["content"].replace("Observation: ", "")
                break
        return f"Thought: 我已经获得了信息：{last_obs}。可以回答了。\nAction: finish\nAction Input: 根据搜索结果，{last_obs}"

# ═══════════════════════════════════════════════════════════
# 运行
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "北京今天多少度？"
    
    print(f"\n{'='*60}")
    print(f"  Agent Loop — 费曼学AI 造物工坊#06")
    print(f"{'='*60}")
    print(f"\n  Query: {query}\n")
    
    start = time.time()
    result = agent_loop(query)
    elapsed = time.time() - start
    
    print(f"\n{'─'*60}")
    print(f"  Answer: {result['answer']}")
    print(f"  Iterations: {result['iterations']}")
    print(f"  Complete: {result['complete']}")
    print(f"  Time: {elapsed:.2f}s")
    print(f"{'─'*60}")
    
    if result["trace"]:
        print(f"\n  Trace:")
        for t in result["trace"]:
            print(f"    [{t['iter']}] {t['action']} → {str(t.get('result',''))[:60]}")
