"""
AutoMem-Lite 记忆系统 Harness
简化版：给Agent增加文件系统记忆动作 + meta-LLM审查循环

核心设计：
1. MemoryActionSpace: read / write / search / append / create / upsert
2. MemoryScaffold: 每个任务类型的记忆模板（prompt + 文件schema + 动作偏好）
3. MetaReviewer: 审查一个episode的轨迹，输出新的scaffold版本
4. 用法：先跑episode收集轨迹 → meta-LLM审查生成v(N+1) → 切换新scaffold继续跑
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

Action = Literal["read", "write", "search", "append", "create", "upsert"]


@dataclass
class MemoryFile:
    path: str
    content: str


@dataclass
class MemoryAction:
    action: Action
    path: str
    content: str = ""
    reason: str = ""


@dataclass
class MemoryScaffold:
    """记忆脚手架：描述Agent应该怎么管理记忆。"""
    version: int
    task_type: str
    system_prompt: str
    file_schema: dict[str, str]
    preferred_actions: list[Action] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)

    def to_prompt(self) -> str:
        schema_lines = "\n".join(f"  {k}: {v}" for k, v in self.file_schema.items())
        action_lines = ", ".join(self.preferred_actions)
        example_lines = "\n".join(f"  - {e}" for e in self.examples)
        return f"""{self.system_prompt}

可用记忆动作（一等公民，与任务动作同等重要）：
  read(path): 读取记忆文件内容
  write(path, content): 覆盖写入记忆文件
  append(path, content): 追加内容
  search(query): 在记忆目录中搜索关键词
  create(path): 创建新记忆文件
  upsert(path, key, content): 如果key存在则覆盖，否则插入（用于去重，如坐标地图）

记忆文件schema：
{schema_lines}

动作优先级建议：{action_lines}

示例：
{example_lines}
"""


class FileSystemMemory:
    """Agent的外部记忆存储。"""

    def __init__(self, base_dir: str | Path):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)
        self._log: list[MemoryAction] = []

    def list_files(self) -> list[str]:
        return [str(p.relative_to(self.base)) for p in self.base.rglob("*") if p.is_file()]

    def read(self, path: str) -> str:
        target = self.base / path
        return target.read_text(encoding="utf-8") if target.exists() else ""

    def write(self, path: str, content: str) -> None:
        target = self.base / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def append(self, path: str, content: str) -> None:
        existing = self.read(path)
        self.write(path, existing + content)

    def create(self, path: str) -> None:
        target = self.base / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()

    def search(self, query: str) -> list[str]:
        results = []
        for p in self.base.rglob("*"):
            if p.is_file() and query.lower() in p.read_text(encoding="utf-8", errors="ignore").lower():
                results.append(str(p.relative_to(self.base)))
        return results

    def upsert(self, path: str, key: str, content: str, key_pattern: str | None = None) -> None:
        """
        按key去重更新。例如地图坐标：key="(3,4)"，匹配到旧条目就替换。
        key_pattern: 用于从现有内容中识别key的正则。
        """
        existing = self.read(path)
        lines = existing.splitlines() if existing else []
        key_re = re.compile(key_pattern or re.escape(key))
        replaced = False
        new_lines = []
        for line in lines:
            if key_re.search(line):
                new_lines.append(content)
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(content)
        self.write(path, "\n".join(new_lines))

    def execute(self, action: MemoryAction) -> str:
        self._log.append(action)
        if action.action == "read":
            return self.read(action.path)
        if action.action == "write":
            self.write(action.path, action.content)
            return "OK"
        if action.action == "append":
            self.append(action.path, action.content)
            return "OK"
        if action.action == "create":
            self.create(action.path)
            return "OK"
        if action.action == "search":
            return "\n".join(self.search(action.path or action.content))
        if action.action == "upsert":
            # path格式: "file_path|key"
            file_path, key = action.path.split("|", 1)
            self.upsert(file_path, key, action.content)
            return "OK"
        return "UNKNOWN_ACTION"

    @property
    def log(self) -> list[MemoryAction]:
        return self._log


class MetaReviewer:
    """
    Loop1: 用meta-LLM审查整个episode轨迹，输出新的scaffold版本。

    这里用占位函数模拟。实际使用时，把 trajectory 和 current_scaffold 传给 LLM，
    让它返回新的 system_prompt / file_schema / preferred_actions / examples。
    """

    def __init__(self, llm_call: Callable[[str], str] | None = None):
        self.llm_call = llm_call or self._default_llm

    def _default_llm(self, prompt: str) -> str:
        # 占位：返回一个硬编码的改进建议
        return json.dumps({
            "issues": ["地图文件无限追加", "没有先查后写"],
            "new_scaffold": {
                "system_prompt": "你是一个有良好记忆习惯的Agent。每次行动前先search/read相关记忆，必要时用upsert去重写入。",
                "file_schema": {"map.txt": "坐标地图，每行一个upsert条目", "plan.txt": "当前计划", "log.txt": "关键事件日志"},
                "preferred_actions": ["search", "read", "upsert"],
                "examples": ["接任务后先read plan.txt", "观察新坐标时用upsert map.txt|(x,y) 更新"],
            }
        }, ensure_ascii=False, indent=2)

    def review(self, trajectory: list[dict], current: MemoryScaffold) -> MemoryScaffold:
        prompt = f"""你是一名记忆系统优化专家。请审查下面Agent在一个episode中的记忆使用轨迹，并输出改进后的记忆脚手架（scaffold）。

当前scaffold版本: v{current.version}
当前system_prompt: {current.system_prompt}
当前file_schema: {json.dumps(current.file_schema, ensure_ascii=False)}

轨迹（每步包含：step, observation, thought, memory_action, result）:
{json.dumps(trajectory, ensure_ascii=False, indent=2)}

请输出JSON：
{{
  "issues": ["问题1", "问题2"],
  "new_scaffold": {{
    "system_prompt": "...",
    "file_schema": {{"file.txt": "描述"}},
    "preferred_actions": ["read", "upsert"],
    "examples": ["..."]
  }}
}}
"""
        raw = self.llm_call(prompt)
        data = json.loads(raw)
        ns = data["new_scaffold"]
        return MemoryScaffold(
            version=current.version + 1,
            task_type=current.task_type,
            system_prompt=ns["system_prompt"],
            file_schema=ns["file_schema"],
            preferred_actions=ns.get("preferred_actions", []),
            examples=ns.get("examples", []),
        )


# ═══════════════════════════════════════════════════════════
# 示例：跑一个episode，然后meta-LLM审查并生成v2 scaffold
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    scaffold_v1 = MemoryScaffold(
        version=1,
        task_type="grid_exploration",
        system_prompt="你是一个探索网格世界的Agent。请把观察到的信息写入记忆文件。",
        file_schema={
            "map.txt": "记录走过的坐标",
            "plan.txt": "当前目标",
        },
        preferred_actions=["write", "append"],
        examples=["看到新坐标就append到map.txt"],
    )

    memory = FileSystemMemory("./demo_memory")

    # 模拟一个episode：Agent看到坐标就append（这是有问题的基线行为）
    steps = [
        {"step": 1, "observation": "at (0,0)", "thought": "记录起点"},
        {"step": 2, "observation": "at (1,0)", "thought": "向东移动"},
        {"step": 3, "observation": "at (0,0)", "thought": "回到起点，但旧记录还在"},
    ]

    trajectory = []
    for s in steps:
        # 基线策略：无脑append
        action = MemoryAction(action="append", path="map.txt", content=f"{s['observation']}\n", reason=s["thought"])
        result = memory.execute(action)
        trajectory.append({**s, "memory_action": action.action, "content": action.content, "result": result})

    print("=== v1 scaffold 运行结束 ===")
    print("map.txt 内容:")
    print(memory.read("map.txt"))
    print("记忆动作日志:", [(a.action, a.path) for a in memory.log])

    # Loop1: meta-LLM审查
    reviewer = MetaReviewer()
    scaffold_v2 = reviewer.review(trajectory, scaffold_v1)
    print("\n=== Loop1 生成 v2 scaffold ===")
    print(scaffold_v2.to_prompt())

    print("\n说明：把 scaffold_v2 替换进Agent的system prompt，再跑下一个episode，就是AutoMem-Lite的完整迭代循环。")
