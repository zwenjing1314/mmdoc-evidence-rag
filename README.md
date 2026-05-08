# mmdoc-evidence-rag

面向多模态长文档的多粒度证据检索与可信生成实验仓库。

当前阶段目标：先完成开题前可展示的最小实验闭环，而不是一次性铺满全部论文实验。

## Immediate Goal

开题前优先完成：

1. 统一整理 MMDocIR 与中文年报数据目录。
2. 将数据转换为统一中间格式：`documents / pages / nodes / queries`。
3. 跑通检索预实验：`BM25-page`、`Dense-page`、`Layout-aware node`、`Page -> Region`。
4. 产出第一张检索结果表与若干成功/失败案例。

## Quick Demo

真实数据放入前，可以先跑内置 demo，确认完整实验闭环：

```bash
uv run mdr prepare --dataset demo
uv run mdr retrieve --config configs/experiments/demo_page_region.yaml
uv run mdr evaluate --run runs/retrieval/demo_page_region/latest
uv run mdr export-demo --run runs/retrieval/demo_page_region/latest
```

输出位置：

```text
runs/retrieval/demo_page_region/latest/summary.md
artifacts/figures/opening_experiment_table.md
```

如果要跑页面级 BM25 baseline：

```bash
uv run mdr retrieve --config configs/experiments/demo_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/demo_bm25_page/latest
```

## Repository Layout

```text
configs/      实验、数据集、解析器、检索器、生成器配置
data/         原始数据、中间数据、处理后标准数据、小样本数据
artifacts/    索引、embedding、解析产物、论文图表等可再生成产物
runs/         每次实验运行结果、指标、日志、预测文件
notebooks/    数据观察和临时分析，不放主流程代码
scripts/      后续命令入口脚本
src/          后续正式 Python 包代码
tests/        后续单元测试和 smoke test
docs/         数据规范、实验设计、论文记录
```

## Environment

主环境方案使用 `uv`：

```bash
uv python install 3.11
uv sync --dev
```

PyCharm 中选择：

```text
.venv/bin/python
```

详细步骤见：

[docs/environment/environment_setup.md](docs/environment/environment_setup.md)

## Data Placement

请把下载好的数据放到：

```text
data/raw/mmdocir/
data/raw/cn_annual_reports/pdfs/
```

中文年报元数据和问题标注后续建议放在：

```text
data/raw/cn_annual_reports/metadata.csv
data/raw/cn_annual_reports/qa_annotations.xlsx
```

## Standard Processed Format

所有数据集最终都转换为：

```text
data/processed/{dataset}/documents.parquet
data/processed/{dataset}/pages.parquet
data/processed/{dataset}/nodes.parquet
data/processed/{dataset}/queries.parquet
```

这样 MMDocIR、中文年报、后续 LongDocURL/MMLongBench-Doc 都能复用同一套检索、生成和评估流程。
