# 项目结构与 Python 模块说明

## 一、这份笔记的阅读方式

这份文档用于解释当前项目是如何组织的，以及每个关键文件夹、关键 Python 文件在实验系统中的作用。

建议按下面顺序理解：

```text
项目目标
-> 关键文件夹
-> 标准数据表
-> Python 包结构
-> CLI 命令如何调用代码
-> 一次完整实验如何流动
```

这个项目不是一个普通的网页项目，也不是只放脚本的文件夹，而是一个围绕“长文档证据检索与可信问答实验”搭建的 Python 实验工程。

## 二、项目整体目标

项目名称：

```text
mmdoc-evidence-rag
```

项目当前主要服务毕业论文开题前实验，核心目标是：

```text
把中文年度报告 PDF 转成可检索、可评价、可展示的实验数据；
实现页级检索和细粒度证据块检索；
输出评价指标和开题展示材料；
为后续 RAG 生成与可信性验证实验预留接口。
```

当前最重要的数据集是：

```text
cn_annual_reports
```

也就是中文上市公司年度报告。

当前已经实现的实验链路：

```text
中文年报 PDF
-> 逐页解析
-> 段落/表格块切分
-> QA 标注生成
-> 标准 parquet 表
-> 检索实验
-> 指标评价
-> 开题展示表导出
```

## 三、项目根目录关键文件说明

项目根目录大致如下：

```text
mmdoc-evidence-rag/
├── artifacts/
├── configs/
├── data/
├── docs/
├── notebooks/
├── runs/
├── scripts/
├── src/
├── tests/
├── pyproject.toml
├── uv.lock
└── README.md
```

### 1. `pyproject.toml`

这是项目最重要的配置文件之一。

它负责：

1. 声明项目名称和 Python 版本。
2. 声明依赖库。
3. 声明开发依赖。
4. 声明 CLI 命令入口。
5. 配置 ruff、pytest、mypy 等工具。

其中最关键的是：

```toml
[project.scripts]
mdr = "mmdocrag.cli:app"
```

这表示命令：

```bash
uv run mdr ...
```

会进入：

```text
src/mmdocrag/cli.py
```

也就是说，`mdr` 是这个项目统一的命令行入口。

### 2. `uv.lock`

这是 uv 生成的依赖锁文件。

作用是固定依赖版本，让环境更可复现。

简单理解：

```text
pyproject.toml 说明需要哪些库；
uv.lock 记录最终安装了哪些具体版本。
```

### 3. `README.md`

项目说明入口文件。

它适合放最简洁的项目介绍、快速启动命令和常用实验流程。

更详细的解释文档放在 `docs/` 目录。

## 四、关键文件夹作用

## 1. `data/`

`data/` 是项目的数据目录，负责存放原始数据、中间数据和处理后的标准数据表。

当前结构大致是：

```text
data/
├── raw/
├── interim/
├── processed/
└── samples/
```

### `data/raw/`

存放原始数据。

例如：

```text
data/raw/cn_annual_reports/
├── pdfs/
├── qa_annotations.csv
├── qa_annotations_v2.csv
└── qa_annotations_v2_generation_log.md
```

其中：

| 文件或文件夹 | 作用 |
|---|---|
| `pdfs/` | 存放中文年度报告 PDF |
| `qa_annotations.csv` | 旧版 QA 标注 |
| `qa_annotations_v2.csv` | 新版 QA 标注，包含单位和证据文本 |
| `qa_annotations_v2_generation_log.md` | V2 标注生成日志 |

注意：`raw` 中的数据通常是“源头数据”，代码不应该随便覆盖旧数据。

### `data/interim/`

存放中间过程数据。

目前这个目录主要是预留的，后续如果需要保存 OCR 中间结果、PDF 页面图片、表格抽取缓存等，可以放这里。

### `data/processed/`

存放项目标准化后的数据表。

例如：

```text
data/processed/cn_annual_reports/
├── documents.parquet
├── pages.parquet
├── nodes.parquet
└── queries.parquet
```

这四张表是项目后续检索和评价的核心输入。

| 表名 | 作用 |
|---|---|
| `documents.parquet` | 文档级信息，一份 PDF 对应一条 document |
| `pages.parquet` | 页面级信息，一页 PDF 对应一条 page |
| `nodes.parquet` | 证据块信息，一页可以切成多个 node |
| `queries.parquet` | 问题和标准答案信息 |

### `data/samples/`

用于放小样本数据。

适合将来做快速测试，避免每次都处理完整年报。

## 2. `configs/`

`configs/` 是实验配置目录。

它让实验参数从代码中分离出来，方便重复运行和对比。

当前主要结构：

```text
configs/
├── datasets/
├── experiments/
├── generators/
├── parsers/
└── retrievers/
```

### `configs/experiments/`

这是目前最常用的配置文件夹。

例如：

```text
configs/experiments/cn_bm25_page.yaml
configs/experiments/cn_page_region.yaml
```

这些 YAML 文件告诉程序：

1. 使用哪个数据集。
2. 使用哪种检索方法。
3. top_k 是多少。
4. 结果输出到哪里。

例如运行：

```bash
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
```

程序会读取这个配置，然后调用对应检索方法。

### `configs/datasets/`

用于保存数据集配置。

当前更多是作为项目结构预留，后续可以把数据路径、字段映射、数据集描述放进来。

### `configs/parsers/`、`configs/retrievers/`、`configs/generators/`

这些目录目前主要是预留。

未来可以分别用于：

| 目录 | 未来作用 |
|---|---|
| `parsers/` | PDF 解析、OCR、表格抽取配置 |
| `retrievers/` | 检索器参数配置 |
| `generators/` | RAG 生成模型配置 |

## 3. `src/`

`src/` 是项目真正的 Python 源代码目录。

当前核心包是：

```text
src/mmdocrag/
```

项目中的 CLI、数据处理、检索、评价、导出都在这个包里。

## 4. `runs/`

`runs/` 存放每次实验运行结果。

例如：

```text
runs/retrieval/cn_page_region/
├── 20260510_115114/
└── latest
```

每次运行检索都会生成一个时间戳目录。

目录中通常包括：

| 文件 | 作用 |
|---|---|
| `predictions.parquet` | 检索结果 |
| `config.json` | 本次运行使用的配置 |
| `run_info.json` | 本次运行的基础信息 |
| `metrics.json` | 评价指标 |
| `errors.csv` | 错误案例 |
| `summary.md` | 实验摘要和示例案例 |

`latest` 指向最近一次运行结果，方便执行：

```bash
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

## 5. `artifacts/`

`artifacts/` 存放实验产物。

例如：

```text
artifacts/figures/opening_experiment_table.md
```

这个文件就是开题展示用的指标表。

未来还可以放：

| 子目录 | 作用 |
|---|---|
| `figures/` | 图表、Markdown 表格 |
| `indices/` | 检索索引 |
| `embeddings/` | 向量缓存 |
| `parsed_docs/` | 解析后的文档结果 |

## 6. `docs/`

`docs/` 是项目文档目录。

它不是代码运行必须的目录，但对毕业论文非常重要，因为它记录了：

1. 项目如何搭建。
2. 数据如何准备。
3. 实验如何运行。
4. 为什么这样设计。
5. 遇到的问题和解决方案。

当前已有文档包括：

| 文档 | 作用 |
|---|---|
| `project_build_from_zero.md` | 从 0 到 1 构建项目的说明 |
| `run_real_data_workflow.md` | 真实数据运行流程 |
| `opening_experiment_closure_steps.md` | 开题前完整实验闭环步骤 |
| `data_schema.md` | 数据表结构说明 |
| `experiment_plan.md` | 实验计划 |

子目录包括：

| 子目录 | 作用 |
|---|---|
| `environment/` | 环境配置说明 |
| `knowledge_notes/` | 基础知识笔记 |
| `questions_and_answers/` | 问题与解答沉淀 |
| `project_change_logs/` | 项目修改记录 |

## 7. `tests/`

`tests/` 是测试目录。

作用是保证核心功能不会被后续修改破坏。

当前测试包括：

| 测试文件 | 作用 |
|---|---|
| `test_schemas_io.py` | 测试 schema 和 parquet 读写 |
| `test_retrieval_metrics.py` | 测试检索打分和评价指标 |
| `test_demo_smoke.py` | 测试 demo 全流程 |
| `test_cn_annual_reports_v2.py` | 测试中文年报 V2 节点切分和标注读取 |

运行测试：

```bash
uv run pytest
```

## 五、标准数据表的作用

项目中最重要的四张标准表是：

```text
documents.parquet
pages.parquet
nodes.parquet
queries.parquet
```

它们由：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

生成。

## 1. `documents.parquet`

文档级表。

一份 PDF 对应一条记录。

主要字段包括：

| 字段 | 含义 |
|---|---|
| `doc_id` | 文档 ID，通常来自 PDF 文件名 |
| `dataset` | 数据集名称 |
| `title` | 文档标题 |
| `source_path` | 原始 PDF 路径 |
| `domain` | 文档领域，例如 annual_report |
| `language` | 文档语言 |
| `num_pages` | 页数 |

## 2. `pages.parquet`

页面级表。

一页 PDF 对应一条记录。

主要字段包括：

| 字段 | 含义 |
|---|---|
| `doc_id` | 所属文档 |
| `page_id` | 页面 ID |
| `page_index` | 页码 |
| `page_text` | 页面文本 |
| `ocr_text` | OCR 或解析文本 |
| `metadata` | 页面解析信息 |

例如：

```text
万科A：2025年年度报告_p10
```

表示万科 A 年报第 10 页。

## 3. `nodes.parquet`

证据节点表。

一页可以对应多个 node。

当前中文年报 V2 中，node 包括：

```text
paragraph
table_block
table_row
```

主要字段包括：

| 字段 | 含义 |
|---|---|
| `node_id` | 节点 ID |
| `doc_id` | 所属文档 |
| `page_id` | 所属页面 |
| `node_type` | 节点类型 |
| `text` | 节点文本 |
| `bbox` | 页面区域坐标，目前部分节点有 |
| `reading_order` | 阅读顺序 |
| `metadata` | 切分方法、单位候选等信息 |

例如：

```text
万科A：2025年年度报告_p10_n001
万科A：2025年年度报告_p10_n002
```

## 4. `queries.parquet`

问题表。

一条 QA 对应一条 query。

主要字段包括：

| 字段 | 含义 |
|---|---|
| `query_id` | 问题 ID |
| `doc_id` | 问题所属文档 |
| `question` | 问题文本 |
| `answer` | 标准答案 |
| `question_type` | 问题类型 |
| `evidence_page_ids` | 标准证据页 |
| `evidence_node_ids` | 标准证据节点 |
| `metadata` | 单位、证据文本、难度等扩展信息 |

`queries.parquet` 是评价检索结果是否命中的依据。

## 六、Python 包结构说明

核心代码都在：

```text
src/mmdocrag/
```

结构如下：

```text
src/mmdocrag/
├── cli.py
├── config.py
├── io.py
├── paths.py
├── schemas.py
├── datasets/
├── retrieval/
├── evaluation/
└── exporting/
```

## 1. `src/mmdocrag/cli.py`

这是项目命令行入口。

因为 `pyproject.toml` 中写了：

```toml
mdr = "mmdocrag.cli:app"
```

所以所有：

```bash
uv run mdr ...
```

都会进入这个文件。

当前主要命令包括：

| 命令 | 作用 |
|---|---|
| `prepare` | 把原始数据处理成标准 parquet 表 |
| `build-cn-annotations` | 生成中文年报 V2 QA 标注 |
| `retrieve` | 运行检索实验 |
| `evaluate` | 评价检索结果 |
| `export-demo` | 导出开题展示表 |

例如：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

会调用：

```text
prepare_dataset("cn_annual_reports", limit_docs=20)
```

## 2. `src/mmdocrag/schemas.py`

这是项目的数据模型定义文件。

它使用 Pydantic 定义了标准记录结构。

主要模型包括：

| 模型 | 作用 |
|---|---|
| `DocumentRecord` | 文档级记录 |
| `PageRecord` | 页面级记录 |
| `EvidenceNode` | 证据节点记录 |
| `QueryRecord` | 问题记录 |
| `RetrievalHit` | 一条检索命中结果 |
| `RetrievalRun` | 一次检索运行 |
| `EvidenceCard` | 后续可信性证据卡片预留结构 |

这个文件的意义是：所有数据都先变成统一结构，再写入 parquet 或传给检索模块。

例如，`EvidenceNode` 统一规定了：

```text
node_id
doc_id
page_id
node_type
text
reading_order
metadata
```

这样不管 node 来自 PDF 文本、OCR、表格解析，后续检索代码都可以用同一个接口处理。

## 3. `src/mmdocrag/io.py`

这是数据读写模块。

主要负责：

1. 把 Pydantic record 写成 parquet。
2. 从 parquet 读回 Pydantic record。
3. 处理 `metadata`、`bbox`、`evidence_page_ids` 等 JSON 字段。

关键函数：

| 函数 | 作用 |
|---|---|
| `write_records` | 写任意 record 列表到 parquet |
| `read_records` | 从 parquet 读取记录 |
| `write_processed_dataset` | 一次写入四张标准表 |
| `read_processed_dataset` | 一次读取四张标准表 |
| `write_hits` | 写检索结果 |
| `read_hits` | 读检索结果 |

它让项目不用到处写 parquet 读写逻辑。

## 4. `src/mmdocrag/paths.py`

这是路径管理模块。

作用是统一管理项目路径，避免代码里写死个人电脑绝对路径。

主要函数包括：

| 函数 | 作用 |
|---|---|
| `project_root` | 获取项目根目录 |
| `data_root` | 获取数据目录 |
| `runs_root` | 获取实验运行结果目录 |
| `artifacts_root` | 获取实验产物目录 |
| `resolve_project_path` | 把相对路径解析成项目内绝对路径 |

比如数据根目录默认是：

```text
项目根目录/data
```

但也可以通过环境变量修改：

```text
MMDOC_RAG_DATA_ROOT
```

这样项目更适合迁移到别的电脑或服务器。

## 5. `src/mmdocrag/config.py`

这是配置读取模块。

主要负责读取 YAML 配置。

例如：

```bash
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
```

会读取这个 YAML 文件，然后让检索代码知道：

```text
dataset 是什么
retriever 类型是什么
top_k 是多少
输出目录在哪里
```

它的作用是把实验参数从代码中抽离出来。

## 七、数据集模块 `src/mmdocrag/datasets/`

这个模块负责把原始数据转换成标准数据表。

核心文件：

```text
src/mmdocrag/datasets/adapters.py
```

它是当前项目最重要的文件之一。

## 1. `prepare_dataset`

这是数据准备的统一入口。

它根据 dataset 名称分发到不同处理函数：

```text
demo -> prepare_demo
mmdocir -> prepare_mmdocir
cn_annual_reports -> prepare_cn_annual_reports
```

所以运行：

```bash
uv run mdr prepare --dataset cn_annual_reports
```

最终会进入：

```text
prepare_cn_annual_reports
```

## 2. `prepare_demo`

生成内置 demo 数据。

作用是：即使没有真实数据，也能跑通项目流程。

它会在代码里直接构造：

```text
documents
pages
nodes
queries
```

适合测试命令是否正常。

## 3. `prepare_mmdocir`

MMDocIR 数据适配器。

目前是通用读取版本，能尝试读取：

```text
json
jsonl
csv
parquet
```

它现在不是主实验重点，后续等中文年报完成后再精修。

## 4. `prepare_cn_annual_reports`

中文年报数据准备函数。

这是当前最核心的数据处理函数。

它完成：

```text
读取 PDF
-> 抽取每页文本和文本块
-> 生成 documents
-> 生成 pages
-> 切分 nodes
-> 读取 QA 标注
-> 匹配 evidence_node_ids
-> 写出四张标准 parquet 表
```

运行后会生成：

```text
data/processed/cn_annual_reports/documents.parquet
data/processed/cn_annual_reports/pages.parquet
data/processed/cn_annual_reports/nodes.parquet
data/processed/cn_annual_reports/queries.parquet
```

## 5. `build_cn_annotations`

中文年报 V2 标注生成函数。

对应命令：

```bash
uv run mdr build-cn-annotations --questions-per-doc 8 --limit-docs 20
```

它会读取 PDF 文本，自动生成：

```text
data/raw/cn_annual_reports/qa_annotations_v2.csv
```

生成的问题类型包括：

```text
报告年度
报告标题
营业收入
归母净利润
经营活动现金流量净额
研发投入
资产总额
风险文本
营业收入同比变化
```

同时会写入：

```text
answer_unit
raw_answer_value
normalized_answer
value_evidence_text
unit_evidence_text
question_type
difficulty
source_section
```

## 6. 中文年报节点切分相关函数

这些函数主要服务 `prepare_cn_annual_reports`。

| 函数 | 作用 |
|---|---|
| `_extract_pdf_page_items` | 用 PyMuPDF 抽取每页文本和 block |
| `_build_cn_page_nodes` | 把一页切成多个 evidence node |
| `_block_chunks` | 根据 PyMuPDF block 生成候选块 |
| `_fallback_text_chunks` | block 不可用时按文本行切分 |
| `_metric_row_chunks` | 把财务指标行切成 `table_row` |
| `_looks_like_table_block` | 判断一个文本块是否像表格 |
| `_unit_candidates` | 从页面文本中提取“单位：xxx” |

这些函数让：

```text
pages 数量 < nodes 数量
```

当前真实结果是：

```text
pages: 5327
nodes: 99304
```

## 8. 中文年报 QA 生成相关函数

这些函数主要服务 `build_cn_annotations`。

| 函数 | 作用 |
|---|---|
| `_build_cn_doc_annotation_rows` | 为一份年报生成多条 QA |
| `_annotation_row` | 统一构造一行 QA 标注 |
| `_company_name_from_doc_id` | 从文件名中提取公司名 |
| `_infer_report_year` | 推断报告年度 |
| `_infer_report_title` | 推断报告标题 |
| `_find_metric_answer` | 查找财务指标数值 |
| `_find_revenue_growth` | 查找营业收入同比变化 |
| `_find_risk_answer` | 查找风险相关文本 |
| `_find_unit_near` | 在指标附近查找单位 |
| `_find_recent_unit` | 当前页找不到单位时向前页查找 |
| `_clip_text` | 截取证据文本片段 |

这里最重要的是单位处理。

因为年报经常写成：

```text
单位：元
营业收入 233,432,768,960.43
```

所以项目需要分别定位：

```text
数值证据
单位证据
```

## 9. 中文年报证据节点匹配函数

这些函数负责把 QA 标注映射到 `nodes.parquet` 中的具体节点。

| 函数 | 作用 |
|---|---|
| `_load_cn_queries` | 读取 QA 标注并生成 QueryRecord |
| `_match_cn_evidence_nodes` | 为 QA 匹配 evidence_node_ids |
| `_score_node_for_annotation` | 计算 node 和 QA 的匹配分数 |
| `_normalize_for_match` | 归一化文本用于匹配 |
| `_compact_numeric_text` | 提取数字形式用于匹配 |
| `_char_overlap_score` | 计算证据文本和节点文本重合度 |

匹配状态会写入：

```text
metadata.node_match_status
```

可能值：

| 状态 | 含义 |
|---|---|
| `matched` | 成功匹配细粒度节点 |
| `fallback` | 没匹配到精确节点，使用页面内节点兜底 |
| `missing` | 没有可用节点 |

当前真实运行结果：

```text
matched: 160
fallback: 0
missing: 0
```

## 八、检索模块 `src/mmdocrag/retrieval/`

检索模块负责根据问题去检索页面或节点。

主要文件：

```text
src/mmdocrag/retrieval/scoring.py
src/mmdocrag/retrieval/pipeline.py
```

## 1. `retrieval/scoring.py`

这是基础打分算法文件。

当前主要包括：

| 类或函数 | 作用 |
|---|---|
| `SimpleBM25` | 简单 BM25 检索打分 |
| `SimpleTfidf` | 简单 TF-IDF 检索打分 |
| `cosine_similarity` | 计算余弦相似度 |
| `reciprocal_rank_fusion` | RRF 融合排序 |

BM25 更像关键词匹配。

TF-IDF/Dense fallback 更像轻量语义匹配。

RRF 用于把页面排序和节点排序融合起来。

## 2. `retrieval/pipeline.py`

这是检索实验主流程。

最重要的函数是：

```text
run_retrieval
```

它会：

```text
读取实验 YAML 配置
-> 读取 processed 数据表
-> 根据 retriever 类型选择检索方法
-> 写出 predictions.parquet
-> 写出 config.json 和 run_info.json
-> 更新 latest
```

支持的检索类型包括：

| retriever type | 作用 |
|---|---|
| `bm25_page` | 页级 BM25 检索 |
| `dense_page` | 页级 dense 检索，没模型时回退 TF-IDF |
| `layout_node` | 节点级检索 |
| `page_region` | 先检索页面，再在页面内检索节点 |

关键函数：

| 函数 | 作用 |
|---|---|
| `retrieve_pages` | 对页面进行检索 |
| `retrieve_nodes` | 对 evidence nodes 进行检索 |
| `retrieve_page_region` | 两阶段检索 |
| `score_texts` | 根据方法选择 BM25、dense 或 TF-IDF |
| `try_sentence_transformer_scores` | 尝试使用 sentence-transformers |
| `update_latest` | 维护 latest 指向最新实验 |

当前中文年报最重要的方法是：

```text
page_region
```

它的思路是：

```text
先找相关页面
-> 再从这些页面的 nodes 中找具体证据块
-> 用 RRF 融合页面分数和节点分数
```

## 九、评价模块 `src/mmdocrag/evaluation/`

评价模块负责判断检索结果好不好。

主要文件：

```text
src/mmdocrag/evaluation/metrics.py
src/mmdocrag/evaluation/pipeline.py
```

## 1. `evaluation/metrics.py`

这里定义具体评价指标。

当前指标包括：

| 指标 | 含义 |
|---|---|
| `Page Recall@k` | Top-k 结果中是否命中标准证据页 |
| `MRR` | 正确结果排名越靠前，分数越高 |
| `nDCG@k` | 考虑排序位置的检索质量指标 |
| `Region Hit@k` | Top-k 结果中是否命中标准证据 node |

其中：

```text
Page Recall
```

看的是页面是否找对。

```text
Region Hit
```

看的是细粒度证据块是否找对。

## 2. `evaluation/pipeline.py`

这是评价主流程。

核心函数：

```text
evaluate_run
```

它会读取：

```text
runs/retrieval/xxx/latest/predictions.parquet
data/processed/{dataset}/queries.parquet
```

然后输出：

```text
metrics.json
errors.csv
summary.md
```

这些文件分别用于：

| 文件 | 作用 |
|---|---|
| `metrics.json` | 保存指标 |
| `errors.csv` | 保存错误案例 |
| `summary.md` | 生成可读摘要和示例 |

## 十、导出模块 `src/mmdocrag/exporting/`

导出模块负责把实验结果整理成开题展示材料。

主要文件：

```text
src/mmdocrag/exporting/demo.py
```

核心函数：

```text
export_demo_table
```

对应命令：

```bash
uv run mdr export-demo --run runs/retrieval/cn_page_region/latest
```

输出：

```text
artifacts/figures/opening_experiment_table.md
```

这个表可以直接放进开题报告或汇报 PPT。

## 十一、一次完整命令如何流动

下面用中文年报实验说明命令和代码之间的关系。

## 1. 生成 V2 标注

命令：

```bash
uv run mdr build-cn-annotations --questions-per-doc 8 --limit-docs 20
```

执行链路：

```text
pyproject.toml
-> mmdocrag.cli:app
-> cli.py 中的 build_cn_annotations_command
-> datasets/adapters.py 中的 build_cn_annotations
-> 读取 PDF
-> 抽取文本
-> 生成 qa_annotations_v2.csv
```

## 2. 准备标准数据表

命令：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

执行链路：

```text
cli.py prepare
-> prepare_dataset
-> prepare_cn_annual_reports
-> _extract_pdf_page_items
-> _build_cn_page_nodes
-> _load_cn_queries
-> write_processed_dataset
```

输出：

```text
data/processed/cn_annual_reports/documents.parquet
data/processed/cn_annual_reports/pages.parquet
data/processed/cn_annual_reports/nodes.parquet
data/processed/cn_annual_reports/queries.parquet
```

## 3. 运行检索

命令：

```bash
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
```

执行链路：

```text
cli.py retrieve
-> run_retrieval
-> load_config
-> read_processed_dataset
-> retrieve_page_region
-> write_hits
-> update_latest
```

输出：

```text
runs/retrieval/cn_page_region/{timestamp}/predictions.parquet
```

## 4. 评价结果

命令：

```bash
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

执行链路：

```text
cli.py evaluate
-> evaluate_run
-> read_hits
-> read_processed_dataset
-> 计算 Page Recall / MRR / nDCG / Region Hit
-> 写出 metrics.json / errors.csv / summary.md
```

## 5. 导出展示表

命令：

```bash
uv run mdr export-demo --run runs/retrieval/cn_page_region/latest
```

执行链路：

```text
cli.py export_demo
-> export_demo_table
-> 读取 metrics.json
-> 写出 opening_experiment_table.md
```

## 十二、当前中文年报实验的关键结果

当前 V2 数据处理结果：

| 项目 | 数量 |
|---|---:|
| documents | 20 |
| pages | 5327 |
| nodes | 99304 |
| queries | 160 |

节点类型：

| node_type | 数量 |
|---|---:|
| `paragraph` | 75481 |
| `table_block` | 22677 |
| `table_row` | 1146 |

检索结果：

| 方法 | Page Recall@1 | Page Recall@5 | MRR | nDCG@5 | Region Hit@5 |
|---|---:|---:|---:|---:|---:|
| BM25-page | 0.0250 | 0.1500 | 0.0682 | 0.0330 | 0.0000 |
| Page -> Region | 0.1750 | 0.2313 | 0.1936 | 0.0957 | 0.2062 |

这些结果可以说明：

1. 已经完成真实 PDF 数据处理。
2. 已经完成细粒度证据节点构建。
3. 已经有 160 条 QA。
4. 已经完成 baseline 对比。
5. Page -> Region 比 BM25-page 更适合当前任务。

## 十三、后续扩展时应该重点看哪些文件

如果要继续改数据处理，看：

```text
src/mmdocrag/datasets/adapters.py
```

如果要继续改检索方法，看：

```text
src/mmdocrag/retrieval/pipeline.py
src/mmdocrag/retrieval/scoring.py
```

如果要继续改评价指标，看：

```text
src/mmdocrag/evaluation/metrics.py
src/mmdocrag/evaluation/pipeline.py
```

如果要新增命令，看：

```text
src/mmdocrag/cli.py
```

如果要改标准数据结构，看：

```text
src/mmdocrag/schemas.py
```

如果要改实验配置，看：

```text
configs/experiments/
```

## 十四、用一句话解释这个项目

这个项目是一个面向毕业论文实验的中文长文档证据检索系统：它把年度报告 PDF 转成标准化的页面、证据块和问答数据，运行多种检索方法，评价页面命中和证据块命中效果，并输出可用于开题展示的实验结果。
