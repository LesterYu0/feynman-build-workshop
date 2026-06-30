"""
费曼学AI · 造物工坊 #06 · Harness模板
从Agent Loop到可部署的Agent服务

使用方法：
1. pip install openai fastapi uvicorn
2. 修改 SYSTEM_PROMPT 和 TOOLS 适配你的场景
3. uvicorn harness_template:app --reload
4. curl -X POST http://localhost:8000/agent -d '{"query": "你的问题"}'
"""

import re
import json
import time
import logging
from typing import Callable
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════
# Harness 组件1: 配置（可YAML/JSON化）
# ═══════════════════════════════════════════════════════════

@dataclass
class AgentConfig:
    """Agent配置 — 生产环境建议用YAML文件加载"""
    max_iterations: int = 10
    max_messages_keep: int = 8
    max_retries: int = 3
    timeout_seconds: float = 30.0
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    verbose: bool = True


# ═══════════════════════════════════════════════════════════
# Harness 组件2: System Prompt 架构
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT_TEMPLATE = """
# Role
你是一个{role_description}

# Constraints
{constraints}

# Tools
{tools_description}

# Output Format
要使用工具，请输出:
Thought: <推理过程>
Action: <工具名>
Action Input: <参数>

完成后输出:
Thought: 我有足够信息回答了。
Action: finish
Action Input: <最终答案>

# Important
- 每次只调用一个工具
- 不确定时说"我不确定"而不是编造
- 必须用finish结束
"""


# ═══════════════════════════════════════════════════════════
# Harness 组件3: Tool Schema（JSON Schema格式）
# ═══════════════════════════════════════════════════════════

TOOL_SCHEMA = [
    {
        "name": "search",
        "description": "搜索知识库获取相关信息",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "calculator",
        "description": "数学计算",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式"
                }
            },
            "required": ["expression"]
        }
    },
]


# ═══════════════════════════════════════════════════════════
# Harness 组件4: Tracing（结构化日志）
# ═══════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger("agent")

@dataclass
class TraceEntry:
    iteration: int
    timestamp: float
    action: str
    action_input: str
    result: str
    tokens_used: int
    latency_ms: float
    error: str = ""

@dataclass
class AgentTrace:
    query: str
    start_time: float = field(default_factory=time.time)
    entries: list = field(default_factory=list)
    total_tokens: int = 0
    
    def add(self, entry: TraceEntry):
        self.entries.append(entry)
        self.total_tokens += entry.tokens_used
        logger.info(json.dumps({
            "iter": entry.iteration,
            "action": entry.action,
            "input": entry.action_input[:100],
            "result": entry.result[:100],
            "tokens": entry.tokens_used,
            "latency_ms": entry.latency_ms,
        }, ensure_ascii=False))
    
    def summary(self) -> dict:
        return {
            "query": self.query,
            "iterations": len(self.entries),
            "total_tokens": self.total_tokens,
            "total_time_ms": (time.time() - self.start_time) * 1000,
            "actions": [e.action for e in self.entries],
        }


# ═══════════════════════════════════════════════════════════
# Harness 组件5: Error Handler（统一错误处理）
# ═══════════════════════════════════════════════════════════

class AgentError(Exception):
    """Agent执行错误"""
    pass

def handle_tool_error(action: str, error: Exception, retry_count: int, config: AgentConfig) -> str:
    """
    统一错误处理策略：
    - Timeout → 换工具
    - ValueError → 修正参数重试
    - RateLimit → 等待重试
    - Unknown → 降级返回
    """
    error_msg = str(error)
    
    if "timeout" in error_msg.lower():
        return f"Tool Error: {action} timed out after {config.timeout_seconds}s. Try a different tool or simplify your query."
    
    if "rate" in error_msg.lower() and retry_count < config.max_retries:
        time.sleep(2 ** retry_count)  # 指数退避
        return "__RETRY__"
    
    if isinstance(error, (ValueError, TypeError)):
        return f"Tool Error: Invalid parameters for {action}: {error_msg}. Please fix the input format."
    
    return f"Tool Error: {action} failed: {error_msg}. Try a different approach."


# ═══════════════════════════════════════════════════════════
# Harness 组件6: Agent Loop（带完整控制点）
# ═══════════════════════════════════════════════════════════

def parse_action(response: str) -> tuple[str, str]:
    """解析LLM输出"""
    action_match = re.search(r"Action:\s*(.+)", response)
    input_match = re.search(r"Action Input:\s*(.+)", response, re.DOTALL)
    
    if not action_match:
        return "finish", response.strip()
    
    action = action_match.group(1).strip()
    action_input = input_match.group(1).strip() if input_match else ""
    return action, action_input


def run_agent(
    query: str,
    tools: dict[str, Callable],
    config: AgentConfig = AgentConfig(),
    system_prompt: str = "",
) -> dict:
    """
    生产级Agent Loop
    
    Returns: {
        "answer": str,
        "complete": bool,
        "iterations": int,
        "trace": AgentTrace
    }
    """
    trace = AgentTrace(query=query)
    
    messages = [
        {"role": "system", "content": system_prompt or SYSTEM_PROMPT_TEMPLATE},
        {"role": "user", "content": query},
    ]
    
    for i in range(config.max_iterations):
        start = time.time()
        
        # ─── Reason ───
        # TODO: 替换为真实LLM调用
        # response = openai.chat.completions.create(model=config.model, messages=messages, temperature=config.temperature)
        response = f"Thought: 模拟响应\nAction: finish\nAction Input: 这是模拟结果"
        
        messages.append({"role": "assistant", "content": response})
        latency = (time.time() - start) * 1000
        
        # ─── Parse ───
        action, action_input = parse_action(response)
        
        # ─── 终止条件（三重兜底）───
        if action == "finish" or "Final Answer" in response:
            answer = action_input if action == "finish" else response.split("Final Answer")[-1].strip()
            trace.add(TraceEntry(
                iteration=i+1, timestamp=time.time(),
                action="finish", action_input=answer,
                result="DONE", tokens_used=0, latency_ms=latency
            ))
            return {"answer": answer, "complete": True, "iterations": i+1, "trace": trace}
        
        # ─── Act（带错误恢复）───
        result = ""
        retry_count = 0
        while retry_count <= config.max_retries:
            try:
                if action not in tools:
                    result = f"Tool Error: Unknown tool '{action}'. Available: {list(tools.keys())}"
                    break
                result = str(tools[action](action_input))
                break
            except Exception as e:
                handled = handle_tool_error(action, e, retry_count, config)
                if handled == "__RETRY__":
                    retry_count += 1
                    continue
                result = handled
                break
        
        # ─── Observe ───
        messages.append({"role": "user", "content": f"Observation: {result}"})
        
        # ─── Trace ───
        trace.add(TraceEntry(
            iteration=i+1, timestamp=time.time(),
            action=action, action_input=action_input,
            result=result[:200], tokens_used=len(str(messages[-1])),
            latency_ms=latency
        ))
        
        # ─── Token Budget ───
        if len(messages) > config.max_messages_keep:
            system = [m for m in messages if m["role"] == "system"]
            recent = messages[-config.max_messages_keep:]
            messages = system + recent
    
    # 超限
    return {
        "answer": "达到最大迭代次数",
        "complete": False,
        "iterations": config.max_iterations,
        "trace": trace,
    }


# ═══════════════════════════════════════════════════════════
# Harness 组件7: FastAPI部署入口
# ═══════════════════════════════════════════════════════════

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    
    app = FastAPI(title="Agent Loop - 造物工坊#06")
    
    class AgentRequest(BaseModel):
        query: str
        max_iterations: int = 10
    
    class AgentResponse(BaseModel):
        answer: str
        complete: bool
        iterations: int
        trace_summary: dict
    
    TOOLS_IMPL: dict[str, Callable] = {
        "search": lambda q: f"[搜索结果] {q}",
        "calculator": lambda expr: str(eval(expr)),
        "finish": lambda x: x,
    }
    
    @app.post("/agent", response_model=AgentResponse)
    def run_agent_api(req: AgentRequest):
        config = AgentConfig(max_iterations=req.max_iterations)
        result = run_agent(req.query, TOOLS_IMPL, config)
        return AgentResponse(
            answer=result["answer"],
            complete=result["complete"],
            iterations=result["iterations"],
            trace_summary=result["trace"].summary(),
        )

except ImportError:
    # FastAPI not installed, skip API setup
    pass


if __name__ == "__main__":
    # 快速测试
    tools = {
        "search": lambda q: f"[模拟] {q}: 32度晴天",
        "calculator": lambda expr: str(eval(expr)),
        "finish": lambda x: x,
    }
    
    result = run_agent("北京今天多少度？", tools)
    print(f"\nAnswer: {result['answer']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Trace: {result['trace'].summary()}")
