# mmdoc-evidence-rag

面向视觉文档证据检索的实验仓库。当前小论文主线是：先验证 ColPali 的页面级基线与页面内证据区域缺口，再决定是否训练布局约束 Patch 融合模块。

## 从这里开始

1. 阅读 [docs/00-index.md](docs/00-index.md)，了解唯一入口和当前阶段。
2. 按 [docs/01-quickstart.md](docs/01-quickstart.md) 配置 Windows 环境与数据目录。
3. 只通过 [docs/02-commands.md](docs/02-commands.md) 或 `./tasks.ps1` 运行实验。
4. 实验结果登记在 [experiments/registry.csv](experiments/registry.csv)，详情放在 `experiments/`。

当前 Gate：ColPali full baseline（Phase 1A）完成并核验为 1,658 queries 后，才能进入 Phase 1B 区域缺口诊断。

## Project Skill

本项目附带一个面向 Codex/大模型的研究 skill：

```text
skills/mmdoc-evidence-research/
```

它不是一个检索模型，也不会自动提升指标。它是一组项目专用的上下文规则，用来帮助大模型在分析代码、设计实验、修改模块和撰写论文内容时保持研究边界一致，特别是区分：

- 已经写入源码的功能；
- 文档中记录过但当前未必可复现的实验结果；
- 仍然只是计划的可信生成、视觉检索和拒答功能。

skill 的核心约束是围绕以下主线工作：

```text
文档解析 -> 证据节点 -> 页面检索 -> 区域定位 -> 证据集 -> 生成 -> 验证/拒答
```

### 使用方式

skill 不需要启动服务，也没有单独的运行命令。Codex 会读取它的 YAML 头信息和 Markdown 指令，在任务匹配时加载它。`PyYAML` 只用于运行 skill 校验脚本，不参与 skill 的日常使用；本项目的 `pyproject.toml` 已经包含 `pyyaml` 依赖。

在支持 Codex skill 的环境中，可以显式调用：

```text
$mmdoc-evidence-research 请分析当前 evidence set 实验的下一步
```

也可以直接提出与本项目相关的任务，让模型根据 skill 的描述自动判断是否使用。项目内的 `skills/` 版本适合提交到 Git，但是否会被当前 Codex 自动发现取决于宿主环境；最稳妥的做法是将该目录复制或链接到个人 skill 目录：

```text
~/.codex/skills/mmdoc-evidence-research
```

安装或更新后，通常新开一个 Codex 任务（或重新加载 skill 列表）即可；不需要运行 Python 程序。显式调用时，`$mmdoc-evidence-research` 是 skill 名称，不是 shell 变量。

主规则见 [skills/mmdoc-evidence-research/SKILL.md](skills/mmdoc-evidence-research/SKILL.md)，详细研究边界和实验规范见其 `references/` 目录。

## Quick Demo

真实数据放入前，可以先跑内置 demo，确认完整实验闭环：

```bash
./tasks.ps1 demo
```

输出位置：

```text
runs/retrieval/demo_page_region/latest/summary.md
artifacts/figures/opening_experiment_table.md
```

如果要跑页面级 BM25 baseline：

```bash
./tasks.ps1 demo-bm25
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

IDE 中选择项目环境的 Python：Windows 通常为 `.venv\Scripts\python.exe`；如果使用已验证的 Conda GPU 环境，则选择 `C:\Users\WenJing\anaconda3\envs\colpali\python.exe`。

详细步骤见 [docs/01-quickstart.md](docs/01-quickstart.md)。旧环境说明已移入 `docs/90-archive/`，不再作为入口。

## Data Placement

MMDocIR 原始数据建议放在项目外，并通过 `MMDOCIR_EVALUATION_ROOT` 指向数据集目录；未设置变量时，程序才会 fallback 到 `data/raw/mmdocir_evaluation/`。中文年报原始数据放到：

```text
data/raw/mmdocir_evaluation/
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
