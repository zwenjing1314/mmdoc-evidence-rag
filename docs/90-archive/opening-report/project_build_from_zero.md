# 项目从 0 到 1 构建说明

本文档说明 `mmdoc-evidence-rag` 项目是如何一步一步构建出来的。这里不讲环境安装，只讲项目文件、代码模块、数据流和实验闭环如何完成。

本项目当前目标不是一次性完成完整毕业论文系统，而是先构建一个“开题前可展示的最小实验闭环”：能准备数据、运行检索、计算指标、导出结果表和案例分析。

## 1. 明确第一阶段目标

所以第一阶段代码不追求复杂模型，而是先完成四件事：

1. 建立统一项目结构。
2. 定义统一数据格式。
3. 跑通检索 baseline。
4. 生成可展示的指标表和案例 summary。

因此第一阶段暂时不实现完整 RAG 生成、视觉语言模型检索、可信验证训练，只预留后续扩展位置。

## 2. 创建项目目录结构

项目根目录下先划分几个核心区域：

```text
configs/      存放数据集配置和实验配置
data/         存放 raw / interim / processed / samples 数据
artifacts/    存放开题表格、图表、索引、embedding 等可再生成产物
runs/         存放每次实验运行结果
src/          存放正式 Python 代码
tests/        存放测试
docs/         存放项目说明、数据规范、实验计划
```

这样做的目的是把“原始数据、处理后数据、实验代码、实验结果、论文文档”分开。后续论文写作时，每一类产物都有固定位置，不会混成一堆脚本和临时文件。

## 3. 设计数据目录

数据目录按阶段拆分：

```text
data/raw/          原始下载数据
data/interim/      中间处理结果
data/processed/    标准化后的 parquet 表
data/samples/      小样本数据
```

其中两个主要数据集的原始数据放置位置是：

```text
data/raw/mmdocir/
data/raw/cn_annual_reports/pdfs/
```

中文年报后续会补充两个标注文件：

```text
data/raw/cn_annual_reports/metadata.csv
data/raw/cn_annual_reports/qa_annotations.xlsx
```

这样的设计保证 MMDocIR、中文年报以及以后可能加入的 LongDocURL / MMLongBench-Doc 都能进入同一条处理流程。

## 4. 定义统一中间数据格式

为了避免每个数据集都写一套检索代码，项目先定义统一数据格式。所有数据集最后都转换为四张表：

```text
documents.parquet
pages.parquet
nodes.parquet
queries.parquet
```

四张表分别对应：

- `documents`：文档级信息，比如文档 ID、标题、来源路径、页数。
- `pages`：页面级信息，比如页码、页面文本、OCR 文本、页面图像路径。
- `nodes`：证据节点级信息，比如段落、表格、图表、公式、bbox、文本内容。
- `queries`：问题与标注信息，比如问题、答案、证据页、证据节点、是否可回答。

对应代码在：

```text
src/mmdocrag/schemas.py
```

这里定义了：

```text
DocumentRecord
PageRecord
EvidenceNode
QueryRecord
RetrievalHit
EvidenceCard
```

这些模型用 `pydantic` 校验字段，保证后续数据处理、检索和评价都使用同一套结构。

## 5. 实现 parquet 读写层

数据标准确定后，下一步实现通用读写工具：

```text
src/mmdocrag/io.py
```

这个文件负责：

1. 把 `pydantic` 数据模型写成 parquet。
2. 从 parquet 读回数据模型。
3. 统一写入 processed 数据集。
4. 统一读取 processed 数据集。
5. 写入和读取检索结果 `RetrievalHit`。

项目用 `polars / pyarrow` 处理 parquet。因为 `metadata`、`bbox`、`evidence_page_ids` 这类字段是列表或字典，写 parquet 前会转换成 JSON 字符串，读取时再还原。

## 6. 实现路径与配置工具

项目不能把个人机器路径写死在代码里，所以单独实现路径工具：

```text
src/mmdocrag/paths.py
```

它负责获取：

```text
project_root()
data_root()
runs_root()
artifacts_root()
```

默认情况下，这些路径都指向项目内目录；如果以后需要把大数据放到外部硬盘，可以通过环境变量覆盖。

配置读取放在：

```text
src/mmdocrag/config.py
```

它负责读取 yaml 配置，并展开 `${MMDOC_RAG_DATA_ROOT}` 这类变量。

## 7. 实现数据适配器

数据适配器在：

```text
src/mmdocrag/datasets/adapters.py
```

目前实现了三个入口：

```text
demo
mmdocir
cn_annual_reports
```

### 7.1 demo 数据集

`demo` 是内置小数据集，不依赖真实下载数据。它会生成：

```text
2 个文档
3 个页面
4 个证据节点
3 个问题
```

作用是：即使 MMDocIR 和中文年报还没放进项目，也能跑通完整实验流程。

运行：

```bash
uv run mdr prepare --dataset demo
```

输出：

```text
data/processed/demo/documents.parquet
data/processed/demo/pages.parquet
data/processed/demo/nodes.parquet
data/processed/demo/queries.parquet
```

### 7.2 MMDocIR 适配器

`mmdocir` 适配器当前是第一版探测式实现。它会扫描：

```text
data/raw/mmdocir/
```

尝试读取常见格式：

```text
json
jsonl
csv
parquet
```

如果暂时没有真实数据，它不会崩溃，而是写出提示文件，提醒先运行 demo 流程。

后续真实 MMDocIR 数据放入后，再根据实际字段对适配器做精修。

### 7.3 中文年报适配器

`cn_annual_reports` 适配器会扫描：

```text
data/raw/cn_annual_reports/pdfs/
```

如果有 PDF，就先登记文档信息和占位节点；如果没有 PDF，就生成一个标注模板：

```text
data/raw/cn_annual_reports/qa_annotations_template.csv
```

这个模板用于后续手工标注中文年报问题、答案和证据页。

## 8. 建立 CLI 命令入口

命令行入口在：

```text
src/mmdocrag/cli.py
```

项目在 `pyproject.toml` 中注册了命令：

```text
mdr = "mmdocrag.cli:app"
```

因此后续统一使用：

```bash
uv run mdr ...
```

目前 CLI 有四个命令：

```text
prepare      数据准备
retrieve     运行检索实验
evaluate     评价检索结果
export-demo  导出开题展示表
```

这四个命令构成当前最小实验闭环。

## 9. 编写实验配置

实验配置放在：

```text
configs/experiments/
```

当前有两类配置。

第一类是 demo 配置：

```text
demo_bm25_page.yaml
demo_page_region.yaml
```

用于无真实数据时跑通完整流程。

第二类是正式实验占位配置：

```text
e01_bm25_page.yaml
e02_dense_page.yaml
e03_layout_node.yaml
e04_page_region.yaml
```

这些配置对应开题报告里规划的 baseline：

- BM25 页面检索。
- Dense 页面检索。
- Layout-aware node 检索。
- Page -> Region 两阶段检索。

## 10. 实现检索模块

检索代码放在：

```text
src/mmdocrag/retrieval/
```

其中：

```text
scoring.py    基础打分方法
pipeline.py   根据实验配置运行检索
```

### 10.1 BM25-page

`BM25-page` 把每个页面作为检索对象，问题作为 query，返回最相关页面。

它用于回答：

> 传统文本检索能不能找到正确证据页？

### 10.2 Dense-like page

第一阶段为了保证离线可跑，Dense 检索采用双模式：

1. 如果本地有 `sentence-transformers` 模型，则尝试使用模型向量。
2. 如果模型不可用，则自动回退到 TF-IDF/cosine 检索。

这样不会因为模型没下载而影响开题前展示。

### 10.3 Layout-node

`Layout-node` 把证据节点作为检索对象，例如段落、表格、图表、公式等。

它用于回答：

> 相比页面级检索，细粒度证据节点是否能定位到更具体的证据？

### 10.4 Page -> Region

`Page -> Region` 是当前论文主线的最小实现：

1. 先做页面级粗召回。
2. 在候选页面内检索证据节点。
3. 用 RRF 思路融合页面排名和节点排名。
4. 输出区域级证据命中结果。

它对应论文中的“页面级粗召回 - 区域级细定位”技术路线。

## 11. 实现评价模块

评价代码放在：

```text
src/mmdocrag/evaluation/
```

其中：

```text
metrics.py    指标计算
pipeline.py   读取 run 并生成评价产物
```

目前实现的指标有：

```text
Page Recall@1
Page Recall@5
Page Recall@10
MRR
nDCG@5
nDCG@10
Region Hit@5
```

评价命令会生成：

```text
metrics.json
errors.csv
summary.md
```

其中 `summary.md` 很适合开题时展示，因为里面包含指标和具体问题案例。

## 12. 实现开题展示导出

展示导出代码在：

```text
src/mmdocrag/exporting/demo.py
```

它会读取某次实验的：

```text
run_info.json
metrics.json
```

然后生成开题展示表：

```text
artifacts/figures/opening_experiment_table.md
```

这个文件可以直接复制到开题材料或汇报 PPT 中。

## 13. 跑通第一条完整流程

当前 demo 全流程如下：

```bash
uv run mdr prepare --dataset demo
uv run mdr retrieve --config configs/experiments/demo_page_region.yaml
uv run mdr evaluate --run runs/retrieval/demo_page_region/latest
uv run mdr export-demo --run runs/retrieval/demo_page_region/latest
```

这条流程完成了：

1. 生成标准数据表。
2. 执行 Page -> Region 检索。
3. 计算检索指标。
4. 输出错误分析和案例 summary。
5. 导出开题展示结果表。

运行后主要看两个文件：

```text
runs/retrieval/demo_page_region/latest/summary.md
artifacts/figures/opening_experiment_table.md
```

当前 demo 的 Page -> Region 结果可以展示：

```text
Page Recall@1 = 1.0000
Page Recall@5 = 1.0000
MRR = 1.0000
Region Hit@5 = 1.0000
```

这些数值来自内置 demo 数据，不代表真实实验结果。它的意义是证明代码链路已经跑通。

## 14. 编写测试保证可复现

测试放在：

```text
tests/
```

当前包括：

```text
test_schemas_io.py
test_retrieval_metrics.py
test_demo_smoke.py
```

测试覆盖三类内容：

1. 数据模型和 parquet 读写是否正常。
2. BM25、TF-IDF、RRF 和评价指标是否正常。
3. demo 的 prepare -> retrieve -> evaluate -> export-demo 全链路是否能跑通。

运行：

```bash
uv run pytest
```

当前测试结果：

```text
7 passed
```

同时也通过了：

```bash
uv run ruff check src tests
```

## 15. 当前项目已经完成的实质工作

截至当前版本，项目已经完成：

1. 实验仓库结构搭建。
2. uv 项目依赖入口与 CLI 注册。
3. 标准数据 schema。
4. parquet 数据读写。
5. demo 数据集适配器。
6. MMDocIR 通用探测式适配器。
7. 中文年报 PDF 登记与标注模板生成。
8. BM25 页面检索。
9. TF-IDF fallback 的 Dense-like 检索。
10. Layout-node 检索。
11. Page -> Region 两阶段检索。
12. Page Recall、MRR、nDCG、Region Hit 指标。
13. 实验运行目录、预测结果、指标文件、错误分析、summary 生成。
14. 开题展示表导出。
15. 单元测试和 smoke test。

这些内容可以支撑开题时说明：

> 当前已经完成多模态长文档 RAG 实验平台的最小闭环，实现了从标准数据构建、证据节点建模、检索 baseline、页面-区域协同检索到指标评估与案例导出的初步实验流程。

## 16. 后续接入真实数据的顺序

下一步放入真实数据后，不应该立刻做生成模型，而应按下面顺序推进：

1. 把 MMDocIR 数据放入 `data/raw/mmdocir/`。
2. 运行 `prepare --dataset mmdocir`，观察生成的四张 parquet。
3. 根据真实字段修正 MMDocIR 适配器。
4. 跑 `e01_bm25_page.yaml` 得到第一张真实结果表。
5. 跑 `e03_layout_node.yaml` 和 `e04_page_region.yaml`，比较区域级定位效果。
6. 把 20 份中文年报放入 `data/raw/cn_annual_reports/pdfs/`。
7. 填写中文年报 QA 标注模板。
8. 跑中文年报小规模应用验证。

完成这些后，就可以把开题报告里的“拟开展实验”改成“已完成初步实验并获得阶段性结果”。

