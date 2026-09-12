# 命令手册（SSOT）

> Status: stable | Scope: 全仓命令 | SSOT: 是
> 本篇是命令唯一真理源。其他文档只允许引用，不许重复写长命令。

约定：所有命令在项目根目录执行；Windows 优先用 `./tasks.ps1`，它已内置 `UV_CACHE_DIR=.uv-cache` 与 ColPali 所需 `HF_HOME=artifacts/hf_cache`。

每条格式固定为：命令 / 输入 / 输出 / 检查。

## demo

```powershell
./tasks.ps1 demo
./tasks.ps1 demo-bm25
```

- 输入：无（内置生成）/ `configs/experiments/demo_*.yaml`
- 输出：`runs/retrieval/demo_page_region/<timestamp>/{predictions.parquet,config.json,run_info.json}` + `evaluate` 后 `metrics.json/summary.md`
- 检查：`summary.md` 存在；`metrics.json` 非空

## 中文年报

```powershell
./tasks.ps1 cn-bm25-test   # test，冻结，不调参
./tasks.ps1 cn-bm25-dev    # dev，调参用
```

- 输入：`configs/experiments/cn_bm25_page.yaml` + `data/processed/cn_annual_reports` + `configs/splits/cn_annual_reports_company_v1.yaml`
- 输出：`runs/retrieval/cn_bm25_page/{test,dev}/<timestamp>/{predictions.parquet,config.json,run_info.json,metrics.json}`
- 检查：`run_info.json` 中 `data_split.name=test|dev`、`query_count=32`、`test_status=frozen`

底层等价（不用手写，备查）：

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/test/latest
```

Dense/Hybrid 需本地 `BAAI/bge-small-zh-v1.5`，离线优先；允许下载时才加 `MDR_ALLOW_MODEL_DOWNLOAD=1`。

## MMDocIR smoke（EXP-001）

```powershell
./tasks.ps1 mmdocir-smoke
```

- 输入：`configs/experiments/mmdocir_colpali_smoke.yaml`（`top_k=5` 小样本）+ `data/processed/mmdocir_evaluation`
- 输出：`runs/retrieval/mmdocir_colpali_smoke/<timestamp>/{predictions.parquet,config.json,run_info.json,metrics.json,errors.csv,summary.md}`
- 检查：`page_image_path` 存在；CPU 下 ColPali 被拒绝并报错（符合 `colpali.py` 设计）；`hits=30` 小样本，不可当正式 baseline
- 登记：`experiments/registry.csv` 中 EXP-001；详情 `experiments/2026-09-12-exp-001-colpali-smoke.md`

## MMDocIR full（Phase 1A 全量 baseline，待跑）

```powershell
./tasks.ps1 mmdocir-full
./tasks.ps1 mmdocir-bm25
./tasks.ps1 evaluate-mmdocir -RunId "runs/retrieval/mmdocir_colpali/<timestamp>"
```

- 输入（full）：`configs/experiments/mmdocir_colpali.yaml`（`top_k=20`）+ `data/processed/mmdocir_evaluation`
- 输出：`runs/retrieval/mmdocir_colpali/<timestamp>/`；BM25 对照 `runs/retrieval/mmdocir_bm25_page/<timestamp>/`
- 检查：full 跑完才登记 Phase 1A baseline；smoke 只算流程验证
- 注意：RTX 3080 Ti 12GB 用保守 batch（`image_batch_size=1, query_batch_size=2, score_batch_size=4`，见 full config 注释），embedding 缓存走 `artifacts/colpali/`

## 质量门

```powershell
./tasks.ps1 check
```

- 输入：`src/` + `tests/`
- 输出：终端 ruff + pytest 结果
- 检查：三条全绿才允许合入 `main`

## CLI 全量（备查）

`prepare` / `build-cn-annotations` / `retrieve [--split train|dev|test]` / `evaluate` / `verify-evidence [--top-k]` / `export-demo`，以 `uv run mdr --help` 为准。`build-evidence-sets/generate/verify` 尚未注册，不可运行。
