# 实验进度与运行命令记录

更新时间：2026-05-26

本文档用于记录当前项目实验进度、已经完成的工作、常用运行命令以及每条命令的作用。后续继续做实验时，可以在本文档末尾按日期追加新的实验记录。

## 1. 当前实验目标

当前阶段重点是中文年度报告数据集实验，不再把所有内容一次性铺开，而是先围绕“单文档内部证据检索”形成稳定实验基础。

当前实验任务可以概括为：

1. 将中文年报 PDF 解析为标准化数据表。
2. 将页面文本进一步切分为段落、表格块和表格行级证据节点。
3. 构建中文年报问答标注，记录答案、单位、证据页和证据节点。
4. 实现页面级检索和页面到区域的两阶段检索。
5. 将检索方式从全语料检索调整为单文档内部检索。
6. 输出可复现的指标结果，为后续 evidence set、重排序和可信验证实验打基础。

## 2. 当前数据状态

中文年报处理后的标准数据位于：

```text
data/processed/cn_annual_reports/
```

当前已经生成的标准表包括：

| 文件 | 作用 | 当前数量 |
| --- | --- | --- |
| `documents.parquet` | 文档级信息，一份年报对应一条文档记录 | 20 |
| `pages.parquet` | 页面级信息，一页 PDF 对应一条页面记录 | 5327 |
| `nodes.parquet` | 细粒度证据节点，包括段落、表格块和表格行 | 99304 |
| `queries.parquet` | 问答标注，包含问题、答案、证据页和证据节点 | 160 |

原始标注文件主要位于：

```text
data/raw/cn_annual_reports/
```

其中：

| 文件 | 作用 |
| --- | --- |
| `qa_annotations.csv` | 早期人工标注版本，作为回退和对照 |
| `qa_annotations_v2.csv` | 自动扩展后的新版标注 |
| `qa_annotations_v2_reviewed.csv` | 人工检查和修订后的新版标注，当前实验优先使用 |
| `qa_annotations_v2_generation_log.md` | V2 标注生成过程记录 |

## 3. 当前代码状态

目前项目已经完成以下核心代码能力：

1. `prepare`：将原始年报数据解析成标准 parquet 表。
2. `build-cn-annotations`：生成中文年报问答标注。
3. `retrieve`：运行检索实验。
4. `evaluate`：评价检索结果。
5. `export-demo`：导出开题展示用结果。

当前检索已经支持两种检索范围：

| 检索范围 | 配置值 | 含义 |
| --- | --- | --- |
| 全语料检索 | `search_scope: corpus` | 一个问题会在所有文档页面或节点中检索 |
| 单文档内部检索 | `search_scope: document` | 一个问题只在其所属文档内部检索 |

中文年报实验当前采用：

```yaml
search_scope: document
```

这表示每个问题只在对应年报内部查找答案页面和证据节点，更符合当前中文年报实验设定。

## 4. 环境与命令说明

项目使用 `uv` 管理 Python 环境和依赖。正常情况下，在项目根目录运行命令：

```bash
cd /Users/zhouwenjing/Documents/WorkTransfer/mmdoc-evidence-rag
```

如果系统中 `uv` 命令可以直接使用，运行：

```bash
uv run mdr --help
```

如果需要使用本机安装路径，也可以使用：

```bash
UV_CACHE_DIR=.uv-cache UV_PYTHON_INSTALL_DIR=.uv-python /Users/zhouwenjing/.local/bin/uv run mdr --help
```

后文为了简洁，统一写成 `uv run ...`。

## 5. 数据准备命令

### 5.1 准备 demo 数据

```bash
uv run mdr prepare --dataset demo
```

作用：

用于生成内置 tiny demo 数据。即使没有真实数据，也可以跑通项目的完整流程。

主要输出：

```text
data/processed/demo/documents.parquet
data/processed/demo/pages.parquet
data/processed/demo/nodes.parquet
data/processed/demo/queries.parquet
```

适用场景：

1. 检查项目是否能正常运行。
2. 快速验证 CLI、检索和评价流程。
3. 在真实数据未准备好时进行演示。

### 5.2 生成中文年报 V2 问答标注

```bash
uv run mdr build-cn-annotations --questions-per-doc 8 --limit-docs 20
```

作用：

根据中文年报 PDF 内容生成问答标注，每份年报目标生成约 8 条问题。

问题类型包括：

1. 报告年度或报告标题。
2. 营业收入。
3. 归属于上市公司股东的净利润。
4. 经营活动产生的现金流量净额。
5. 研发投入或研发费用。
6. 资产总额。
7. 风险文本。
8. 同比变化或原因类问题。

主要输出：

```text
data/raw/cn_annual_reports/qa_annotations_v2.csv
data/raw/cn_annual_reports/qa_annotations_v2_generation_log.md
```

说明：

当前实际实验优先使用人工检查后的：

```text
data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv
```

### 5.3 准备中文年报标准数据

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

作用：

将中文年报原始 PDF 和标注文件转换为项目统一格式。

主要工作包括：

1. 逐页解析 PDF。
2. 生成页面级 `pages.parquet`。
3. 将页面内容切分为段落、表格块和表格行级证据节点。
4. 生成 `nodes.parquet`。
5. 读取 `qa_annotations_v2_reviewed.csv` 或回退读取旧标注。
6. 生成 `queries.parquet`。
7. 生成文档级 `documents.parquet`。

主要输出：

```text
data/processed/cn_annual_reports/documents.parquet
data/processed/cn_annual_reports/pages.parquet
data/processed/cn_annual_reports/nodes.parquet
data/processed/cn_annual_reports/queries.parquet
```

当前处理结果：

```text
documents: 20
pages: 5327
nodes: 99304
queries: 160
```

## 6. 检索实验命令

### 6.1 BM25 页面级检索

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
```

作用：

运行 BM25 页面级检索 baseline。

当前配置要点：

```yaml
dataset: cn_annual_reports
retriever:
  type: bm25_page
  search_scope: document
  top_k: [1, 5, 10]
```

含义：

1. 使用中文年报数据集。
2. 使用 BM25 关键词检索方法。
3. 每个问题只在其所属年报内部检索。
4. 最多返回 Top-10 页面。

主要输出：

```text
runs/retrieval/cn_bm25_page/时间戳目录/predictions.parquet
runs/retrieval/cn_bm25_page/时间戳目录/config.json
runs/retrieval/cn_bm25_page/时间戳目录/run_info.json
```

其中 `latest` 会指向最新一次运行结果：

```text
runs/retrieval/cn_bm25_page/latest/
```

### 6.2 Dense 页面级检索

```bash
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
```

作用：

运行 Dense-page 页面级检索 baseline。

当前配置要点：

```yaml
dataset: cn_annual_reports
retriever:
  type: dense_page
  search_scope: document
  encoder: BAAI/bge-m3
  top_k: [1, 5, 10]
```

含义：

1. 优先尝试本地 `sentence-transformers` 模型。
2. 如果本地没有可用模型，则回退到 TF-IDF 方式，保证离线可复现。
3. 每个问题只在其所属年报内部检索。

主要输出：

```text
runs/retrieval/cn_dense_page/时间戳目录/predictions.parquet
runs/retrieval/cn_dense_page/时间戳目录/config.json
runs/retrieval/cn_dense_page/时间戳目录/run_info.json
```

### 6.3 Page to Region 两阶段检索

```bash
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
```

作用：

运行页面到区域的两阶段检索。

基本流程：

1. 先在单篇年报内部做页面级粗召回。
2. 在召回页面中取出候选证据节点。
3. 对候选节点进行区域级检索。
4. 结合页面级排序和节点级排序进行融合重排。
5. 输出段落、表格块或表格行级证据节点。

主要输出：

```text
runs/retrieval/cn_page_region/时间戳目录/predictions.parquet
runs/retrieval/cn_page_region/时间戳目录/config.json
runs/retrieval/cn_page_region/时间戳目录/run_info.json
```

## 7. 评价命令

### 7.1 评价 BM25 页面级检索

```bash
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest
```

作用：

读取 BM25 最新一次检索结果，并和 `queries.parquet` 中的证据页进行对比，计算检索指标。

主要输出：

```text
runs/retrieval/cn_bm25_page/latest/metrics.json
runs/retrieval/cn_bm25_page/latest/errors.csv
runs/retrieval/cn_bm25_page/latest/summary.md
```

当前最新结果：

| 指标 | 数值 |
| --- | ---: |
| Page Recall@1 | 0.0813 |
| Page Recall@5 | 0.2812 |
| Page Recall@10 | 0.4062 |
| MRR | 0.1784 |
| nDCG@5 | 0.0747 |
| nDCG@10 | 0.0908 |
| Region Hit@5 | 0.0000 |

说明：

BM25 是关键词检索 baseline。它对完全匹配的问题有效，但对同义表达、长页面噪声和财务表述变化比较敏感。

### 7.2 评价 Dense 页面级检索

```bash
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest
```

作用：

评价 Dense-page 最新一次检索结果。

主要输出：

```text
runs/retrieval/cn_dense_page/latest/metrics.json
runs/retrieval/cn_dense_page/latest/errors.csv
runs/retrieval/cn_dense_page/latest/summary.md
```

当前最新结果：

| 指标 | 数值 |
| --- | ---: |
| Page Recall@1 | 0.2437 |
| Page Recall@5 | 0.4750 |
| Page Recall@10 | 0.6188 |
| MRR | 0.3420 |
| nDCG@5 | 0.1588 |
| nDCG@10 | 0.1767 |
| Region Hit@5 | 0.0000 |

说明：

Dense-page 当前页级召回明显高于 BM25-page，是后续页面级召回的主要 baseline。

### 7.3 评价 Page to Region 两阶段检索

```bash
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

作用：

评价两阶段检索结果，包括页面级命中和区域级证据节点命中。

主要输出：

```text
runs/retrieval/cn_page_region/latest/metrics.json
runs/retrieval/cn_page_region/latest/errors.csv
runs/retrieval/cn_page_region/latest/summary.md
```

当前最新结果：

| 指标 | 数值 |
| --- | ---: |
| Page Recall@1 | 0.2375 |
| Page Recall@5 | 0.4500 |
| Page Recall@10 | 0.4500 |
| MRR | 0.3125 |
| nDCG@5 | 0.1571 |
| nDCG@10 | 0.1571 |
| Region Hit@5 | 0.2125 |

说明：

Page to Region 的重点不是单纯提升页级召回，而是在召回页面基础上进一步返回细粒度证据节点。当前 Region Hit@5 仍然较低，说明后续需要重点改进区域级检索、证据集合构建和重排序。

## 8. 质量检查命令

### 8.1 代码格式化

```bash
uv run ruff format src tests
```

作用：

统一格式化 `src` 和 `tests` 下的 Python 代码。

### 8.2 代码规范检查

```bash
uv run ruff check src tests
```

作用：

检查代码是否存在风格问题、未使用导入、明显错误等。

当前状态：

```text
All checks passed!
```

### 8.3 单元测试

```bash
uv run pytest
```

作用：

运行项目测试，检查数据模型、检索逻辑、评价指标等是否正常。

当前状态：

```text
11 passed
```

## 9. 推荐完整运行顺序

如果从头重新跑中文年报实验，建议按下面顺序执行：

```bash
cd /Users/zhouwenjing/Documents/WorkTransfer/mmdoc-evidence-rag
```

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest
```

```bash
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest
```

```bash
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

```bash
uv run ruff check src tests
uv run pytest
```

## 10. 当前实验结论

当前中文年报实验已经完成了一个可运行、可评价、可复现的检索实验基础。

已经可以说明：

1. 中文年报 PDF 可以被解析为页面级和节点级标准数据。
2. 问答标注可以映射到真实页面和证据节点。
3. BM25、Dense-page、Page to Region 三类 baseline 可以运行。
4. 单文档内部检索已经实现，实验设定比之前更加合理。
5. Dense-page 的页级召回明显优于 BM25-page。
6. Page to Region 能够返回区域级证据节点，但区域命中率还需要继续提升。

当前还不能过度声称：

1. Page to Region 已经显著优于 Dense-page。
2. 区域级证据定位已经达到可用水平。
3. 已经完成可信生成和拒答机制。
4. 已经完成真正的视觉检索或多模态融合实验。

## 11. 下一阶段建议

下一阶段建议围绕导师修改后的创新点继续推进，优先做核心增量，而不是继续堆很多模块。

### 11.1 补关键检索基线

需要补充：

1. `global-region`：不经过页面召回，直接在所有节点中检索。
2. `oracle-page -> region`：假设页面召回正确，只评价区域定位能力上限。
3. `predicted-page -> region`：当前 Page to Region，评价真实两阶段检索效果。
4. `single-node vs evidence-set`：比较单节点排序和证据集合选择。

这些实验可以回答：

1. 页面级召回是否真的有必要。
2. 区域级检索到底是被页面召回拖累，还是自身排序能力不足。
3. evidence set 是否比单个证据节点更适合回答复杂问题。

### 11.2 实现 evidence set

需要将当前“返回单个节点列表”升级为“选择最小充分证据集合”。

初步可以做：

1. 对数值型问题抽取问题要素，例如指标、年份、单位、数值。
2. 从候选节点中选择覆盖要素最多的一组证据。
3. 输出 evidence set，包括多个 evidence node。
4. 评价 evidence set 是否覆盖答案所需信息。

### 11.3 增加证据充分性判断

当前只是检索，还没有真正判断证据是否足够回答问题。

后续需要实现：

1. 数值型问题的“指标-年份-单位-数值”覆盖检查。
2. 文本型问题的关键词和语义覆盖检查。
3. 不充分时标记 `insufficient`。
4. 证据冲突时标记 `conflict`。

### 11.4 增加可信生成和拒答

后续可以在 evidence set 基础上继续做：

1. 将证据组织成 evidence cards。
2. 调用生成模型基于证据回答。
3. 对答案进行支持性验证。
4. 证据不足时拒答。
5. 生成 `supported`、`partially_supported`、`insufficient`、`citation_mismatch` 等状态。

## 12. 后续实验记录模板

后续每次实验可以按照下面格式追加：

```text
日期：

实验目标：

修改内容：

运行命令：

输出文件：

关键指标：

观察结论：

存在问题：

下一步：
```

