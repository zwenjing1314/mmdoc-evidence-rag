# Hybrid-Page 与 Hybrid-Page→Region 修改记录

更新时间：2026-05-31

## 1. 修改目的

本次修改完成两项实验开发任务：

1. 整理现有中文年报检索实验表。
2. 新增 `Hybrid-page` 和 `Hybrid-Page→Region` 两个 baseline。

修改目标是验证：

```text
BM25 关键词检索和 Dense 语义检索融合后，是否能提升页面召回，并进一步改善区域级证据定位。
```

## 2. 新增方法

### 2.1 Hybrid-page

方法流程：

```text
query
 -> BM25-page 检索
 -> Dense-page 检索
 -> RRF 融合页面排序
 -> Top-K pages
```

实现函数：

```python
retrieve_hybrid_pages()
```

配置文件：

```text
configs/experiments/cn_hybrid_page.yaml
```

运行命令：

```bash
uv run mdr retrieve --config configs/experiments/cn_hybrid_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_hybrid_page/latest
```

### 2.2 Hybrid-Page→Region

方法流程：

```text
query
 -> Hybrid-page 页面召回
 -> 候选页面内收集 evidence nodes
 -> 区域级节点检索
 -> 页面排序与节点排序 RRF 融合
 -> Top-K evidence nodes
```

实现函数：

```python
retrieve_hybrid_page_region()
```

配置文件：

```text
configs/experiments/cn_hybrid_page_region.yaml
```

运行命令：

```bash
uv run mdr retrieve --config configs/experiments/cn_hybrid_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_hybrid_page_region/latest
```

## 3. 主要代码修改

主要修改文件：

```text
src/mmdocrag/retrieval/pipeline.py
tests/test_retrieval_metrics.py
```

新增配置文件：

```text
configs/experiments/cn_hybrid_page.yaml
configs/experiments/cn_hybrid_page_region.yaml
```

新增实验表文档：

```text
docs/run_project/current_experiment_results.md
```

## 4. 关键实现说明

### 4.1 页面融合

页面融合使用已有的：

```python
reciprocal_rank_fusion()
```

对 BM25 和 Dense 的页面排序结果进行融合。

当前默认融合方法：

```yaml
page_methods:
  - bm25
  - dense
```

当前仍采用单文档内部检索：

```yaml
search_scope: document
```

### 4.2 区域检索复用

本次将 Page→Region 的后半段逻辑抽出为：

```python
retrieve_regions_from_page_hits()
```

这样普通 `Page→Region` 和 `Hybrid-Page→Region` 可以复用同一套候选节点收集、节点检索和页面-节点融合逻辑。

## 5. 当前实验结果

### 5.1 Hybrid-page

```text
page_recall@1  = 0.1062
page_recall@5  = 0.3000
page_recall@10 = 0.6562
mrr            = 0.2272
ndcg@5         = 0.2107
ndcg@10        = 0.3247
region_hit@5   = 0.0000
```

观察：

```text
Hybrid-page 的 Page Recall@10 高于 Dense-page，但 Page Recall@5 低于 Dense-page，说明当前融合扩大了覆盖范围，但前排排序还不够好。
```

### 5.2 Hybrid-Page→Region

```text
page_recall@1  = 0.1062
page_recall@5  = 0.2938
page_recall@10 = 0.2938
mrr            = 0.0184
ndcg@5         = 0.0134
ndcg@10        = 0.0134
region_hit@5   = 0.0312
```

观察：

```text
Hybrid-Page→Region 当前效果较差，说明页面召回融合后的前排页面质量和区域候选节点噪声仍然存在问题，不能简单认为页面融合会自动提升区域定位。
```

## 6. 质量检查

已运行：

```bash
uv run ruff check src tests
uv run pytest
```

当前结果：

```text
All checks passed
16 passed
```

## 7. 后续建议

下一步建议围绕 Hybrid 的失败原因做误差分析：

1. 对比 `Dense-page` 和 `Hybrid-page` 的 Top-5 页面差异。
2. 检查 `Hybrid-page` 是否将 BM25 的噪声页面融合到了前排。
3. 调整 RRF 参数或尝试加权融合。
4. 增加 `page_top_k=20/30` 的 Page→Region 对照实验。
5. 继续实现 `single-node vs evidence-set`，不要只依赖单个最高分节点。

