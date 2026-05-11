# 关于四张标准表和 demo 数据生成的疑问解答

本文记录两个问题：

1. `documents.parquet` 是由什么生成的？
2. 为什么运行 `uv run mdr prepare --dataset demo` 后可以生成四个 parquet 文件？demo 原始文件在哪里？

## 1. 你的理解是对的

你已经理解了三张表的来源关系：

```text
MMDocIR_annotations.jsonl  -> queries.parquet
MMDocIR_pages.parquet      -> pages.parquet
MMDocIR_layouts.parquet    -> nodes.parquet
```

更具体地说：

| 原始文件 | 作用 | 项目标准表 |
|---|---|---|
| `MMDocIR_annotations.jsonl` | 问题、答案、证据页、证据区域标注 | `queries.parquet` |
| `MMDocIR_pages.parquet` | 页面级数据，如页面 OCR/VLM 文本 | `pages.parquet` |
| `MMDocIR_layouts.parquet` | 区域级数据，如段落、表格、图表、bbox | `nodes.parquet` |

这三张表分别服务于：

- 问题标注；
- 页面级检索；
- 区域级证据定位。

## 2. 那 `documents.parquet` 是由什么生成的？

`documents.parquet` 是**文档级索引表**，它不是直接由某一个单独的 MMDocIR 文件一对一生成，而是从多个原始文件里的文档信息汇总出来的。

在 MMDocIR 中，文档级信息主要来自：

```text
MMDocIR_annotations.jsonl 中的 doc_name / domain
MMDocIR_pages.parquet 中的 doc_name / domain
MMDocIR_layouts.parquet 中的 doc_name / domain
```

其中最核心的是：

```text
doc_name
domain
```

项目会把每个唯一的 `doc_name` 当成一个文档，生成一条 `DocumentRecord`。

例如 MMDocIR 里有一个文档：

```text
doc_name = PH_2016.06.08_Economy-Final.pdf
domain = Research report / Introduction
```

那么 `documents.parquet` 里就应该有类似一行：

```text
doc_id: PH_2016.06.08_Economy-Final.pdf
dataset: mmdocir
title: PH_2016.06.08_Economy-Final.pdf
domain: Research report / Introduction
language: mixed
num_pages: 该文档页数
```

所以可以这样理解：

```text
documents.parquet = 对文档集合做去重和汇总后得到的文档目录表
```

它类似一个“文档总表”或“文档索引”。

## 3. 为什么需要 `documents.parquet`

如果只有 `pages.parquet`、`nodes.parquet`、`queries.parquet`，也能做一部分检索，但项目会缺少文档层面的统一管理。

`documents.parquet` 的作用包括：

1. 记录数据集中有哪些文档。
2. 记录每个文档属于哪个数据集。
3. 记录文档标题、领域、语言、来源路径、页数等信息。
4. 方便后续按文档统计实验结果。
5. 方便中文年报和 MMDocIR 走同一套流程。

例如后续写论文时可以统计：

```text
本次实验共处理多少个文档？
每个文档平均多少页？
不同 domain 下检索效果是否不同？
中文年报和 MMDocIR 的文档数量分别是多少？
```

这些都依赖 `documents.parquet`。

## 4. 四张标准表之间的关系

可以把四张表理解成四个层级：

```text
documents.parquet
  ↓
pages.parquet
  ↓
nodes.parquet

queries.parquet 通过 evidence_page_ids / evidence_node_ids 指向 pages 和 nodes
```

更直观地说：

```text
一个 document 有多个 page
一个 page 有多个 evidence node
一个 query 会标注正确的 page 或 node
```

例如：

```text
Document: 示例科技 2025 年报
  Page 1: 主要财务指标
    Node 1: 营业收入段落
    Node 2: 财务指标表格
  Page 2: 现金流量表
    Node 3: 现金流量段落

Query: 示例科技2025年营业收入是多少？
  evidence_page_ids = [Page 1]
  evidence_node_ids = [Node 1, Node 2]
```

这就是项目数据结构的核心。

## 5. 为什么 `uv run mdr prepare --dataset demo` 能生成四个文件？

因为 `demo` 不是从磁盘上的原始 demo 文件读出来的。

`demo` 是代码里内置的小样本数据。

代码位置：

```text
src/mmdocrag/datasets/adapters.py
```

对应函数：

```python
def prepare_demo(limit_docs: int | None = None) -> PrepareResult:
```

这个函数内部直接手写了：

```text
documents
pages
nodes
queries
```

也就是：

```python
documents = [
    DocumentRecord(...),
    DocumentRecord(...),
]

pages = [
    PageRecord(...),
    PageRecord(...),
    PageRecord(...),
]

nodes = [
    EvidenceNode(...),
    EvidenceNode(...),
    EvidenceNode(...),
    EvidenceNode(...),
]

queries = [
    QueryRecord(...),
    QueryRecord(...),
    QueryRecord(...),
]
```

最后调用：

```python
write_processed_dataset(processed_dir, documents, pages, nodes, queries)
```

这一步就会写出四个文件：

```text
documents.parquet
pages.parquet
nodes.parquet
queries.parquet
```

## 6. `demo` 数据具体在哪里？

它不在 `data/raw/demo/` 里。

它在代码里：

```text
src/mmdocrag/datasets/adapters.py
```

具体在 `prepare_demo()` 函数中。

当前 demo 里内置了两个文档：

```text
demo_finance_2025
demo_contract_001
```

三个页面：

```text
demo_finance_2025_p1
demo_finance_2025_p2
demo_contract_001_p1
```

四个证据节点：

```text
demo_finance_2025_p1_n1
demo_finance_2025_p1_n2
demo_finance_2025_p2_n1
demo_contract_001_p1_n1
```

三个问题：

```text
demo_q1: 示例科技2025年营业收入是多少？
demo_q2: 经营活动产生的现金流量净额是多少？
demo_q3: 合同服务期限是什么？
```

所以运行：

```bash
uv run mdr prepare --dataset demo
```

会看到：

```text
documents = 2
pages = 3
nodes = 4
queries = 3
```

这些数字就是代码里内置数据的数量。

## 7. 为什么要内置 demo 数据？

因为真实数据可能还没放好、字段还没适配、文件又很大。

如果没有 demo 数据，那么每次验证代码都必须依赖 MMDocIR 或中文年报。

这样会导致：

- 调试很慢；
- 没数据时无法跑流程；
- 适配器没写好时检索代码无法测试；
- 开题前不容易快速展示完整闭环。

内置 demo 的作用是：

```text
不依赖真实数据，也能验证 prepare -> retrieve -> evaluate -> export-demo 全流程
```

它不是最终实验数据，而是“系统自检数据”。

## 8. `prepare --dataset demo` 的完整调用链

命令：

```bash
uv run mdr prepare --dataset demo
```

调用链如下：

```text
uv run
  ↓
mdr 命令
  ↓
src/mmdocrag/cli.py 中的 prepare()
  ↓
prepare_dataset(dataset="demo")
  ↓
prepare_demo()
  ↓
构造 DocumentRecord / PageRecord / EvidenceNode / QueryRecord
  ↓
write_processed_dataset()
  ↓
写出四个 parquet 文件
```

其中：

```text
src/mmdocrag/cli.py
```

负责命令行入口。

```text
src/mmdocrag/datasets/adapters.py
```

负责生成 demo 数据。

```text
src/mmdocrag/io.py
```

负责写 parquet。

## 9. `write_processed_dataset()` 做了什么

代码位置：

```text
src/mmdocrag/io.py
```

函数：

```python
def write_processed_dataset(
    processed_dir,
    documents,
    pages,
    nodes,
    queries,
) -> None:
    write_records(processed_dir / "documents.parquet", documents)
    write_records(processed_dir / "pages.parquet", pages)
    write_records(processed_dir / "nodes.parquet", nodes)
    write_records(processed_dir / "queries.parquet", queries)
```

也就是说，只要传入四组数据对象，它就会固定写出四张标准表。

这就是为什么 `demo`、`mmdocir`、`cn_annual_reports` 最终都能生成同样的四个文件。

## 10. demo 和真实数据的区别

| 对比项 | demo | MMDocIR / 中文年报 |
|---|---|---|
| 数据来源 | 代码内置 | 磁盘原始文件 |
| 是否需要 raw 文件 | 不需要 | 需要 |
| 数据规模 | 很小 | 很大 |
| 作用 | 测试流程、演示闭环 | 正式实验 |
| 是否可作为论文结果 | 不可作为正式结果 | 可以作为实验结果 |

所以：

```text
demo 用来证明系统能跑
真实数据用来支撑论文实验
```

## 11. 对 MMDocIR 来说，四张表应该如何生成

等 MMDocIR 适配器精修后，理想关系是：

```text
MMDocIR_annotations.jsonl
  -> documents.parquet 的 doc_name/domain 汇总
  -> queries.parquet 的 Q/A/evidence_page_ids/evidence_bboxes

MMDocIR_pages.parquet
  -> pages.parquet 的 page_id/page_text/ocr_text/vlm_text

MMDocIR_layouts.parquet
  -> nodes.parquet 的 node_id/node_type/page_id/bbox/text/ocr_text/vlm_text
```

其中 `documents.parquet` 可以主要由 annotations 生成，也可以结合 pages/layouts 统计页数和领域。

更准确地说：

```text
documents.parquet = 从 annotations/pages/layouts 中抽取唯一 doc_name 后汇总生成
```

## 12. 一句话总结

你的疑问可以这样总结：

```text
queries/pages/nodes 都能找到明确的原始文件来源，
documents 是从文档级字段 doc_name/domain 汇总去重生成的文档总表。
```

而：

```text
demo 没有原始文件，
它是 prepare_demo() 函数中手写的内置小样本，
用于不依赖真实数据时跑通完整实验流程。
```

