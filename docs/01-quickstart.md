# 快速开始（Windows 现行）

> Status: stable | Scope: 入门 | SSOT: 是

## 1. 环境

```powershell
cd "c:\Users\WenJing\Documents\WorkTransfer\mmdoc-evidence-rag"
uv sync --dev
uv run mdr --help
uv run pytest
```

ColPali 另需 GPU 依赖（CPU 会被主动拒绝）：

```powershell
uv sync --extra colpali
```

详细版本以 `pyproject.toml` + `uv.lock` 为准。

## 2. Demo 最小闭环（无真实数据）

```powershell
./tasks.ps1 demo
```

等价于：

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run mdr prepare --dataset demo
uv run mdr retrieve --config configs/experiments/demo_page_region.yaml
uv run mdr evaluate --run runs/retrieval/demo_page_region/latest
uv run mdr export-demo --run runs/retrieval/demo_page_region/latest
```

产物：`runs/retrieval/demo_page_region/latest/{predictions.parquet,metrics.json,summary.md}`。

## 3. 中文年报 smoke

```powershell
./tasks.ps1 cn-bm25-test
```

前置：`data/processed/cn_annual_reports/*.parquet` 存在；`configs/splits/cn_annual_reports_company_v1.yaml` 为冻结划分（train 12/96、dev 4/32、test 4/32）。

## 4. MMDocIR smoke（EXP-001）

```powershell
./tasks.ps1 mmdocir-smoke
```

前置（三缺一即停）：

1. 原始数据在项目外：`MMDOCIR_EVALUATION_ROOT` 指向 `MMDocIR_Evaluation_Dataset`；
2. `uv run mdr prepare --dataset mmdocir_evaluation` 已生成 `data/processed/mmdocir_evaluation/`；
3. `pages.parquet` 中 `page_image_path` 存在（`src/mmdocrag/retrieval/colpali.py` 会校验）。

注意 Windows 下 `latest` 可能是软链接或 `latest.txt`，`evaluate --run .../latest` 两种都支持。

## 5. 质量门

```powershell
./tasks.ps1 check
```

等价 `ruff check` + `ruff format --check` + `pytest`。
