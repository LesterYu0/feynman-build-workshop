#!/usr/bin/env python3
"""
agent_memory.py — 最小 Agent 记忆系统
======================================
造物车间 #01 · 7步设计Agent记忆系统

实现了从零到一的多层记忆：三分类 → SQLite FTS5 → 时间戳 → 归纳 → 冻结快照

用法:
    python3 agent_memory.py init          # 初始化数据库
    python3 agent_memory.py add "内容"    # 添加记忆
    python3 agent_memory.py search "关键词" # 搜索记忆
    python3 agent_memory.py consolidate   # 运行归纳
    python3 agent_memory.py stats         # 查看统计
    python3 agent_memory.py test          # 运行自测

依赖：零额外依赖——Python 3 标准库就够了。需要 SQLite 3.35+。
"""

import sqlite3
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# 配置区 — 改这里就行
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    "db_path": "./agent_memory.db",       # 记忆数据库路径
    "log_dir": "./logs/",                 # 日志目录（每日日志存放位置）
    "consolidation_days": 7,              # 归纳时读取最近 N 天的日志
    "stale_days": 30,                     # 超过 N 天未被引用的记录降级为归档
    "memory_md": "./MEMORY.md",           # 核心记忆文件路径
}


# ═══════════════════════════════════════════════════════════════
# Step 2: SQLite + FTS5 — 正确的地基
# ═══════════════════════════════════════════════════════════════

def init_db(db_path: str) -> None:
    """创建数据库表：FTS5 全文索引 + 元数据表。

    为什么不用向量库做地基？
    - FTS5 精确关键词召回（"dark mode" 一定返回 dark_mode 记忆）
    - 向量库语义搜索不准反而危险（它给你“看起来像”的结果）
    - 先解耦搜索和理解，让 LLM 在 FTS5 结果上精排
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # FTS5 全文索引表 — 负责"找得到"
    # 使用 trigram 分词器以支持 CJK 文字的部分匹配
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
            content,
            tokenize='trigram'
        )
    """)

    # 元数据表 — 负责"记得准"
    # category: persistent(该存) | session(该缓存) | archived(归档)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fts_rowid INTEGER,
            category TEXT NOT NULL DEFAULT 'persistent',
            frozen BOOLEAN NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            valid_until TEXT,
            superseded_by INTEGER,
            last_accessed TEXT,
            access_count INTEGER DEFAULT 0,
            FOREIGN KEY (fts_rowid) REFERENCES memory_fts(rowid),
            FOREIGN KEY (superseded_by) REFERENCES memory_meta(id)
        )
    """)

    # 索引
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_memory_category
                   ON memory_meta(category)""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_memory_created
                   ON memory_meta(created_at)""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_memory_valid
                   ON memory_meta(valid_until)""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_memory_frozen
                   ON memory_meta(frozen)""")

    conn.commit()
    conn.close()
    print(f"✅ 记忆数据库初始化完成: {db_path}")


# ═══════════════════════════════════════════════════════════════
# Step 1 & 2: 三分类记忆 + 写入
# ═══════════════════════════════════════════════════════════════

def classify_memory(content: str) -> str:
    """Step 1: 三分类记忆。

    这是整个系统最重要的一步——不是"存什么"，而是"不存什么"。

    persistent: 跨 session 不变的信息（用户偏好、已修 bug、技术决策）
    session:    当前 session 有效，结束后可丢弃（临时变量、中间结果）
    archived:   过时或被替代，保留但不再参与主动搜索

    生产级 Agent 要用 LLM 做分类；这里提供一个最小规则引擎。
    """
    content_lower = content.lower()

    # 该存：用户偏好、修复记录、技术决策、系统配置
    persistent_keywords = [
        "偏好", "prefer", "修复", "fix", "bug", "crash", "决策",
        "选择", "配置", "config", "规则", "rule", "总是", "always",
        "架构", "architecture", "踩坑", "教训",
    ]
    # 该缓存：临时、中间结果、单次连接
    session_keywords = [
        "临时", "temp", "中间", "intermediate", "单次", "测试",
        "output:", "result:", "响应:", "response:",
    ]

    for kw in persistent_keywords:
        if kw in content_lower:
            return "persistent"
    for kw in session_keywords:
        if kw in content_lower:
            return "session"
    return "persistent"  # 默认存下来


def add_memory(
    db_path: str,
    content: str,
    category: str | None = None,
    valid_until: str | None = None,
) -> int:
    """添加一条记忆。

    Args:
        content: 记忆内容
        category: 如果为 None，自动三分类
        valid_until: ISO 格式日期，如 "2026-12-31"。空字符串 = 永久有效。

    Returns:
        fts_rowid: 新记忆的 FTS5 rowid
    """
    if category is None:
        category = classify_memory(content)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    now = datetime.now().isoformat()

    # 写入 FTS5 索引
    cur.execute("INSERT INTO memory_fts (content) VALUES (?)", (content,))
    fts_rowid = cur.lastrowid

    # 写入元数据
    cur.execute(
        """INSERT INTO memory_meta
           (fts_rowid, category, created_at, valid_until)
           VALUES (?, ?, ?, ?)""",
        (fts_rowid, category, now, valid_until or None),
    )

    conn.commit()
    conn.close()
    print(f"✅ 已添加记忆 [{category}] (ID={fts_rowid}): {content[:60]}...")
    return fts_rowid


# ═══════════════════════════════════════════════════════════════
# Step 3: 时间戳 — 记忆的保质期
# ═══════════════════════════════════════════════════════════════

def search_memory(
    db_path: str,
    query: str,
    limit: int = 5,
    include_expired: bool = False,
    prefer_frozen: bool = True,
) -> list[dict]:
    """搜索记忆 — FTS5 trigram 宽召回 + 元数据过滤 + LIKE 降级。

    搜索策略：
    1. FTS5 trigram 搜索（3字及以上中文、英文均可命中）
    2. 短查询降级：1-2字中文自动切 LIKE（trigram 最少需要3字）
    3. 元数据过滤：排除过期 + 优先返回冻结项
    4. 返回格式适合直接喂给 LLM 做精排
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    now = datetime.now().isoformat()

    # 判断是否需要 LIKE 降级（纯 CJK 短查询，trigram 需要至少 3 字符）
    use_like = len(query) <= 2 and all("\u4e00" <= c <= "\u9fff" for c in query)

    order_clause = "m.frozen DESC, rank" if prefer_frozen else "rank"
    valid_clause = (
        "AND (m.valid_until IS NULL OR m.valid_until > ?)"
        if not include_expired else ""
    )

    if use_like:
        # 短 CJK 查询降级为 LIKE
        base_sql = f"""SELECT m.id, f.content, m.category, m.created_at,
                              m.valid_until, m.access_count, m.frozen
                       FROM memory_fts f
                       JOIN memory_meta m ON f.rowid = m.fts_rowid
                       WHERE f.content LIKE ?
                         {valid_clause}
                       ORDER BY {order_clause}
                       LIMIT ?"""
        params = (f"%{query}%",)
    else:
        base_sql = f"""SELECT m.id, f.content, m.category, m.created_at,
                              m.valid_until, m.access_count, m.frozen
                       FROM memory_fts f
                       JOIN memory_meta m ON f.rowid = m.fts_rowid
                       WHERE memory_fts MATCH ?
                         {valid_clause}
                       ORDER BY {order_clause}
                       LIMIT ?"""
        params = (query,)

    if include_expired:
        cur.execute(base_sql, (*params, limit))
    else:
        cur.execute(base_sql, (*params, now, limit))

    results = [dict(row) for row in cur.fetchall()]

    # 更新访问计数
    for r in results:
        cur.execute(
            """UPDATE memory_meta
               SET last_accessed = ?, access_count = access_count + 1
               WHERE id = ?""",
            (now, r["id"]),
        )

    conn.commit()
    conn.close()

    # 格式化输出 — 可直接喂给 LLM
    return [
        {
            "id": r["id"],
            "category": r["category"],
            "frozen": bool(r["frozen"]),
            "created": r["created_at"],
            "expires": r["valid_until"] or "永不过期",
            "accessed": r["access_count"],
            "content": r["content"],
        }
        for r in results
    ]


# ═══════════════════════════════════════════════════════════════
# Step 4: Frozen Snapshot — 保护前缀缓存
# ═══════════════════════════════════════════════════════════════

def freeze_stable_memories(db_path: str, inactivity_days: int = 3) -> int:
    """Step 4: 冻结稳定记忆，保护前缀缓存。

    问题：System Prompt 频繁变动 → Prefix Cache 永远不命中 → Token 账单爆炸
    解法：将 3 天内未变动的核心记忆标记为 frozen
         冻结区属于 Stable Prefix → Cache 命中率回到 80%+

    只冻结 persistent 类且未被 superseded 的记忆。
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=inactivity_days)).isoformat()

    cur.execute(
        """UPDATE memory_meta SET frozen = 1
           WHERE category = 'persistent'
             AND frozen = 0
             AND superseded_by IS NULL
             AND created_at < ?""",
        (cutoff,),
    )
    count = cur.rowcount
    conn.commit()
    conn.close()
    print(f"🧊 冻结了 {count} 条稳定记忆")
    return count


def get_frozen_snapshot(db_path: str, max_entries: int = 50) -> list[dict]:
    """获取冻结记忆快照，用于注入 System Prompt 的 Stable Prefix。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """SELECT m.id, f.content, m.category, m.created_at, m.access_count
           FROM memory_fts f
           JOIN memory_meta m ON f.rowid = m.fts_rowid
           WHERE m.frozen = 1
             AND m.superseded_by IS NULL
           ORDER BY m.access_count DESC, m.created_at DESC
           LIMIT ?""",
        (max_entries,),
    )
    results = [dict(row) for row in cur.fetchall()]
    conn.close()
    return results


# ═══════════════════════════════════════════════════════════════
# Step 5: 归纳层 — 让 Agent 每天 Auto-Dream
# ═══════════════════════════════════════════════════════════════

def mark_superseded(db_path: str, old_id: int, new_id: int) -> None:
    """旧记忆被新记忆替代。调用后旧记忆不再参与主动搜索。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    now = datetime.now().isoformat()

    cur.execute(
        """UPDATE memory_meta
           SET superseded_by = ?, valid_until = ?, frozen = 0
           WHERE id = ?""",
        (new_id, now, old_id),
    )

    conn.commit()
    conn.close()
    print(f"✅ 记忆 #{old_id} 已被 #{new_id} 替代")


def consolidate(db_path: str, log_dir: str, days: int) -> list[dict]:
    """Step 5: 读取最近 N 天日志 → 去重 → 冲突检测 → 淘汰过期。

    真正的去重和冲突检测需要 LLM 完成。这里提供了完整的：
    1. 日志读取框架
    2. 条目提取逻辑
    3. LLM 调用点（注释标注）
    4. 淘汰过期记忆逻辑
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        print(f"⚠️ 日志目录不存在: {log_dir}")
        return []

    # 1. 读取最近 N 天日志
    cutoff = datetime.now() - timedelta(days=days)
    recent_logs = []
    for f in sorted(log_path.glob("*.md"), reverse=True):
        try:
            log_date = datetime.strptime(f.stem, "%Y-%m-%d")
            if log_date >= cutoff:
                recent_logs.append({"date": f.stem, "path": str(f)})
        except ValueError:
            continue

    print(f"📋 读取到 {len(recent_logs)} 天的日志")

    # 2. 提取条目
    entries: list[dict] = []
    for log in recent_logs:
        with open(log["path"]) as f:
            content = f.read()
        sections = [s.strip() for s in content.split("\n## ") if s.strip()]
        for section in sections:
            entries.append({"date": log["date"], "content": section})

    print(f"📦 共 {len(entries)} 条待归纳")

    # ─── 3. LLM 调用点 ──────────────────────────────────
    # prompt = f"""
    # 以下是 {days} 天内的 Agent 工作日志。请做三件事：
    # 1. 去重：多条记录说同一件事 → 合并为一条
    # 2. 冲突检测：互斥信息 → 保留最新，标记旧的为 superseded
    # 3. 时效淘汰：超过 30 天未引用的 → 降级为 archived
    #
    # 输出格式（JSON）：
    # {{
    #   "deduplicated": [...],   # 去重后的记录
    #   "superseded": [...],     # 需要标记过时的旧 ID
    #   "highlights": [...]      # 值得写入 MEMORY.md 的精华
    # }}
    # """
    # result = call_llm(prompt)  # 替换为你的 LLM 调用
    # ─────────────────────────────────────────────────────

    # 4. 清理过期记忆
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    stale_cutoff = datetime.now().isoformat()
    cur.execute(
        """UPDATE memory_meta SET category = 'archived', frozen = 0
           WHERE category = 'persistent'
             AND valid_until IS NOT NULL
             AND valid_until < ?
             AND superseded_by IS NULL""",
        (stale_cutoff,),
    )
    archived_count = cur.rowcount
    conn.commit()
    conn.close()

    print(f"🗄️ 归档了 {archived_count} 条过期记忆")
    print("✅ 归纳完成。请运行 search 验证结果。")
    return entries


# ═══════════════════════════════════════════════════════════════
# 统计
# ═══════════════════════════════════════════════════════════════

def stats(db_path: str) -> dict:
    """数据库统计信息。返回 dict 方便程序调用。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT category, COUNT(*) FROM memory_meta GROUP BY category")
    by_category = dict(cur.fetchall())

    cur.execute("SELECT COUNT(*) FROM memory_meta WHERE superseded_by IS NOT NULL")
    superseded = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM memory_meta WHERE frozen = 1")
    frozen = cur.fetchone()[0]

    conn.close()

    print("═══════════════════════════════════")
    print("📊 记忆系统统计")
    print("═══════════════════════════════════")
    for cat, count in sorted(by_category.items()):
        print(f"  {cat}: {count} 条")
    print(f"  已过期/被替代: {superseded} 条")
    print(f"  已冻结: {frozen} 条")
    print("═══════════════════════════════════")

    return {
        "by_category": by_category,
        "superseded": superseded,
        "frozen": frozen,
    }


# ═══════════════════════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════════════════════

def run_tests() -> None:
    """运行自测，验证所有核心功能。"""
    import tempfile
    test_db = Path(tempfile.gettempdir()) / "agent_memory_test.db"
    # 清理上次测试残留
    test_db.unlink(missing_ok=True)
    for ext in ("-journal", "-wal", "-shm"):
        Path(str(test_db) + ext).unlink(missing_ok=True)
    print("🧪 运行自测...\n")

    # 测试 1: 初始化
    print("Test 1/6: 数据库初始化...")
    init_db(str(test_db))
    assert test_db.exists()
    print("  ✅ PASS\n")

    # 测试 2: 三分类
    print("Test 2/6: 三分类记忆...")
    assert classify_memory("用户偏好暗色模式") == "persistent"
    assert classify_memory("临时中间结果xyz") == "session"
    assert classify_memory("修复null pointer崩溃bug") == "persistent"
    print("  ✅ PASS\n")

    # 测试 3: 添加和搜索
    print("Test 3/6: 添加和搜索...")
    add_memory(str(test_db), "用户偏好暗色模式，所有界面用暗色主题", "persistent")
    add_memory(str(test_db), "修复auth模块null_pointer崩溃，添加了空值检查", "persistent")
    add_memory(str(test_db), "临时调试日志：output error_code_500", "session")

    # trigram 分词器：3字及以上中文可搜索
    results = search_memory(str(test_db), "暗色模式")
    assert len(results) > 0, "FTS5 trigram search failed"
    assert "暗色" in results[0]["content"]
    print("  ✅ PASS\n")

    # 测试 4: 冻结
    print("Test 4/6: 冻结稳定记忆...")
    freeze_stable_memories(str(test_db), inactivity_days=0)
    snapshot = get_frozen_snapshot(str(test_db))
    assert len(snapshot) > 0
    print(f"  ✅ PASS (冻结了 {len(snapshot)} 条)\n")

    # 测试 5: 替代
    print("Test 5/6: 替代过时记忆...")
    results = search_memory(str(test_db), "暗色模式")
    old_id = results[0]["id"]
    new_id = add_memory(str(test_db), "用户改成亮色模式偏好", "persistent")
    mark_superseded(str(test_db), old_id, new_id)
    print("  ✅ PASS\n")

    # 测试 6: 统计
    print("Test 6/6: 统计...")
    result = stats(str(test_db))
    assert "persistent" in result["by_category"]
    print("  ✅ PASS\n")

    print("════════════════════════════════════")
    print("🎉 全部 6 项测试通过！")
    print("════════════════════════════════════")
    # 清理
    test_db.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    db = CONFIG["db_path"]

    if len(sys.argv) < 2:
        print("用法: python3 agent_memory.py <command> [args]")
        print()
        print("命令:")
        print("  init                    初始化数据库")
        print('  add "内容" [分类]       添加记忆（自动三分类）')
        print('  search "关键词"         搜索记忆')
        print("  freeze                  冻结稳定记忆")
        print("  frozen-snapshot         查看冻结快照")
        print("  supersede <旧ID> <新ID> 标记替代")
        print("  consolidate             运行归纳")
        print("  stats                   查看统计")
        print("  test                    运行自测")
        sys.exit(0)

    cmd = sys.argv[1]

    try:
        if cmd == "init":
            init_db(db)
        elif cmd == "add":
            content = sys.argv[2]
            category = sys.argv[3] if len(sys.argv) > 3 else None
            add_memory(db, content, category)
        elif cmd == "search":
            query = sys.argv[2]
            results = search_memory(db, query)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        elif cmd == "freeze":
            freeze_stable_memories(db)
        elif cmd == "frozen-snapshot":
            snapshot = get_frozen_snapshot(db)
            print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        elif cmd == "supersede":
            old_id, new_id = int(sys.argv[2]), int(sys.argv[3])
            mark_superseded(db, old_id, new_id)
        elif cmd == "consolidate":
            consolidate(db, CONFIG["log_dir"], CONFIG["consolidation_days"])
        elif cmd == "stats":
            stats(db)
        elif cmd == "test":
            run_tests()
        else:
            print(f"未知命令: {cmd}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
