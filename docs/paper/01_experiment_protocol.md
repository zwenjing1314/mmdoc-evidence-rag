# 小论文实验协议

本文件定义小论文的正式数据划分和运行规范。所有正式结果使用：

```text
data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv
SHA-256: 553b76d1428ad430e43056e9ca2380f15fce5bb6ca69ce58e995342a805d1d95
```

`qa_annotations_v2.csv` 保留为历史来源和备份。由于 reviewed 文件存在，程序不会同时合并两份标注，而是只读取 reviewed 文件。

## 1. 固定划分

分割清单：`configs/splits/cn_annual_reports_company_v1.yaml`。

| Split | 公司数 | 问题数 | 用途 |
| --- | ---: | ---: | --- |
| train | 12 | 96 | 方法开发、问题分析和候选规则设计 |
| dev | 4 | 32 | 选择权重、Top-K、阈值和方法版本 |
| test | 4 | 32 | 冻结后的最终报告与论文主表 |

`test_status: frozen` 表示测试公司清单和 QA 文件版本不得修改。程序会在每次实验前检查 reviewed QA 的 SHA-256；不一致时会停止运行。

## 2. 运行命令

中文实验配置默认使用 `test`。例如正式 BM25 baseline：

```bash
UV_CACHE_DIR=.uv-cache uv run mdr retrieve \
  --config configs/experiments/cn_bm25_page.yaml
UV_CACHE_DIR=.uv-cache uv run mdr evaluate \
  --run runs/retrieval/cn_bm25_page/test/latest
```

成功时，第一条命令输出：

```text
Retrieval run written to: .../runs/retrieval/cn_bm25_page/test/<timestamp>
```

`run_info.json` 必须包含：

```text
data_split.name = test
data_split.document_count = 4
data_split.query_count = 32
data_split.test_status = frozen
```

在开发集调参时，明确覆盖 split，输出会写到独立的 `dev/` 目录，不会覆盖 test 结果：

```bash
HF_HOME=artifacts/hf_cache UV_CACHE_DIR=.uv-cache \
uv run mdr retrieve --config configs/experiments/cn_evidence_set_region.yaml --split dev
UV_CACHE_DIR=.uv-cache \
uv run mdr evaluate --run runs/retrieval/cn_evidence_set_region/dev/latest
```

Dense 相关实验必须保留 `HF_HOME=artifacts/hf_cache`。在 `run_info.json` 中检查实际后端；纯 Dense 应为：

```text
dense:sentence_transformers:BAAI/bge-small-zh-v1.5:maxlen=128
```

## 2.1 MMDocIR 公开集外部验证

官方评测数据保留在项目外部目录，不复制也不移动：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset
```

首次处理和页面级 BM25 基线：

```bash
MMDOCIR_EVALUATION_ROOT=/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset \
UV_CACHE_DIR=.uv-cache uv run mdr prepare --dataset mmdocir_evaluation

UV_CACHE_DIR=.uv-cache uv run mdr retrieve \
  --config configs/experiments/mmdocir_bm25_page.yaml
UV_CACHE_DIR=.uv-cache uv run mdr evaluate \
  --run runs/retrieval/mmdocir_bm25_page/latest
```

处理后的标准数据规模为 313 篇文档、20,395 页、170,338 个布局节点和 1,658 个问题。页面级金标覆盖全部问题；布局节点可精确映射的问题为 1,598/1,658，因此页面和布局指标必须分开报告。

Dense 与 Hybrid 页面检索使用多语种模型 `BAAI/bge-m3`。模型下载成功后运行：

```bash
HF_HOME=artifacts/hf_cache UV_CACHE_DIR=.uv-cache \
uv run mdr retrieve --config configs/experiments/mmdocir_dense_page_bge_m3.yaml
HF_HOME=artifacts/hf_cache UV_CACHE_DIR=.uv-cache \
uv run mdr evaluate --run runs/retrieval/mmdocir_dense_page_bge_m3/latest

HF_HOME=artifacts/hf_cache UV_CACHE_DIR=.uv-cache \
uv run mdr retrieve --config configs/experiments/mmdocir_hybrid_page_bge_m3.yaml
HF_HOME=artifacts/hf_cache UV_CACHE_DIR=.uv-cache \
uv run mdr evaluate --run runs/retrieval/mmdocir_hybrid_page_bge_m3/latest
```

当前已完成的 BM25 页面级结果：`Page Recall@1=0.4903`、`@5=0.7521`、`@10=0.8456`、`MRR=0.6084`、`nDCG@5=0.6060`。

## 3. 规则

1. 在 `train` 和 `dev` 完成全部规则、权重、Top-K 与方法选择后，记录 Git commit 并冻结配置。
2. `test` 只运行最终确定的方法和 baseline；若根据 test 结果改代码或调参数，必须创建新版本并重新开始 dev 流程。
3. 每次正式运行都保留 `config.json`、`run_info.json`、`metrics.json` 和预测文件。程序还会把本次的 split 清单复制到运行目录。
4. `runs/` 和原始数据不提交 Git；提交 split 清单、配置、代码、测试、命令和汇总结果。
