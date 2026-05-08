# Environment Setup

本文档用于配置本项目的 Python 实验环境。当前主方案改为：

> **PyCharm + uv + `pyproject.toml` + `uv.lock`**

Conda/Anaconda3 作为第二方案保留，主要用于你在某台机器上遇到 CUDA、系统库或 PyCharm 解释器兼容问题时兜底。

## 1. 为什么主方案改用 uv

`uv` 是 Astral 推出的现代 Python 包和项目管理工具，能统一处理：

- Python 版本；
- 虚拟环境；
- 项目依赖；
- lockfile；
- pip 风格安装；
- 命令运行。

相比单独维护 `requirements.txt`，`uv + pyproject.toml + uv.lock` 更适合本项目这种需要长期复现实验的论文工程。后续你在 Mac 上开发、Ubuntu 3080Ti 上跑实验，两边都可以使用同一份 `pyproject.toml` 和 `uv.lock` 尽量保持依赖一致。

## 2. 当前环境文件分工

```text
pyproject.toml       主依赖入口，日常开发优先使用
.python-version      固定 Python 主版本
uv.lock              uv 生成的锁定文件，首次 uv sync 后出现
environment.yml      Conda 第二方案，不作为主入口
```

不再维护 `requirements.in` 或普通 `requirements.txt` 作为主方案，避免依赖来源混乱。

## 3. 安装 uv

如果本机还没有 `uv`，先安装。

macOS / Linux：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装后重新打开终端，检查：

```bash
uv --version
```

也可以用 pipx 安装：

```bash
pipx install uv
```

## 4. 使用 uv 创建环境

进入项目根目录：

```bash
cd /Users/zhouwenjing/Documents/WorkTransfer/mmdoc-evidence-rag
```

安装 Python 3.11：

```bash
uv python install 3.11
```

创建并同步环境：

```bash
uv sync --dev
```

`uv sync --dev` 会：

1. 根据 `.python-version` 和 `pyproject.toml` 创建 `.venv`；
2. 安装项目依赖和开发依赖；
3. 生成或更新 `uv.lock`；
4. 保证当前环境与锁定文件一致。

以后新增或删除依赖后，也运行：

```bash
uv sync --dev
```

## 5. 在 PyCharm 中配置 uv 环境

1. 打开 PyCharm。
2. 打开项目目录：

```text
/Users/zhouwenjing/Documents/WorkTransfer/mmdoc-evidence-rag
```

3. 先在终端运行：

```bash
uv sync --dev
```

4. 在 PyCharm 中进入 `Settings/Preferences -> Project -> Python Interpreter`。
5. 选择 `Add Interpreter -> Add Local Interpreter -> Existing`。
6. 选择项目下的解释器：

```text
/Users/zhouwenjing/Documents/WorkTransfer/mmdoc-evidence-rag/.venv/bin/python
```

这样 PyCharm 使用的就是 uv 创建的项目虚拟环境。

## 6. 常用 uv 命令

运行 Python：

```bash
uv run python --version
```

安装新依赖：

```bash
uv add package-name
```

安装开发依赖：

```bash
uv add --dev package-name
```

删除依赖：

```bash
uv remove package-name
```

同步环境：

```bash
uv sync --dev
```

运行格式检查：

```bash
uv run ruff check src tests
```

格式化：

```bash
uv run ruff format src tests
```

运行测试：

```bash
uv run pytest
```

## 7. PyTorch 安装策略

当前 `pyproject.toml` 暂时不直接写死 `torch`，因为你的 Mac M1 Pro 和 Ubuntu 3080Ti 安装方式不同。

### Mac M1 Pro

Mac 用于代码开发、小样本 smoke test 和写论文，一般可直接安装：

```bash
uv pip install torch torchvision torchaudio
```

### Ubuntu + 3080Ti

Ubuntu 3080Ti 是主实验机器。请到 PyTorch 官方安装页面选择：

```text
OS: Linux
Package: Pip
Language: Python
Compute Platform: CUDA
```

复制官方给出的命令。命令形式通常类似：

```bash
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cuXXX
```

其中 `cuXXX` 以 PyTorch 官方页面当前推荐为准，不要手写猜版本。

安装后验证：

```bash
uv run python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

如果 Ubuntu 机器输出 `True`，说明 CUDA 版 PyTorch 可用。

## 8. 验证环境

同步完成后运行：

```bash
uv run python -c "import pandas, pyarrow, sklearn, fitz, sentence_transformers; print('env ok')"
```

检查开发工具：

```bash
uv run ruff --version
uv run pytest --version
```

## 9. 第二方案：Conda / Anaconda3

如果某台机器上 uv 环境遇到兼容问题，可以使用 Conda 兜底。

创建环境：

```bash
conda env create -f environment.yml
conda activate mmdoc-rag
```

更新环境：

```bash
conda env update -f environment.yml --prune
```

在 PyCharm 中选择 Conda 环境解释器即可。

注意：Conda 现在只是第二方案。日常开发、依赖新增、依赖锁定，优先使用 uv。

## 10. 后续锁定与论文复现

uv 会自动维护：

```text
uv.lock
```

论文实验稳定后，需要把下面文件一起保留：

```text
pyproject.toml
uv.lock
.python-version
```

如果使用 Conda 第二方案，再额外保留：

```text
environment.yml
```

## 11. 参考文档

- uv official docs: https://docs.astral.sh/uv/
- uv project guide: https://docs.astral.sh/uv/guides/projects/
- PyTorch install selector: https://pytorch.org/get-started/locally/
- PyCharm virtual environment docs: https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html
- Conda managing environments: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html
