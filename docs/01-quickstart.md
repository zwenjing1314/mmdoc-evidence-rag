# 快速开始（Windows 现行，SSOT）

> Status: stable | Scope: 环境 + 数据准备入口 | SSOT: 是
> 环境细节只写在这里。`02-commands.md` 只写命令，不重复环境。

## 1. 唯一环境：uv

```powershell
cd "c:\Users\WenJing\Documents\WorkTransfer\mmdoc-evidence-rag"
uv sync --dev
uv run --extra colpali mdr --help
uv run --extra colpali pytest
```

版本以 `pyproject.toml` + `uv.lock` + `.python-version` 为准（Python `>=3.11,<3.13`）。

ColPali 也使用同一个 uv 项目环境。Windows GPU 依赖由 `pyproject.toml` 中的 PyTorch `cu130` 源锁定；不要激活或使用 Conda/`.venv-colpali` 运行项目：

```powershell
Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
Remove-Item Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue
uv sync --dev --extra colpali
uv run --extra colpali python -c "import torch, colpali_engine; print(torch.__version__); print(torch.cuda.is_available())"
```

## 2. 环境职责

项目正式环境只有 uv 创建的 `.venv`。旧的 Conda `colpali` 和 `.venv-colpali` 仅作为迁移期备份，暂不删除，且不得用于正式实验。论文复现以 `pyproject.toml + uv.lock + .python-version` 为准。

运行 `./tasks.ps1 mmdocir-smoke` 或 `./tasks.ps1 mmdocir-full` 前确保没有激活其他虚拟环境。脚本会检查 uv 环境的 `torch.cuda.is_available()`。

## 3. PyTorch / CUDA 策略

Windows ColPali extra 固定使用 `torch==2.13.0`、`torchvision==0.28.0` 的 `cu130` wheels；普通 `uv sync --dev` 不安装 ColPali extra，但项目中的基础深度学习依赖仍会复用同一 CUDA torch 版本。

- 验证：`uv run --extra colpali python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"`。
- 若下载出现 SSL EOF，先执行 `$env:UV_SYSTEM_CERTS = "true"`；`tasks.ps1` 会自动设置该变量。

## 4. MMDocIR 数据位置和准备（SSOT）

原始数据在项目外，不复制不移动，通过环境变量指向：

```powershell
$env:MMDOCIR_EVALUATION_ROOT = "D:\MMDocIR_Evaluation_Dataset"  # 按本机实际路径改
```

标准产物在项目内（均被 `.gitignore` 忽略，不进 git）：

```text
data/raw/mmdocir_evaluation/        # 未设置 MMDOCIR_EVALUATION_ROOT 时的 fallback
data/processed/mmdocir_evaluation/        # full: documents/pages/nodes/queries.parquet
data/processed/mmdocir_evaluation_smoke/  # smoke: separate 1-document copy
data/interim/mmdocir_evaluation/page_images/  # 页面图，colpali 必需
```

准备方法（详情见 `docs/02-commands.md`，这里只讲输入输出）：

```text
输入：MMDOCIR_Evaluation_Dataset 下 MMDocIR_annotations.jsonl + MMDocIR_pages.parquet + MMDocIR_layouts.parquet
输出：data/processed/mmdocir_evaluation/*.parquet（313 文档、20395 页、170338 节点、1658 问题）
检查：pages.parquet 中 page_image_path 存在，否则 colpali 直接报错停掉

```

Smoke 必须写入独立目录，不能用 `--limit-docs` 覆盖 full 目录：

```powershell
uv run --extra colpali mdr prepare --dataset mmdocir_evaluation --limit-docs 1 --output-dataset mmdocir_evaluation_smoke
```

## 5. 中文年报数据（SSOT 引用）

划分与 QA 版本以 `docs/10-small-paper/protocol.md` 为准（train 12/96、dev 4/32、test 4/32）。准备命令见 `docs/02-commands.md`。
