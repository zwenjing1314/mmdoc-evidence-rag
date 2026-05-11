# 中文年报开题实验完整复现记录

## 一、文档目的

这份文档完整记录中文年报实验从开始到结束的处理流程。

目标是让任何人按照本文档中的命令，都能复现当前开题前实验闭环：

```text
中文年报 PDF
-> QA 标注生成
-> QA 人工修订
-> PDF 逐页解析
-> 细粒度证据节点切分
-> 标准 parquet 表
-> 三组检索实验
-> 指标评价
-> 开题展示结果表
```

当前实验只使用中文年报数据集：

```text
cn_annual_reports
```

暂不使用 MMDocIR。

## 二、项目路径和运行前提

项目目录：

```text
/Users/zhouwenjing/Documents/WorkTransfer/mmdoc-evidence-rag
```

进入项目：

```bash
cd /Users/zhouwenjing/Documents/WorkTransfer/mmdoc-evidence-rag
```

项目使用 uv 管理环境。

正常情况下，命令写法是：

```bash
uv run mdr ...
```

如果当前终端找不到 `uv`，可以使用完整路径：

```bash
UV_CACHE_DIR=.uv-cache UV_PYTHON_INSTALL_DIR=.uv-python /Users/zhouwenjing/.local/bin/uv run mdr ...
```

本文档为了清晰，主要使用简写：

```bash
uv run mdr ...
```

如果简写失败，就换成完整路径。

## 三、最终数据和结果概览

当前最终使用的人工修订标注文件：

```text
data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv
```

最终标准数据规模：

| 项目 | 数量 |
|---|---:|
| documents | 20 |
| pages | 5327 |
| nodes | 99304 |
| queries | 160 |

节点类型分布：

| node_type | 数量 |
|---|---:|
| `paragraph` | 75481 |
| `table_block` | 22677 |
| `table_row` | 1146 |

证据节点匹配结果：

| 状态 | 数量 |
|---|---:|
| matched | 160 |
| fallback | 0 |
| missing | 0 |

最终检索指标：

| Method | Page Recall@1 | Page Recall@5 | Page Recall@10 | MRR | nDCG@5 | Region Hit@5 |
|---|---:|---:|---:|---:|---:|---:|
| BM25-page | 0.0437 | 0.1625 | 0.2437 | 0.0932 | 0.0398 | 0.0000 |
| Dense-page | 0.1938 | 0.2687 | 0.3187 | 0.2247 | 0.1080 | 0.0000 |
| Page -> Region | 0.1938 | 0.2625 | 0.2625 | 0.2183 | 0.1070 | 0.2000 |

最终展示表：

```text
artifacts/figures/opening_experiment_comparison_table.md
```

## 四、第一阶段：准备中文年报 PDF 数据

## 1. 原始 PDF 存放位置

中文年报 PDF 放在：

```text
data/raw/cn_annual_reports/pdfs/
```

当前该目录下有 20 份 PDF。

这些 PDF 最初来自桌面数据目录，并通过软连接或复制方式放入项目数据目录。

检查 PDF：

```bash
find data/raw/cn_annual_reports/pdfs -maxdepth 1 -name "*.pdf" | sort
```

作用：

```text
列出中文年报 PDF，确认原始数据已经放入项目。
```

预期结果：

```text
能看到 20 个 PDF 文件。
```

## 五、第二阶段：生成第一版 QA 标注

项目最早生成过旧版标注：

```text
data/raw/cn_annual_reports/qa_annotations.csv
```

这个文件是第一版规则生成结果，主要用于先跑通实验。

旧版特点：

1. 每份年报约 5 个问题。
2. 问题集中在报告前几页。
3. 数值答案缺少单位字段。
4. 证据粒度比较粗。

它现在保留作为历史版本和回退版本。

当前最终实验不再优先使用它。

## 六、第三阶段：生成 V2 QA 标注

后来为了让问题更分散、字段更完整，新增了 V2 标注生成命令。

运行命令：

```bash
uv run mdr build-cn-annotations --questions-per-doc 8 --limit-docs 20
```

作用：

```text
读取 data/raw/cn_annual_reports/pdfs/ 下的 20 份 PDF；
从每份年报中规则抽取约 8 条问题；
生成带单位、证据文本、问题类型、难度、来源章节的 QA 标注。
```

输出文件：

```text
data/raw/cn_annual_reports/qa_annotations_v2.csv
data/raw/cn_annual_reports/qa_annotations_v2_generation_log.md
```

输出结果：

```text
Chinese annual report V2 annotations written to:
data/raw/cn_annual_reports/qa_annotations_v2.csv
```

V2 标注字段包括：

| 字段 | 作用 |
|---|---|
| `query_id` | 问题编号 |
| `doc_id` | 所属年报 |
| `question` | 问题 |
| `answer` | 答案 |
| `evidence_pages` | 证据页 |
| `evidence_text` | 证据文本 |
| `answer_unit` | 答案单位 |
| `raw_answer_value` | 原始数值 |
| `normalized_answer` | 规范答案 |
| `value_evidence_text` | 数值证据文本 |
| `unit_evidence_text` | 单位证据文本 |
| `question_type` | 问题类型 |
| `difficulty` | 难度 |
| `source_section` | 来源章节 |

## 七、第四阶段：人工校验和修订 QA 标注

V2 标注是规则自动生成的，不能直接作为最终金标准。

我们先抽查了 10 条高风险样本，记录在：

```text
docs/opening_annotation_check_noftes.md
```

抽查发现的问题包括：

1. 把年份 `2025` 误抽成净利润。
2. 把章节序号 `2` 误抽成研发投入。
3. 把 `99.15%` 误抽成资产总额。
4. 把收入占比 `99%` 误抽成营业收入同比增减。
5. 有些 `营业收入（元）` 没有识别出单位。

随后对全部 160 条 V2 标注进行了修订。

最终修订文件：

```text
data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv
```

修订结果：

| 项目 | 数量 |
|---|---:|
| QA 总数 | 160 |
| 保留无明显问题 | 40 |
| 规则辅助修正 | 93 |
| 人工重点修正 | 27 |
| 仍需复核 | 0 |
| 可回答问题 | 160 |

修订重点：

1. 补齐所有 numeric 问题的单位。
2. 修正资产总额类问题。
3. 修正研发投入/研发费用类问题。
4. 修正同比增减类问题。
5. 缩窄风险文本类问题表述。

现在项目读取 QA 时的优先顺序是：

```text
qa_annotations_v2_reviewed.csv
-> qa_annotations_v2.csv
-> qa_annotations.csv
```

也就是说，只要 reviewed 文件存在，后续实验都会优先使用人工修订版本。

## 八、第五阶段：准备标准 parquet 数据表

运行命令：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

作用：

```text
读取中文年报 PDF；
逐页抽取文本；
把每一页切分成 paragraph、table_block、table_row 等细粒度节点；
读取 qa_annotations_v2_reviewed.csv；
把 evidence_pages 映射到 evidence_node_ids；
写出标准 parquet 表。
```

输出目录：

```text
data/processed/cn_annual_reports/
```

输出文件：

```text
documents.parquet
pages.parquet
nodes.parquet
queries.parquet
```

运行结果：

```text
documents: 20
pages: 5327
nodes: 99304
queries: 160
message: Chinese annual reports parsed with paragraph/table-row evidence nodes.
```

四张表的作用：

| 文件 | 作用 |
|---|---|
| `documents.parquet` | 文档级信息，一份 PDF 一条 |
| `pages.parquet` | 页面级信息，一页一条 |
| `nodes.parquet` | 细粒度证据块，一页多个 |
| `queries.parquet` | 问题、答案、标准证据页和证据节点 |

检查标准表：

```bash
find data/processed/cn_annual_reports -maxdepth 1 -type f | sort
```

预期看到：

```text
data/processed/cn_annual_reports/documents.parquet
data/processed/cn_annual_reports/pages.parquet
data/processed/cn_annual_reports/nodes.parquet
data/processed/cn_annual_reports/queries.parquet
```

## 九、第六阶段：检查证据节点匹配情况

运行命令：

```bash
uv run python -c "import json, polars as pl; q=pl.read_parquet('data/processed/cn_annual_reports/queries.parquet'); statuses=[json.loads(x).get('node_match_status') for x in q['metadata']]; print({'queries': q.height, 'matched': statuses.count('matched'), 'fallback': statuses.count('fallback'), 'missing': statuses.count('missing')})"
```

作用：

```text
确认 queries.parquet 中的每条问题是否成功匹配到真实 evidence_node_ids。
```

当前结果：

```text
{'queries': 160, 'matched': 160, 'fallback': 0, 'missing': 0}
```

含义：

1. 160 条问题全部匹配到细粒度证据节点。
2. 没有使用 fallback。
3. 没有 missing。

这说明数据闭环是完整的。

## 十、第七阶段：运行 BM25-page baseline

配置文件：

```text
configs/experiments/cn_bm25_page.yaml
```

运行命令：

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
```

作用：

```text
运行传统关键词页级检索 baseline。
输入是 pages.parquet 和 queries.parquet。
输出是每个问题的 Top-k 页面检索结果。
```

输出目录：

```text
runs/retrieval/cn_bm25_page/{timestamp}/
```

最近一次运行可通过：

```text
runs/retrieval/cn_bm25_page/latest
```

访问。

评价命令：

```bash
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest
```

作用：

```text
读取 predictions.parquet；
与 queries.parquet 中的 evidence_page_ids / evidence_node_ids 对比；
计算 Page Recall、MRR、nDCG、Region Hit。
```

输出文件：

```text
runs/retrieval/cn_bm25_page/latest/metrics.json
runs/retrieval/cn_bm25_page/latest/errors.csv
runs/retrieval/cn_bm25_page/latest/summary.md
```

当前指标：

| Metric | Value |
|---|---:|
| Page Recall@1 | 0.0437 |
| Page Recall@5 | 0.1625 |
| Page Recall@10 | 0.2437 |
| MRR | 0.0932 |
| nDCG@5 | 0.0398 |
| nDCG@10 | 0.0501 |
| Region Hit@5 | 0.0000 |

解释：

```text
BM25-page 是页级检索，不返回 node_id，所以 Region Hit@5 为 0。
```

## 十一、第八阶段：运行 Dense-page 实验

配置文件：

```text
configs/experiments/cn_dense_page.yaml
```

运行命令：

```bash
MDR_DISABLE_SENTENCE_TRANSFORMERS=1 uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
```

为什么加 `MDR_DISABLE_SENTENCE_TRANSFORMERS=1`：

```text
当前本地没有确认可用的 BAAI/bge-m3 模型。
加这个环境变量后，程序会跳过 sentence-transformers 模型加载，
使用离线可运行的 TF-IDF fallback。
这样不依赖网络和模型下载，开题前更稳定。
```

如果以后本地已经下载好 BGE 模型，可以尝试不加这个变量：

```bash
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
```

评价命令：

```bash
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest
```

输出目录：

```text
runs/retrieval/cn_dense_page/latest/
```

当前指标：

| Metric | Value |
|---|---:|
| Page Recall@1 | 0.1938 |
| Page Recall@5 | 0.2687 |
| Page Recall@10 | 0.3187 |
| MRR | 0.2247 |
| nDCG@5 | 0.1080 |
| nDCG@10 | 0.1150 |
| Region Hit@5 | 0.0000 |

解释：

```text
Dense-page 是页级检索，页级指标明显高于 BM25。
但它不返回 node_id，因此 Region Hit@5 仍为 0。
```

## 十二、第九阶段：运行 Page -> Region 实验

配置文件：

```text
configs/experiments/cn_page_region.yaml
```

运行命令：

```bash
MDR_DISABLE_SENTENCE_TRANSFORMERS=1 uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
```

作用：

```text
先做页级召回；
再在候选页面内部检索 paragraph / table_block / table_row；
最终输出带 node_id 的细粒度证据检索结果。
```

评价命令：

```bash
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

输出目录：

```text
runs/retrieval/cn_page_region/latest/
```

当前指标：

| Metric | Value |
|---|---:|
| Page Recall@1 | 0.1938 |
| Page Recall@5 | 0.2625 |
| Page Recall@10 | 0.2625 |
| MRR | 0.2183 |
| nDCG@5 | 0.1070 |
| nDCG@10 | 0.1070 |
| Region Hit@5 | 0.2000 |

解释：

```text
Page -> Region 的页级指标接近 Dense-page。
更重要的是，它能返回具体 evidence node，因此 Region Hit@5 达到 0.2000。
这是开题前展示“细粒度证据定位”的关键结果。
```

## 十三、第十阶段：导出最终对比表

运行命令：

```bash
uv run python -c "from pathlib import Path; import json; runs={'BM25-page':'runs/retrieval/cn_bm25_page/latest','Dense-page (TF-IDF fallback)':'runs/retrieval/cn_dense_page/latest','Page -> Region':'runs/retrieval/cn_page_region/latest'}; out=Path('artifacts/figures/opening_experiment_comparison_table.md'); out.parent.mkdir(parents=True, exist_ok=True); lines=['# Opening Defense Chinese Annual Report Retrieval Comparison','', '| Method | Page Recall@1 | Page Recall@5 | Page Recall@10 | MRR | nDCG@5 | Region Hit@5 | Run |', '|---|---:|---:|---:|---:|---:|---:|---|']; [lines.append(f\"| {method} | {json.loads((Path(run)/'metrics.json').read_text(encoding='utf-8'))['page_recall@1']:.4f} | {json.loads((Path(run)/'metrics.json').read_text(encoding='utf-8'))['page_recall@5']:.4f} | {json.loads((Path(run)/'metrics.json').read_text(encoding='utf-8'))['page_recall@10']:.4f} | {json.loads((Path(run)/'metrics.json').read_text(encoding='utf-8'))['mrr']:.4f} | {json.loads((Path(run)/'metrics.json').read_text(encoding='utf-8'))['ndcg@5']:.4f} | {json.loads((Path(run)/'metrics.json').read_text(encoding='utf-8'))['region_hit@5']:.4f} | `{run}` |\") for method, run in runs.items()]; lines += ['', 'Dataset: `cn_annual_reports`', 'Annotation file: `data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv`']; out.write_text('\\n'.join(lines)+'\\n', encoding='utf-8')"
```

作用：

```text
读取三组实验的 metrics.json；
生成开题展示用的最终指标对比表。
```

输出文件：

```text
artifacts/figures/opening_experiment_comparison_table.md
```

当前内容：

| Method | Page Recall@1 | Page Recall@5 | Page Recall@10 | MRR | nDCG@5 | Region Hit@5 |
|---|---:|---:|---:|---:|---:|---:|
| BM25-page | 0.0437 | 0.1625 | 0.2437 | 0.0932 | 0.0398 | 0.0000 |
| Dense-page | 0.1938 | 0.2687 | 0.3187 | 0.2247 | 0.1080 | 0.0000 |
| Page -> Region | 0.1938 | 0.2625 | 0.2625 | 0.2183 | 0.1070 | 0.2000 |

## 十四、第十一阶段：代码质量检查

运行：

```bash
uv run ruff check src tests
```

作用：

```text
检查 Python 代码风格和潜在问题。
```

当前结果：

```text
All checks passed!
```

运行：

```bash
uv run pytest
```

作用：

```text
运行单元测试和 smoke test，确认核心流程没有被破坏。
```

当前结果：

```text
10 passed
```

## 十五、完整复现命令清单

如果要从当前项目状态重新复现实验，按下面顺序运行即可。

```bash
cd /Users/zhouwenjing/Documents/WorkTransfer/mmdoc-evidence-rag
```

确认 PDF：

```bash
find data/raw/cn_annual_reports/pdfs -maxdepth 1 -name "*.pdf" | sort
```

生成 V2 自动标注：

```bash
uv run mdr build-cn-annotations --questions-per-doc 8 --limit-docs 20
```

注意：

```text
如果已经有人工修订版 qa_annotations_v2_reviewed.csv，不建议再次覆盖它。
该命令只会重新生成 qa_annotations_v2.csv，不会生成 reviewed 文件。
```

准备标准表：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

运行 BM25：

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest
```

运行 Dense-page：

```bash
MDR_DISABLE_SENTENCE_TRANSFORMERS=1 uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest
```

运行 Page -> Region：

```bash
MDR_DISABLE_SENTENCE_TRANSFORMERS=1 uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

质量检查：

```bash
uv run ruff check src tests
uv run pytest
```

最终查看结果：

```bash
cat artifacts/figures/opening_experiment_comparison_table.md
```

## 十六、每个关键输出文件的作用

| 文件 | 作用 |
|---|---|
| `data/raw/cn_annual_reports/qa_annotations.csv` | 旧版自动 QA 标注 |
| `data/raw/cn_annual_reports/qa_annotations_v2.csv` | V2 自动 QA 标注 |
| `data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv` | 最终人工修订标注 |
| `data/processed/cn_annual_reports/documents.parquet` | 文档级标准表 |
| `data/processed/cn_annual_reports/pages.parquet` | 页面级标准表 |
| `data/processed/cn_annual_reports/nodes.parquet` | 细粒度证据节点标准表 |
| `data/processed/cn_annual_reports/queries.parquet` | 问题与标准证据表 |
| `runs/retrieval/*/latest/predictions.parquet` | 检索预测结果 |
| `runs/retrieval/*/latest/metrics.json` | 指标结果 |
| `runs/retrieval/*/latest/errors.csv` | 错误案例 |
| `runs/retrieval/*/latest/summary.md` | 实验摘要 |
| `artifacts/figures/opening_experiment_comparison_table.md` | 开题展示对比表 |

## 十七、开题报告中可直接使用的实验描述

可以写成：

```text
本文首先以中文上市公司年度报告为对象，构建面向长文档财务问答的证据检索实验数据。
当前已完成 20 份年度报告的逐页解析，共得到 5327 个页面和 99304 个细粒度证据节点。
在此基础上，构建并人工修订 160 条覆盖首页信息、主要会计数据、现金流、研发、资产负债、
风险文本和同比变化的问题。

初步实验比较了 BM25 页级检索、Dense 页级检索和 Page->Region 两阶段检索。
实验结果显示，Dense-page 在页级召回上优于 BM25 baseline；Page->Region 在保持相近页级检索效果的同时，
能够进一步定位细粒度证据节点，Region Hit@5 达到 0.2000。
这说明两阶段证据检索方法具备进一步扩展为可信 RAG 问答系统的基础。
```

## 十八、当前实验的边界

当前实验已经足够用于开题前展示，但它不是最终毕业论文全部实验。

当前实验边界：

1. 只使用中文年报数据。
2. MMDocIR 暂未纳入最终实验。
3. Dense-page 当前使用 TF-IDF fallback，没有强制下载 BGE 模型。
4. Page -> Region 的 Region 是文本块级节点，不是完整视觉区域检测。
5. 可信性验证模块还未正式实现，只是在数据中预留了单位、证据文本和证据节点字段。

后续论文工作可以继续扩展：

1. 引入 BGE-M3 或其他中文 embedding 模型。
2. 优化表格结构化切分。
3. 增加可信性验证实验。
4. 扩展到 MMDocIR 数据集。
5. 加入 RAG 生成回答模块。
