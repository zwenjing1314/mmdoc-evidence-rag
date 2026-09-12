# Global-Region 与 Oracle-Page→Region Baseline 修改记录

更新时间：2026-05-29

## 1. 修改目的

本次修改用于补齐中文年报检索实验中的两个关键 baseline：

1. `global-region`：不经过页面级召回，直接在单篇文档的所有 evidence nodes 中检索。
2. `oracle-page -> region`：假设页面级召回完全正确，只在 gold evidence pages 内进行区域级节点检索。

这两个 baseline 用于回答：

```text
当前 Page→Region 效果不好，到底是页面召回错了，还是区域节点排序能力不足？
```

## 2. 新增配置文件

新增：

```text
configs/experiments/cn_global_region.yaml
configs/experiments/cn_oracle_page_region.yaml
```

运行命令：

```bash
uv run mdr retrieve --config configs/experiments/cn_global_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_global_region/latest
```

```bash
uv run mdr retrieve --config configs/experiments/cn_oracle_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_oracle_page_region/latest
```

## 3. 代码修改

主要修改文件：

```text
src/mmdocrag/retrieval/pipeline.py
src/mmdocrag/evaluation/metrics.py
tests/test_retrieval_metrics.py
```

### 3.1 `global_region`

新增函数：

```python
retrieve_global_region()
```

逻辑：

```text
query -> 当前文档所有 nodes -> 节点级检索 -> Top-K nodes
```

它不使用页面级召回，直接在节点粒度上检索。

### 3.2 `oracle_page_region`

新增函数：

```python
retrieve_oracle_page_region()
```

逻辑：

```text
query -> gold evidence pages -> gold pages 内部 nodes -> 节点级检索 -> Top-K nodes
```

它用于估计区域级检索能力上限。

### 3.3 nDCG 指标修正

旧版 `nDCG` 在 node-level 检索结果中可能重复计算同一个 gold page，导致 `nDCG > 1`。

本次修改后：

1. 如果 hit 是 node 结果，并且 query 有 gold nodes，则优先按 node_id 判断是否命中。
2. 如果 hit 是 page 结果，或者 query 没有 gold nodes，则按 page_id 判断是否命中。

这样可以避免同一 gold page 上的多个错误 node 被重复计为相关结果。

## 4. 当前实验结果

### 4.1 Global-Region

```text
page_recall@1  = 0.2500
page_recall@5  = 0.3937
page_recall@10 = 0.3937
mrr            = 0.2059
ndcg@5         = 0.1408
ndcg@10        = 0.1408
region_hit@5   = 0.2812
```

含义：

```text
直接在文档内部所有节点中检索，Region Hit@5 达到 0.2812。
```

### 4.2 Oracle-Page→Region

```text
page_recall@1  = 1.0000
page_recall@5  = 1.0000
page_recall@10 = 1.0000
mrr            = 0.4800
ndcg@5         = 0.4768
ndcg@10        = 0.4768
region_hit@5   = 0.7875
```

含义：

```text
如果页面已经正确，区域级节点检索的 Hit@5 可以达到 0.7875。
```

这说明当前 Page→Region 的瓶颈很可能主要来自页面级召回或候选页面质量，而不是区域节点检索完全不可行。

## 5. 验证命令

```bash
uv run ruff check src tests
uv run pytest
```

当前结果：

```text
All checks passed
14 passed
```

## 6. 后续建议

下一步建议实现：

```text
single-node vs evidence-set
```

即比较：

1. 只取最高分单个 node。
2. 选择一组覆盖“指标、年份、数值、单位”的 evidence set。

这一步可以直接支撑论文中的“最小充分证据集合”创新点。

