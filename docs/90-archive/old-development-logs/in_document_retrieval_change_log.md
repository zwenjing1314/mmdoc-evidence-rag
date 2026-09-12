# 单文档内部检索修改记录

修改日期：2026-05-26

## 1. 修改背景

原始检索代码中，`retrieve_pages()` 会将 `pages.parquet` 中的所有页面作为候选库：

```python
docs = [page.page_text or page.ocr_text or page.page_id for page in pages]
scores_by_query = score_texts([query.question for query in queries], docs, method, encoder)
```

这意味着每个问题都会在全部年报的全部页面中计算分数。例如中文年报实验中，某个属于“万科A：2025年年度报告”的问题，会同时检索其他公司年报的页面。

这种方式属于：

```text
corpus-level retrieval / 跨文档全库检索
```

它适合企业知识库中“不知道答案在哪个文档”的场景，但不完全适合当前中文年报实验的主目标。

当前中文年报实验更关注：

```text
已知问题属于某一份年报，在该年报内部定位正确页面和区域证据
```

因此需要增加：

```text
document-level retrieval / in-document retrieval / 单文档内部检索
```

## 2. 修改目标

本次修改目标是让检索模块同时支持两种检索范围：

| 检索范围 | 配置值 | 含义 | 适用场景 |
|---|---|---|---|
| 全库检索 | `corpus` | 每个 query 检索全部文档的全部页面或节点 | 多文档知识库问答 |
| 单文档检索 | `document` | 每个 query 只检索 `query.doc_id` 对应文档内的页面或节点 | 长文档内部证据定位 |

中文年报主实验默认改为 `document`，以便更准确评估长文档内部页面召回和区域定位能力。

## 3. 修改文件

### 3.1 检索主逻辑

修改文件：

```text
src/mmdocrag/retrieval/pipeline.py
```

新增内容：

- `SEARCH_SCOPE_CORPUS`
- `SEARCH_SCOPE_DOCUMENT`
- `normalize_search_scope()`
- `group_queries_by_doc()`
- `group_pages_by_doc()`
- `group_nodes_by_doc()`

修改函数：

- `run_retrieval()`
- `retrieve_pages()`
- `retrieve_nodes()`
- `retrieve_page_region()`

### 3.2 中文年报实验配置

修改文件：

```text
configs/experiments/cn_bm25_page.yaml
configs/experiments/cn_dense_page.yaml
configs/experiments/cn_page_region.yaml
```

新增配置：

```yaml
retriever:
  search_scope: document
```

### 3.3 单元测试

修改文件：

```text
tests/test_retrieval_metrics.py
```

新增测试：

```python
test_document_scope_retrieves_only_query_document_pages()
```

该测试验证：

- `search_scope: corpus` 时，query 可以被其他文档的强匹配页面吸引；
- `search_scope: document` 时，query 只能检索自身 `doc_id` 对应文档内的页面。

## 4. 修改后的代码逻辑

### 4.1 全库检索模式

当配置为：

```yaml
retriever:
  search_scope: corpus
```

或者不写 `search_scope` 时，系统保持原有逻辑：

```text
query
  -> 检索全部 documents 的全部 pages/nodes
  -> 返回全库 Top-k
```

该模式适合多文档知识库问答。

### 4.2 单文档内部检索模式

当配置为：

```yaml
retriever:
  search_scope: document
```

系统会按照 `query.doc_id` 对页面或节点进行过滤：

```text
query.doc_id
  -> 找到同一 doc_id 下的 pages/nodes
  -> 只在该文档内部计算分数
  -> 返回文档内 Top-k
```

对应逻辑：

```python
pages_by_doc = group_pages_by_doc(pages)
for doc_id, doc_queries in group_queries_by_doc(queries).items():
    doc_pages = pages_by_doc.get(doc_id, [])
    retrieve_pages(doc_queries, doc_pages, ...)
```

节点检索同理：

```python
nodes_by_doc = group_nodes_by_doc(nodes)
for doc_id, doc_queries in group_queries_by_doc(queries).items():
    doc_nodes = nodes_by_doc.get(doc_id, [])
    retrieve_nodes(doc_queries, doc_nodes, ...)
```

## 5. 对 Page→Region 的影响

原始 `Page→Region` 流程是：

```text
全部页面召回
  -> 取 Top-k 页面
  -> 在 Top-k 页面对应 nodes 内做区域检索
```

修改后，如果配置 `search_scope: document`，流程变为：

```text
只在 query 所属文档内召回页面
  -> 取该文档内 Top-k 页面
  -> 在这些页面对应 nodes 内做区域检索
```

这样可以避免其他公司年报中的相似页面干扰中文年报实验。

## 6. 为什么这次修改重要

原始全库检索实际上混合了两个任务：

```text
任务 1：判断答案在哪一份文档
任务 2：判断答案在该文档的哪一页、哪一区域
```

而当前论文主线是长文档内部证据定位，重点应是第二个任务：

```text
在已知文档内部进行页面召回和区域定位
```

因此，单文档内部检索可以让实验结论更清晰：

- Page Recall 反映文档内部页面定位能力；
- Region Hit 反映正确页面或候选页面内的区域证据定位能力；
- 后续 `oracle-page→region` 和 `evidence set` 实验更容易解释。

## 7. 后续建议

本次修改只是实现检索范围控制，后续仍建议继续完成：

1. 增加 `global-region` baseline；
2. 增加 `oracle-page→region` baseline；
3. 增加 `evidence set` 数据结构；
4. 实现 `slot_coverage`、`unit_consistency`、`numeric_match`；
5. 做 `corpus` 与 `document` 两种范围的对比实验；
6. 在论文中明确区分“跨文档检索”和“文档内证据定位”。

## 8. 推荐运行命令

重新运行中文年报文档内检索实验：

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest

uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest

uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

如果需要保留全库检索对比实验，可以新建配置文件并设置：

```yaml
retriever:
  search_scope: corpus
```

## 9. 本次修改后的验证结果

本次修改后已运行以下检查：

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run pytest
```

结果：

```text
ruff check: All checks passed
pytest: 11 passed
```

同时重新运行了中文年报三组文档内检索实验。

### 9.1 BM25-page，document scope

运行命令：

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest
```

结果：

| 指标 | 数值 |
|---|---:|
| Page Recall@1 | 0.0813 |
| Page Recall@5 | 0.2812 |
| Page Recall@10 | 0.4062 |
| MRR | 0.1784 |
| nDCG@5 | 0.0747 |
| nDCG@10 | 0.0908 |
| Region Hit@5 | 0.0000 |

### 9.2 Dense-page，document scope

运行命令：

```bash
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest
```

结果：

| 指标 | 数值 |
|---|---:|
| Page Recall@1 | 0.2437 |
| Page Recall@5 | 0.4750 |
| Page Recall@10 | 0.6188 |
| MRR | 0.3420 |
| nDCG@5 | 0.1588 |
| nDCG@10 | 0.1767 |
| Region Hit@5 | 0.0000 |

### 9.3 Page→Region，document scope

运行命令：

```bash
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

结果：

| 指标 | 数值 |
|---|---:|
| Page Recall@1 | 0.2375 |
| Page Recall@5 | 0.4500 |
| Page Recall@10 | 0.4500 |
| MRR | 0.3125 |
| nDCG@5 | 0.1571 |
| nDCG@10 | 0.1571 |
| Region Hit@5 | 0.2125 |

说明：

- 切换到 `document` scope 后，页面召回指标明显高于之前全库检索设置；
- Page→Region 仍然能够返回区域级节点，Region Hit@5 为 0.2125；
- 该结果仍属于 baseline，后续需要继续补充 `global-region`、`oracle-page→region` 和 `evidence set` 实验。
