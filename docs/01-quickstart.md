# 快速开始（Windows 现行，SSOT）

> Status: stable | Scope: 环境 + 数据准备入口 | SSOT: 是
> 环境细节只写在这里。`02-commands.md` 只写命令，不重复环境。

## 1. 主方案：uv（日常开发唯一入口）

```powershell
cd "c:\Users\WenJing\Documents\WorkTransfer\mmdoc-evidence-rag"
uv sync --dev
uv run mdr --help
uv run pytest
```

版本以 `pyproject.toml` + `uv.lock` + `.python-version` 为准（Python `>=3.11,<3.13`）。

ColPali 另需 GPU 依赖（CPU 会被 `src/mmdocrag/retrieval/colpali.py` 主动拒绝）：

```powershell
uv sync --extra colpali
```

## 2. 第二方案：Conda（仅兜底）

Conda 是第二方案，仅在某台机器遇到 CUDA、系统库或解释器兼容问题时用。日常加依赖、锁版本仍用 uv。

```powershell
conda env create -f environment.yml
conda activate mmdoc-rag
conda env update -f environment.yml --prune
```

对应关系：`environment.yml`（conda）与 `pyproject.toml`（uv）保持同源，论文复现以 `pyproject.toml + uv.lock + .python-version` 为准。

`tasks.ps1` 打印的 `Environment` 行会同时显示 uv 环境与当前 `CONDA_DEFAULT_ENV`（如有），便于反查本次实验到底在哪个解释器下跑的。

## 3. PyTorch / CUDA 策略（不写死版本）

`pyproject.toml` 不写死 `torch`，按机器装：

- 本机 Windows：按 [PyTorch 官网](https://pytorch.org/get-started/locally/)选 CUDA 版本装；
- 验证：`uv run python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"`。

## 4. MMDocIR 数据位置和准备（SSOT）

原始数据在项目外，不复制不移动，通过环境变量指向：

```powershell
$env:MMDOCIR_EVALUATION_ROOT = "D:\MMDocIR_Evaluation_Dataset"  # 按本机实际路径改
```

标准产物在项目内（均被 `.gitignore` 忽略，不进 git）：

```text
data/raw/mmdocir_evaluation/        # 原始（或外指）
data/processed/mmdocir_evaluation/  # documents/pages/nodes/queries.parquet
data/interim/mmdocir_evaluation/page_images/  # 页面图，colpali 必需
```

准备方法（详情见 `docs/02-commands.md`，这里只讲输入输出）：

```text
输入：MMDOCIR_Evaluation_Dataset 下 MMDocIR_annotations.jsonl + MMDocIR_pages.parquet + MMDocIR_layouts.parquet
输出：data/processed/mmdocir_evaluation/*.parquet（313 文档、20395 页、170338 节点、1658 问题）
检查：pages.parquet 中 page_image_path 存在，否则 colpali 直接报错停掉
```

## 5. 中文年报数据（SSOT 引用）

划分与 QA 版本以 `docs/10-small-paper/protocol.md` 为准（train 12/96、dev 4/32、test 4/32）。准备命令见 `docs/02-commands.md`。
