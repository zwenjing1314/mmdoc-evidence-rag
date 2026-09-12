# 项目完整运行命令

本文档只记录当前代码已经支持的命令。文档中提到的 `build-evidence-sets`、`generate`、`verify` 等尚未注册到 CLI 的命令属于后续计划，不应直接运行。

## 1. 基本约定

所有命令默认在项目根目录执行：

```bash
cd /Users/zhouwenjing/Documents/WorkTransfer/PythonProject/mmdoc-evidence-rag
```

推荐使用 `uv run`，它会在项目环境中运行命令：

```bash
uv sync --dev
uv run mdr --help
```

如果系统找不到 `uv`，先确认安装位置：

```bash
command -v uv
```

也可以使用本机的完整路径。下面只是示例，实际路径以 `command -v uv` 的输出为准：

```bash
/Users/zhouwenjing/.local/bin/uv sync --dev
/Users/zhouwenjing/.local/bin/uv run mdr --help
```

项目依赖包括 `pyyaml`。它用于读取 YAML 配置，不需要单独启动任何服务。

## 2. 数据目录和环境变量

默认数据根目录是项目下的 `data/`：

```text
data/raw/       原始数据
data/interim/   中间数据
data/processed/标准 parquet 数据
```

如需将大数据放在项目外，可以设置：

```bash
export MMDOC_RAG_DATA_ROOT=/path/to/mmdoc-data
```

代码读取的标准数据文件为：

```text
${MMDOC_RAG_DATA_ROOT}/processed/{dataset}/documents.parquet
${MMDOC_RAG_DATA_ROOT}/processed/{dataset}/pages.parquet
${MMDOC_RAG_DATA_ROOT}/processed/{dataset}/nodes.parquet
${MMDOC_RAG_DATA_ROOT}/processed/{dataset}/queries.parquet
```

运行结果默认写入：

```text
runs/retrieval/{experiment_name}/
```

论文图表和导出文件默认写入：

```text
artifacts/
```

## 3. 查看 CLI 命令

当前正式支持的子命令只有：

```bash
uv run mdr --help
uv run mdr prepare --help
uv run mdr build-cn-annotations --help
uv run mdr retrieve --help
uv run mdr evaluate --help
uv run mdr verify-evidence --help
uv run mdr export-demo --help
```

它们对应的流程是：

```text
prepare -> retrieve -> evaluate -> verify-evidence/export-demo
```

## 4. Demo 最小闭环

Demo 不需要下载真实 PDF，适合第一次检查环境和代码流程。

### 4.1 准备 demo 数据

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

### 4.2 运行 Demo Page -> Region

```bash
uv run mdr retrieve --config configs/experiments/demo_page_region.yaml
uv run mdr evaluate --run runs/retrieval/demo_page_region/latest
```

### 4.3 运行 Demo BM25-page

```bash
uv run mdr retrieve --config configs/experiments/demo_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/demo_bm25_page/latest
```

### 4.4 导出 Demo 展示表

必须先运行 `evaluate`，因为导出命令会读取 `metrics.json`：

```bash
uv run mdr export-demo --run runs/retrieval/demo_page_region/latest
```

典型输出：

```text
runs/retrieval/demo_page_region/latest/summary.md
artifacts/figures/opening_experiment_table.md
```

## 5. 中文年报数据准备

### 5.1 放置真实 PDF

将 PDF 放到：

```text
data/raw/cn_annual_reports/pdfs/
```

可选的人工标注文件放到：

```text
data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv
```

程序会优先读取人工修订版本；没有该文件时再按适配器中的回退规则读取其他标注文件。

### 5.2 生成 V2 QA 标注

如果还没有中文年报 QA 标注，可以根据本地 PDF 生成：

```bash
uv run mdr build-cn-annotations --questions-per-doc 8 --limit-docs 20
```

省略 `--limit-docs` 可处理目录中的全部 PDF：

```bash
uv run mdr build-cn-annotations --questions-per-doc 8
```

主要输出：

```text
data/raw/cn_annual_reports/qa_annotations_v2.csv
data/raw/cn_annual_reports/qa_annotations_v2_generation_log.md
```

生成后的标注仍应人工抽查，不能把规则生成结果直接等同于高质量金标准。

### 5.3 解析中文年报并生成标准数据

快速实验只处理 20 份：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

处理全部 PDF：

```bash
uv run mdr prepare --dataset cn_annual_reports
```

主要输出：

```text
data/processed/cn_annual_reports/documents.parquet
data/processed/cn_annual_reports/pages.parquet
data/processed/cn_annual_reports/nodes.parquet
data/processed/cn_annual_reports/queries.parquet
```

## 6. 中文年报检索实验

中文年报配置默认使用：

```yaml
search_scope: document
```

也就是每个问题只在所属年报内部检索，而不是在所有公司年报中混合检索。

### 6.1 BM25-page

不需要 embedding 模型：

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest
```

### 6.2 Dense-page

配置文件要求本地可用的 SentenceTransformer 模型，默认是 `BAAI/bge-small-zh-v1.5`：

```bash
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest
```

当前实现默认离线查找本地模型。如果模型没有缓存，命令会失败，而不是自动联网下载。允许下载时可以显式设置：

```bash
MDR_ALLOW_MODEL_DOWNLOAD=1 uv run mdr retrieve \
  --config configs/experiments/cn_dense_page.yaml
```

### 6.3 Hybrid-page

融合 BM25 和 Dense 页面候选：

```bash
uv run mdr retrieve --config configs/experiments/cn_hybrid_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_hybrid_page/latest
```

该配置同样需要 `BAAI/bge-small-zh-v1.5`。

### 6.4 Page -> Region

先召回页面，再在候选页面内检索 paragraph、table_block、table_row：

```bash
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

### 6.5 Hybrid Page -> Region

页面阶段使用 BM25 + Dense 融合，再进行区域检索：

```bash
uv run mdr retrieve --config configs/experiments/cn_hybrid_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_hybrid_page_region/latest
```

### 6.6 Global Region

跳过页面召回，直接在所属文档的所有节点中检索：

```bash
uv run mdr retrieve --config configs/experiments/cn_global_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_global_region/latest
```

它是对照实验，不代表页面—区域层次化方法。

### 6.7 Oracle Page -> Region

使用 gold evidence pages 作为候选页面，只用于分析区域检索上限：

```bash
uv run mdr retrieve --config configs/experiments/cn_oracle_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_oracle_page_region/latest
```

论文中必须将它标记为 oracle/upper bound，不能和普通可部署方法直接并列宣称。

### 6.8 Evidence Set Region

当前最接近论文核心方法的实验。它合并页面候选、全局节点候选、结构化数值扫描和首页锚点，再按问题槽位覆盖选择证据集：

```bash
uv run mdr retrieve --config configs/experiments/cn_evidence_set_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_evidence_set_region/latest
```

检查 Top-5 证据是否充分：

```bash
uv run mdr verify-evidence \
  --run runs/retrieval/cn_evidence_set_region/latest \
  --top-k 5
```

`--top-k` 不等于证据集节点数；证据集内部节点数由配置中的 `max_evidence_nodes` 和 `output_top_k` 控制。

### 6.9 一次运行全部中文年报检索配置

下面命令会依次执行所有主要实验。Dense 相关配置要求本地 embedding 模型：

```bash
for config in \
  cn_bm25_page \
  cn_dense_page \
  cn_hybrid_page \
  cn_page_region \
  cn_hybrid_page_region \
  cn_global_region \
  cn_oracle_page_region \
  cn_evidence_set_region
do
  uv run mdr retrieve --config "configs/experiments/${config}.yaml"
  uv run mdr evaluate --run "runs/retrieval/${config}/latest"
done
```

只运行不需要 Dense 模型的 BM25 baseline：

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest
```

## 7. MMDocIR 实验

### 7.1 放置 MMDocIR 数据

将 MMDocIR 原始数据放到：

```text
data/raw/mmdocir/
```

如果数据放在其他位置：

```bash
export MMDOC_RAG_DATA_ROOT=/path/to/mmdoc-data
```

### 7.2 生成标准数据

```bash
uv run mdr prepare --dataset mmdocir
```

快速限制文档数量：

```bash
uv run mdr prepare --dataset mmdocir --limit-docs 10
```

MMDocIR 适配器需要符合当前代码预期的本地文件结构。如果输出数量为 0，先检查原始文件布局和 `src/mmdocrag/datasets/adapters.py` 中的适配逻辑。

### 7.3 MMDocIR 四组配置实验

BM25 页面 baseline：

```bash
uv run mdr retrieve --config configs/experiments/e01_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/e01_bm25_page/latest
```

Dense 页面检索：

```bash
uv run mdr retrieve --config configs/experiments/e02_dense_page.yaml
uv run mdr evaluate --run runs/retrieval/e02_dense_page/latest
```

Layout-aware node：

```bash
uv run mdr retrieve --config configs/experiments/e03_layout_node.yaml
uv run mdr evaluate --run runs/retrieval/e03_layout_node/latest
```

Page -> Region：

```bash
uv run mdr retrieve --config configs/experiments/e04_page_region.yaml
uv run mdr evaluate --run runs/retrieval/e04_page_region/latest
```

这些 MMDocIR 配置使用 `BAAI/bge-m3`，需要本地模型缓存；必要时显式允许下载：

```bash
MDR_ALLOW_MODEL_DOWNLOAD=1 uv run mdr retrieve \
  --config configs/experiments/e02_dense_page.yaml
```

## 8. 运行结果文件

每次 `retrieve` 会新建时间戳目录，例如：

```text
runs/retrieval/cn_page_region/20260812_120000/
```

并更新：

```text
runs/retrieval/cn_page_region/latest/
```

检索阶段主要输出：

```text
predictions.parquet  检索命中及其分数、节点信息和 metadata
config.json          本次运行使用的配置
run_info.json        数据集、实验名、检索器类型和命中数量
```

运行 `evaluate` 后还会生成：

```text
metrics.json         Page Recall、MRR、nDCG、Region Hit 等指标
errors.csv           页面或节点未命中的问题
summary.md           指标和示例案例摘要
```

## 9. 代码质量检查

格式检查：

```bash
uv run ruff format --check src tests
```

自动格式化：

```bash
uv run ruff format src tests
```

静态检查：

```bash
uv run ruff check src tests
```

单元测试：

```bash
uv run pytest
```

运行指定测试文件：

```bash
uv run pytest tests/test_retrieval_metrics.py
uv run pytest tests/test_evidence_sufficiency.py
uv run pytest tests/test_cn_annual_reports_v2.py
```

## 10. 从零开始的推荐顺序

### 10.1 只检查环境

```bash
uv sync --dev
uv run mdr --help
uv run pytest
```

### 10.2 运行无真实数据的最小闭环

```bash
uv run mdr prepare --dataset demo
uv run mdr retrieve --config configs/experiments/demo_page_region.yaml
uv run mdr evaluate --run runs/retrieval/demo_page_region/latest
uv run mdr export-demo --run runs/retrieval/demo_page_region/latest
```

### 10.3 运行中文年报主实验

```bash
uv run mdr build-cn-annotations --questions-per-doc 8 --limit-docs 20
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20

uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest

uv run mdr retrieve --config configs/experiments/cn_evidence_set_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_evidence_set_region/latest
uv run mdr verify-evidence \
  --run runs/retrieval/cn_evidence_set_region/latest \
  --top-k 5
```

### 10.4 运行论文前的质量检查

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest
```

## 11. 常见问题

### `No module named mmdocrag`

不要直接使用系统 Python。使用：

```bash
uv run pytest
uv run mdr --help
```

如果必须使用未安装的解释器做临时检查，需要设置 `PYTHONPATH=src`，但仍必须安装项目依赖。

### Dense 检索提示模型不存在

中文年报和 MMDocIR 的 Dense 配置设置了 `require_model: true`。先确认模型已经缓存，或明确允许下载：

```bash
MDR_ALLOW_MODEL_DOWNLOAD=1 uv run mdr retrieve \
  --config configs/experiments/cn_dense_page.yaml
```

不要把 `MDR_DISABLE_SENTENCE_TRANSFORMERS=1` 和 `require_model: true` 一起使用；这会强制关闭模型并导致命令失败。TF-IDF fallback 只适用于 `require_model: false` 的配置或自定义实验。

### 找不到 processed parquet

先运行对应数据集的 `prepare`：

```bash
uv run mdr prepare --dataset demo
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
uv run mdr prepare --dataset mmdocir
```

### 找不到 `latest`

检查实验目录：

```bash
ls -la runs/retrieval/cn_page_region/
```

如果当前文件系统不支持软链接，代码会生成 `latest.txt`，评价时仍使用：

```bash
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

### 为什么没有生成可信答案

当前 CLI 只实现数据准备、检索、检索评价、证据充分性检查和 Demo 表导出；真正的 LLM 生成、答案支持性验证、冲突处理和拒答命令尚未实现。

## 12. 命令与研究阶段对应关系

| 命令/实验 | 研究作用 |
|---|---|
| `prepare` | 文档解析和统一证据数据构建 |
| `bm25_page` | 关键词页面 baseline |
| `dense_page` | 语义页面 baseline |
| `hybrid_page` | BM25/Dense 页面融合对照 |
| `page_region` | 预测页面到区域的两阶段检索 |
| `global_region` | 判断是否需要页面过滤 |
| `oracle_page_region` | 分离页面召回误差和区域定位上限 |
| `evidence_set_region` | 当前最小充分证据集检索核心 |
| `evaluate` | 页面/区域检索效果评价 |
| `verify-evidence` | 规则版证据充分性和引用一致性检查 |
| `export-demo` | 导出开题展示表 |

当前系统尚未覆盖的研究链路是：

```text
evidence cards -> LLM/VLM generation -> claim support -> citation validation -> refusal
```
