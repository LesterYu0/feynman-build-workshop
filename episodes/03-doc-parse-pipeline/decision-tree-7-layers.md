# 资产 3 — 7 层 Pipeline 选型决策树

> 拿到一个文档，从哪开始？看完这棵树你就知道。

## 完整决策树

```
START: 拿到一份文档
│
├── 1. 是什么文件类型？
│   ├── PDF → 跳到 L3 (PDF 4 档)
│   ├── Excel (.xlsx/.xls) → 跳到 L5 (Excel 多表)
│   ├── Word (.docx) → 跳到 L6 (Word 统一)
│   ├── 图片 (.png/.jpg) → 走 L4 (OCR 4 降级)
│   ├── TXT/MD → 1 行代码直接读
│   └── 其他 → UNKNOWN，记入异常清单
│
│
├── L3 — PDF 4 档
│   ├── 2. 是数字还是扫描？
│   │   ├── 数字 PDF（可复制文字）→ 3
│   │   ├── 扫描件（图片）→ 直接走档 4 (MinerU)
│   │   └── 混合 → 走档 3 (PyMuPDF) + 缺页 OCR 降级
│   │
│   ├── 3. 数字 PDF → 走哪档？
│   │   ├── 只看文字 → 档 1 (PDF-dots) 0.5s/页
│   │   ├── 要表格 → 档 2 (PDFPlumber) 1-2s/页
│   │   ├── 复杂排版 → 档 3 (PyMuPDF) 2-3s/页
│   │   └── 不知道怎么选 → 档 2（最稳）
│   │
│   └── 4. 档 4 (MinerU) 是终点吗？
│       ├── 是 → 直接出 Document
│       └── 否（速度太慢）→ 4 降级拆开：
│           ├── L4-1 Tesseract（英文好）
│           ├── L4-2 PaddleOCR（中文好）
│           ├── L4-3 Surya（旋转/复杂好）
│           └── L4-4 VLM（终极方案，付费）
│
│
├── L5 — Excel 多表
│   ├── 5. Sheet 数量？
│   │   ├── 1-3 个 → openpyxl 一次性解析
│   │   ├── 3+ 个 → 按 sheet 单独成 Document
│   │   └── 10+ 个 → 提醒业务方确认要不要全要
│   │
│   ├── 6. 有公式吗？
│   │   ├── 有公式 → 保留 data_only=False 模式（拿公式）
│   │   └── 无公式 → data_only=True（拿值）
│   │
│   └── 7. 合并单元格？
│       ├── 有 → 解开合并（每个单元格都填值）
│       └── 无 → 直接抽
│
│
├── L6 — Word 统一
│   ├── 8. 段落 / 表格 / 图片？
│   │   ├── 段落 → python-docx
│   │   ├── 表格 → python-docx doc.tables
│   │   └── 图片 → doc.inline_shapes（OCR 走 L4）
│   │
│   └── 9. 标题层级？
│       ├── 有 → 保留 style.name（Heading 1/2/3）
│       └── 无 → 按段落长度 + 格式粗略判断
│
│
└── L7 — 业务验收
    │
    ├── 10. 业务关键字是否全部出现？
    │   ├── 全部出现 → ✅ 验收通过
    │   ├── 缺失 1-2 个 → ⚠️ 告警（人工 review）
    │   └── 缺失 > 2 个 → ❌ 退回 L3 重选更高档
    │
    ├── 11. 表格行号 / 页码是否保留？
    │   ├── 保留 → ✅
    │   └── 没保留 → 退回 L3 档 2+ 重做
    │
    └── 12. Chunk 数量是否合理？
        ├── 数字 PDF：约 = 页数 × 1-3 chunks
        ├── 扫描件：约 = 页数 × 5-10 chunks
        ├── Excel：约 = sheet 数
        ├── Word：约 = 段落数 + 表格数
        └── 偏差 > 50% → 异常，告警
```

---

## 3 个实战例子（按决策树走一遍）

### 例子 1：招股书 PDF（数字 PDF，100 页）

```
START: 拿到招股书.pdf
  → 1. 文件类型 = PDF
  → L3:
    → 2. 数字 PDF（可复制文字）→ 3
    → 3. 要表格（财务报表）→ 档 2 (PDFPlumber)
  → L7:
    → 10. 业务关键字"营业收入/净利润/总资产"全部出现 ✅
    → 11. 表格行号保留 ✅
  → 出 Document
```

**结果**：100 页 × 1.5s/页 = **150s = 2.5 分钟**。

### 例子 2：审计报告扫描件（80 页）

```
START: 拿到审计报告.pdf
  → 1. 文件类型 = PDF
  → L3:
    → 2. 扫描件（不能选文字）→ 走档 4 (MinerU)
    → 4. 档 4 是终点 → 直接出 Document
  → L7:
    → 10. 业务关键字"审计意见/无保留意见"全部出现 ✅
    → 12. chunks = 80 × 7 = 560（合理）
  → 出 Document
```

**结果**：80 页 × 10s/页 = **800s = 13 分钟**。

### 例子 3：股权结构 Excel（5 个 sheet）

```
START: 拿到股权结构.xlsx
  → 1. 文件类型 = Excel
  → L5:
    → 5. Sheet 数 = 5（适中）
    → 6. 有公式（VLOOKUP）→ data_only=False 模式
    → 7. 合并单元格（股东持股比例）→ 解开
  → L7:
    → 10. 业务关键字"股东名称/持股比例"全部出现 ✅
  → 出 Document
```

**结果**：5 sheet × 2s = **10s**。

---

## 决策树的核心心法

### 3 个黄金法则

1. **数字 PDF → 档 2 是 90% 情况下的最优解**  
   不要无脑上档 4（慢），不要无脑用档 1（没表格）。

2. **扫描件 → 直接档 4，别挣扎**  
   档 1-3 对扫描件都是 0 字符输出。直接 MinerU。

3. **业务验收是底线，不是锦上添花**  
   解析后**必须**跑业务关键字校验，否则你不知道解析对了没有。

### 2 个反模式（不要这么做）

❌ **反模式 1：无脑走档 4**  
```python
# 错：所有 PDF 都走档 4
doc = parse_document("x.pdf", hint="mineru")  # 慢 5-10 倍
```

✅ **正确做法：按决策树判断**  
```python
# 对：数字 PDF 走档 2，扫描件走档 4
if is_scan(pdf_path):
    doc = parse_document(pdf_path, hint="mineru")
else:
    doc = parse_document(pdf_path, hint="pdfplumber")
```

❌ **反模式 2：跳过业务验收**  
```python
# 错：解析完直接入库
doc = parse_document("x.pdf")
db.insert(doc)  # 解析错了也不知道
```

✅ **正确做法：必跑 validate()**  
```python
doc = parse_document("x.pdf", keywords=["营业收入", "净利润"])
if not doc.metadata["validation"]["passed"]:
    alert("业务关键字缺失，需人工 review")
```

---

## 打印版（A4 纸贴显示器）

```
┌─────────────────────────────────────────┐
│  7层文档解析 Pipeline 决策速查           │
├─────────────────────────────────────────┤
│  1. 文件类型 → PDF/Excel/Word/图片      │
│  2. PDF 是数字还是扫描？                  │
│     数字 → 档2 / 扫描 → 档4             │
│  3. 表格需求？ → 档1(无)/档2(有)         │
│  4. 复杂排版？ → 档3 / 档4              │
│  5. 业务验收 → 关键字 + 行号 + chunk数  │
│                                          │
│  黄金法则：                              │
│   • 数字PDF 90% → 档2                   │
│   • 扫描件直接档4                        │
│   • 验收必跑                             │
└─────────────────────────────────────────┘
```

---

## 速查表（决策树 → 代码）

| 决策 | 代码 |
|---|---|
| 1. 路由 | `route_parser(path)` |
| 2. 数字 vs 扫描 | `is_scan(path)` → bool |
| 3. 走档 1 | `parse_document(path, hint="pdf_dots")` |
| 4. 走档 2 | `parse_document(path, hint="pdfplumber")` |
| 5. 走档 3 | `parse_document(path, hint="pymupdf")` |
| 6. 走档 4 | `parse_document(path, hint="mineru")` |
| 7. 走 OCR L1 | `_tesseract(path)` |
| 8. 走 OCR L2 | `_paddleocr(path)` |
| 9. 走 OCR L3 | `_surya(path)` |
| 10. 走 OCR L4 | `_vlm(path)` |
| 11. 业务验收 | `doc.validate(keywords)` |
