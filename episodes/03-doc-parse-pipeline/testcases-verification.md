# 资产 4 — 4 象限压测验收清单

> 解析后必跑的 4 象限检查。每条都是从实战翻车现场总结出来的。

## 4 象限速查

```
                解析成功
                   │
        ┌──────────┼──────────┐
        │          │          │
    内容对        格式对
   (语义层)      (结构层)
        │          │          │
   业务验收     表格行号
   关键字命中   页码保留
   数字金额     bbox 完整
        │          │          │
        └──────────┴──────────┘
                   │
                解析成功
```

**完整 4 象限**：

| 象限 | 检查项 | 失败影响 |
|---|---|---|
| **Q1 内容** | 业务关键字是否全部出现？数字/金额/比例是否准确？ | 业务方 review 才发现 |
| **Q2 格式** | 表格行号 / 页码 / bbox 是否保留？ | 引用错误，无法定位原文 |
| **Q3 性能** | 解析时延是否在预算内？chunk 数量是否合理？ | 拖慢整体 pipeline |
| **Q4 健壮** | 异常文件是否优雅降级？空文件/损坏文件是否报错？ | 静默失败，污染下游 |

---

## 象限 1：内容验收（语义层）

### 测试 1.1：业务关键字 100% 命中

```python
def test_business_keywords():
    keywords = ["营业收入", "净利润", "总资产", "ROE", "经营性现金流"]
    doc = parse_document("fixtures/audit_report_2024.pdf", keywords=keywords)
    
    result = doc.metadata["validation"]
    assert result["passed"], f"缺失关键字: {result['missing_keywords']}"
    assert result["found_keywords"] == result["total_keywords"]
```

**通过标准**：5/5 关键字全部出现。

**实战翻车**：
- 档 1 抽文字时，**"净利润"被拆成"净利"+"润"**，关键字搜索失败
- 档 2 抽表格时，**金额带千分位逗号"1,234,567"**，但搜索"1234567"失败
- 档 4 OCR 时，**"总资产"被识别成"总资立"**，同音字错

**修复**：
- 档 2 抽表格时同时保留**纯数字版本**（`"1234567"` + `"1,234,567"`）
- 关键字搜索时**同音字容错**（"立/产"、"润/纯"）

### 测试 1.2：数字金额准确（误差 < 0.01%）

```python
def test_amount_accuracy():
    doc = parse_document("fixtures/financial_statement.pdf")
    full_text = doc.text
    
    # 抽取所有"营业收入: 1,234,567"格式
    amounts = re.findall(r"营业收入[：:]?\s*([\d,\.]+)", full_text)
    
    # 至少要有 5 年的营业收入
    assert len(amounts) >= 5, f"只抽到 {len(amounts)} 年"
    
    # 每年金额必须 > 0
    for amt in amounts:
        val = float(amt.replace(",", ""))
        assert val > 0
```

**通过标准**：连续 5 年的营业收入都被准确解析（不为空、不为 0）。

### 测试 1.3：日期格式统一（YYYY-MM-DD）

```python
def test_date_format():
    doc = parse_document("fixtures/contract.pdf")
    
    # 抽取所有日期
    dates = re.findall(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?", doc.text)
    
    # 至少要有 3 个日期（签署/生效/到期）
    assert len(dates) >= 3
    
    # 格式必须统一（不能混用 2024-01-01 和 2024年1月1日）
    formats = set()
    for d in dates:
        if "年" in d:
            formats.add("中文")
        elif "-" in d:
            formats.add("ISO")
        elif "/" in d:
            formats.add("US")
    
    assert len(formats) == 1, f"混用日期格式: {formats}"
```

---

## 象限 2：格式验收（结构层）

### 测试 2.1：表格行号保留

```python
def test_table_line_numbers():
    doc = parse_document("fixtures/equity_structure.xlsx")
    
    # 找股权表
    sheet_chunks = [c for c in doc.chunks if c.table_id == "股权结构"]
    assert len(sheet_chunks) > 0, "没找到股权表"
    
    # 每个数据行必须带行号
    for chunk in sheet_chunks:
        if chunk.line_no is None:
            pytest.fail(f"表格行未保留行号: {chunk.text[:50]}")
```

**通过标准**：每个表格 chunk 的 `line_no` 字段非空。

### 测试 2.2：页码保留

```python
def test_page_numbers():
    doc = parse_document("fixtures/multi_page_report.pdf")
    
    # 至少要有 10 个不同页码
    pages = set(c.page for c in doc.chunks if c.page > 0)
    assert len(pages) >= 10, f"只抽到 {len(pages)} 页"
    
    # 页码必须连续（1, 2, 3, ..., N）
    expected = set(range(1, doc.page_count + 1))
    assert pages == expected, f"页码不连续: {pages - expected}"
```

### 测试 2.3：bbox 完整（仅 PDF）

```python
def test_bbox_completeness():
    doc = parse_document("fixtures/complex_layout.pdf", hint="pymupdf")
    
    # PyMuPDF 档必须保留 bbox
    bbox_chunks = [c for c in doc.chunks if c.bbox is not None]
    assert len(bbox_chunks) > 0, "PyMuPDF 档未保留 bbox"
    
    # bbox 必须是 4 元组
    for chunk in bbox_chunks:
        assert len(chunk.bbox) == 4
        x0, y0, x1, y1 = chunk.bbox
        assert x0 < x1 and y0 < y1, f"bbox 非法: {chunk.bbox}"
```

---

## 象限 3：性能验收

### 测试 3.1：解析时延 < 预算

```python
@pytest.mark.parametrize("file,strategy,expected_max_sec", [
    ("fixtures/small_5pages.pdf", "pdf_dots", 3),
    ("fixtures/medium_50pages.pdf", "pdfplumber", 100),
    ("fixtures/large_500pages.pdf", "pymupdf", 1500),
    ("fixtures/scan_100pages.pdf", "mineru", 1000),
])
def test_parse_latency(file, strategy, expected_max_sec):
    doc = parse_document(file, hint=ParseStrategy(strategy))
    
    assert doc.parse_time_ms < expected_max_sec * 1000, \
        f"解析超时: {doc.parse_time_ms}ms > {expected_max_sec * 1000}ms"
```

**通过标准**：

| 档 | 5 页 | 50 页 | 500 页 |
|---|---|---|---|
| 档 1 PDF-dots | < 3s | < 25s | < 250s |
| 档 2 PDFPlumber | < 10s | < 100s | < 1000s |
| 档 3 PyMuPDF | < 15s | < 150s | < 1500s |
| 档 4 MinerU | < 50s | < 500s | < 5000s |

### 测试 3.2：chunk 数量合理

```python
def test_chunk_count_reasonable():
    doc = parse_document("fixtures/typical_report.pdf")
    
    # 数字 PDF：每页 1-3 chunks
    if doc.file_type == FileType.PDF_NATIVE:
        ratio = len(doc.chunks) / doc.page_count
        assert 0.5 < ratio < 5, f"chunk 比例异常: {ratio}/页"
    
    # 扫描件：每页 5-10 chunks
    elif doc.file_type == FileType.PDF_SCAN:
        ratio = len(doc.chunks) / doc.page_count
        assert 3 < ratio < 15
```

---

## 象限 4：健壮性验收

### 测试 4.1：空文件优雅失败

```python
def test_empty_file():
    empty_path = "fixtures/empty.pdf"
    Path(empty_path).touch()  # 0 字节文件
    
    doc = parse_document(empty_path)
    assert doc.error is not None, "空文件应报错"
    assert "empty" in doc.error.lower() or "0 pages" in doc.error.lower()
```

### 测试 4.2：损坏文件优雅失败

```python
def test_corrupted_file():
    corrupted_path = "fixtures/corrupted.pdf"
    Path(corrupted_path).write_bytes(b"not a pdf" * 100)
    
    doc = parse_document(corrupted_path)
    assert doc.error is not None
    assert "parse" in doc.error.lower() or "invalid" in doc.error.lower()
```

### 测试 4.3：密码保护文件

```python
def test_encrypted_file():
    enc_path = "fixtures/encrypted.pdf"
    doc = parse_document(enc_path)
    
    # 应报错，不应静默成功
    assert doc.error is not None
    assert "password" in doc.error.lower() or "encrypt" in doc.error.lower()
```

### 测试 4.4：OCR 4 降级链路

```python
def test_ocr_fallback_chain():
    # 故意用最难的扫描件，触发 4 级降级
    doc = parse_document("fixtures/rotated_scan_30deg.pdf", hint="mineru")
    
    # 即使 OCR 识别率低，也不应静默失败
    assert doc.error is None, f"OCR 链路完全失败: {doc.error}"
    
    # 应至少有部分 chunks（识别率 > 30%）
    assert len(doc.chunks) > 0
    
    # 平均置信度应 > 0.5
    if doc.chunks:
        avg_conf = sum(c.confidence for c in doc.chunks) / len(doc.chunks)
        assert avg_conf > 0.5, f"OCR 置信度过低: {avg_conf}"
```

---

## 完整压测脚本（复制即可跑）

```python
# test_doc_pipeline.py
import pytest
from pathlib import Path
from code_doc_parse_pipeline import parse_document, ParseStrategy, FileType

FIXTURES = Path("tests/fixtures")

# === 象限 1: 内容 ===
class TestContent:
    def test_business_keywords(self):
        keywords = ["营业收入", "净利润", "总资产", "ROE", "经营性现金流"]
        doc = parse_document(FIXTURES / "audit_report.pdf", keywords=keywords)
        assert doc.metadata["validation"]["passed"]
    
    def test_amount_accuracy(self):
        doc = parse_document(FIXTURES / "financial_statement.pdf")
        assert "营业收入" in doc.text
        amounts = re.findall(r"营业收入[：:]?\s*([\d,\.]+)", doc.text)
        assert len(amounts) >= 5


# === 象限 2: 格式 ===
class TestStructure:
    def test_table_line_numbers(self):
        doc = parse_document(FIXTURES / "equity.xlsx")
        for chunk in doc.chunks:
            if chunk.table_id:
                assert chunk.line_no is not None
    
    def test_page_numbers(self):
        doc = parse_document(FIXTURES / "multi_page.pdf")
        assert len(set(c.page for c in doc.chunks)) >= 10
    
    def test_bbox(self):
        doc = parse_document(FIXTURES / "complex.pdf", hint="pymupdf")
        assert any(c.bbox is not None for c in doc.chunks)


# === 象限 3: 性能 ===
class TestPerformance:
    @pytest.mark.parametrize("strategy,max_ms", [
        ("pdf_dots", 3000),
        ("pdfplumber", 10000),
    ])
    def test_latency(self, strategy, max_ms):
        doc = parse_document(FIXTURES / "5page.pdf", hint=ParseStrategy(strategy))
        assert doc.parse_time_ms < max_ms


# === 象限 4: 健壮性 ===
class TestRobustness:
    def test_empty(self):
        empty = FIXTURES / "empty.pdf"
        empty.touch()
        doc = parse_document(empty)
        assert doc.error is not None
    
    def test_corrupted(self):
        corrupted = FIXTURES / "bad.pdf"
        corrupted.write_bytes(b"not a pdf" * 100)
        doc = parse_document(corrupted)
        assert doc.error is not None
```

---

## 验收日报（每次解析后填）

| 字段 | 值 | 备注 |
|---|---|---|
| 文件 | `xxx.pdf` | 200 页 |
| 档位 | 档 2 PDFPlumber | 数字 PDF + 表格 |
| 时延 | 280s | 1.4s/页 |
| Q1 业务关键字 | 5/5 命中 | ✅ |
| Q2 表格行号 | 保留 | ✅ |
| Q2 页码 | 200/200 | ✅ |
| Q3 chunk 比例 | 2.3 chunks/页 | 合理 |
| Q4 异常处理 | N/A | 无异常 |
| **结论** | **通过** | 入库 |

---

## 4 象限 vs 4 硬骨头（不要混）

| 4 象限（本资产） | 4 硬骨头（视频主题） |
|---|---|
| 内容 / 格式 / 性能 / 健壮 | OCR ≠ 文档解析 / Excel 合并单元格 / 扫描件旋转 / 模糊 PDF |
| 验收测试维度 | 业务痛点维度 |
| **回答"对不对"** | **回答"难在哪"** |

兄弟看 4 象限检查清单时，记得它和 4 硬骨头是**正交**的——4 象限是验收框架，4 硬骨头是踩坑故事。
