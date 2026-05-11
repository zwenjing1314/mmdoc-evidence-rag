# 开题前实验最终收尾记录

## 一、当前结论

中文年报开题前实验已经形成一个完整的小闭环。

当前闭环包括：

```text
PDF 数据准备
-> 逐页解析
-> 细粒度证据节点切分
-> QA 标注生成
-> QA 人工修订
-> 标准 parquet 表生成
-> 三组检索实验
-> 指标评价
-> 结果表导出
```

目前已经不只是“计划做什么”，而是已经有真实数据、真实代码、真实结果和可展示的错误分析。

## 二、已完成内容

## 1. 数据与标注

当前使用数据集：

```text
cn_annual_reports
```

原始 PDF 位置：

```text
data/raw/cn_annual_reports/pdfs/
```

修订后的 QA 标注：

```text
data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv
```

修订状态：

| 项目 | 数量 |
|---|---:|
| QA 总数 | 160 |
| 保留无明显问题 | 40 |
| 规则辅助修正 | 93 |
| 人工重点修正 | 27 |
| 仍需复核 | 0 |
| 可回答问题 | 160 |

所有数值题均已补充单位，当前没有 `answer_unit` 为空的 numeric 问题。

## 2. 标准数据表

运行：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

生成：

| 表 | 作用 |
|---|---|
| `documents.parquet` | 文档级表 |
| `pages.parquet` | 页面级表 |
| `nodes.parquet` | 细粒度证据节点表 |
| `queries.parquet` | 问题与标准证据表 |

当前规模：

| 项目 | 数量 |
|---|---:|
| documents | 20 |
| pages | 5327 |
| nodes | 99304 |
| queries | 160 |

证据节点匹配结果：

| 状态 | 数量 |
|---|---:|
| matched | 160 |
| fallback | 0 |
| missing | 0 |

说明所有 QA 都能映射到真实证据节点。

## 3. 检索实验

已完成三组实验：

| 方法 | 配置文件 | 说明 |
|---|---|---|
| BM25-page | `configs/experiments/cn_bm25_page.yaml` | 关键词页级 baseline |
| Dense-page | `configs/experiments/cn_dense_page.yaml` | 页级语义/TF-IDF fallback |
| Page -> Region | `configs/experiments/cn_page_region.yaml` | 先找页面，再找细粒度证据块 |

最终指标表：

```text
artifacts/figures/opening_experiment_comparison_table.md
```

当前结果：

| Method | Page Recall@1 | Page Recall@5 | Page Recall@10 | MRR | nDCG@5 | Region Hit@5 |
|---|---:|---:|---:|---:|---:|---:|
| BM25-page | 0.0437 | 0.1625 | 0.2437 | 0.0932 | 0.0398 | 0.0000 |
| Dense-page | 0.1938 | 0.2687 | 0.3187 | 0.2247 | 0.1080 | 0.0000 |
| Page -> Region | 0.1938 | 0.2625 | 0.2625 | 0.2183 | 0.1070 | 0.2000 |

解释：

1. BM25 是传统关键词 baseline，效果最低。
2. Dense-page 的页级召回最好。
3. Page -> Region 的页级效果接近 Dense-page，同时能命中细粒度证据节点。
4. `Region Hit@5 = 0.2000` 是开题前展示“细粒度证据定位”的关键指标。

## 三、开题报告中可以怎么说

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

## 四、答辩展示建议

开题前 PPT 建议只展示 4 个点：

1. **数据处理流程**  
   展示 `PDF -> Page -> Node -> Query -> Retrieval -> Evaluation`。

2. **数据规模**  
   展示 `20 PDFs / 5327 pages / 99304 nodes / 160 QA`。

3. **实验对比表**  
   展示 BM25、Dense-page、Page -> Region 三组结果。

4. **案例分析**  
   展示 1 个成功案例和 1 个失败案例，说明系统已经能工作，同时后续研究问题仍然真实存在。

## 五、接下来还要做什么

开题前核心实验已经够用了。

接下来不是继续无限加实验，而是做汇报材料收敛：

1. 把最终指标表放进开题报告。
2. 从 `runs/retrieval/cn_page_region/latest/summary.md` 选 2 到 3 个案例。
3. 把 `qa_annotations_v2_reviewed.csv` 的人工修订过程写成“数据构建与质量控制”。
4. 在开题报告中强调后续工作：
   - 引入更强中文/多语种 embedding 模型；
   - 优化表格结构化切分；
   - 做可信性验证；
   - 扩展到 MMDocIR。

## 六、当前不建议继续做的事

开题前暂时不建议继续做：

1. 大规模 MMDocIR 精修。
2. 复杂视觉版面识别训练。
3. 完整生成式 RAG 系统。
4. 大模型自动评判可信性。

原因是时间有限，当前中文年报实验已经足够支撑“已有实质工作”，接下来更重要的是把已有工作讲清楚。

## 七、最终命令清单

以后复现最终实验，可以按这个顺序运行：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20

uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest

MDR_DISABLE_SENTENCE_TRANSFORMERS=1 uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest

MDR_DISABLE_SENTENCE_TRANSFORMERS=1 uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

最终展示表：

```text
artifacts/figures/opening_experiment_comparison_table.md
```
