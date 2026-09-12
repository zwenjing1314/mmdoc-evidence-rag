# 开题前完整实验闭环后续步骤

## 一、当前已经完成到哪里

当前中文年报实验已经完成了一个“检索实验小闭环”：

```text
中文年报 PDF
-> 逐页解析
-> 段落/表格块切分
-> V2 QA 标注生成
-> 标准 parquet 表
-> BM25 / Page->Region 检索
-> 指标评价
-> 开题展示表导出
```

当前真实数据规模：

| 项目 | 数量 |
|---|---:|
| 年报 PDF | 20 |
| 页面 | 5327 |
| 细粒度节点 | 99304 |
| QA 问题 | 160 |

当前已经可以作为“已有实验基础”展示，但如果要形成更完整的开题前实验闭环，还需要继续完成以下步骤。

## 二、第一步：人工校验 V2 标注

文件位置：

```text
data/raw/cn_annual_reports/qa_annotations_v2.csv
```

建议优先人工检查 30 到 50 条，而不是一开始全部检查。

重点检查字段：

| 字段 | 检查内容 |
|---|---|
| `question` | 问题是否自然、是否对应当前公司 |
| `answer` | 答案是否正确 |
| `answer_unit` | 单位是否来自原文 |
| `raw_answer_value` | 数字是否抄对 |
| `value_evidence_text` | 是否包含指标值 |
| `unit_evidence_text` | 是否包含“单位：元/万元/亿元”等 |
| `evidence_pages` | 页码是否正确 |
| `question_type` | 类型是否合理 |

尤其要注意：

1. 括号数字通常表示负数，例如 `(88,556,470,495.64)`。
2. “单位：万元”和“单位：元”不能混淆。
3. 表格跨页时，单位可能在上一页。
4. 归母净利润、扣非净利润、净利润不要混成同一个指标。
5. 合并报表和母公司报表不要混淆。

建议输出一个人工校验记录：

```text
docs/opening_annotation_check_notes.md
```

记录哪些问题确认正确，哪些问题需要修正。

## 三、第二步：补一版人工修正后的标注

建议不要直接改自动生成文件，而是复制一份：

```text
data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv
```

然后让代码优先读取 reviewed 文件：

```text
qa_annotations_v2_reviewed.csv
-> qa_annotations_v2.csv
-> qa_annotations.csv
```

这样可以区分：

```text
自动生成标注
人工校验标注
旧版标注
```

开题报告里也可以写得更清楚：

```text
初始标注由规则自动生成，随后人工抽样校验并修正关键数值字段。
```

## 四、第三步：重新跑标准实验

人工校验后，重新运行：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

然后跑 BM25 baseline：

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest
```

再跑 Page -> Region：

```bash
MDR_DISABLE_SENTENCE_TRANSFORMERS=1 uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

最后导出展示表：

```bash
uv run mdr export-demo --run runs/retrieval/cn_page_region/latest
```

展示表位置：

```text
artifacts/figures/opening_experiment_table.md
```

## 五、第四步：补 Dense 检索实验

目前 Page -> Region 在没有本地模型时会使用 TF-IDF fallback。

开题前建议至少补一个 Dense 检索实验：

```bash
uv run mdr retrieve --config configs/experiments/e02_dense_page.yaml
uv run mdr evaluate --run runs/retrieval/e02_dense_page/latest
```

如果本地没有 `BAAI/bge-m3`，可以先保留 TF-IDF fallback 结果；如果后面能下载模型，再补一版 BGE 结果。

建议最终对比表至少包含：

| 方法 | 作用 |
|---|---|
| BM25-page | 传统关键词检索 baseline |
| TF-IDF/Dense-page | 离线语义检索 fallback |
| Page -> Region | 先页级召回，再细粒度证据定位 |

这样开题时能说明不是只跑了一个方法，而是有对比实验。

## 六、第五步：做案例分析

只看指标不够，开题前一定要准备案例分析。

建议从结果文件中挑 6 个案例：

```text
runs/retrieval/cn_page_region/latest/summary.md
runs/retrieval/cn_page_region/latest/errors.csv
```

案例类型建议包括：

| 案例类型 | 数量 | 说明 |
|---|---:|---|
| 成功案例 | 2 | 检索到正确页面和正确节点 |
| 页面对、节点错 | 1 | 说明细粒度定位仍有提升空间 |
| 公司错 | 1 | 说明公司名和指标名混淆问题 |
| 单位相关错误 | 1 | 说明可信性实验的必要性 |
| 风险文本类错误 | 1 | 说明长文本语义检索难度 |

每个案例建议整理成：

```text
问题
标准答案
标准证据页
模型 Top-3 命中
是否命中
错误原因
后续改进
```

这部分非常适合写入开题报告的“初步实验结果与问题分析”。

## 七、第六步：补可信性最小实验

你的论文方向不是只做检索，还涉及可信性，所以开题前最好补一个最小可信性实验。

第一版不需要复杂模型，可以先做规则版：

```text
检索结果
-> evidence card
-> 判断答案数字是否出现在证据中
-> 判断单位是否出现在证据中
-> 判断问题指标是否出现在证据中
-> 输出 support / insufficient / conflict
```

建议新增输出：

```text
runs/trustworthiness/cn_rule_check/latest/trust_metrics.json
runs/trustworthiness/cn_rule_check/latest/trust_cases.csv
```

可以统计：

| 指标 | 含义 |
|---|---|
| value_supported_rate | 数字被证据支持的比例 |
| unit_supported_rate | 单位被证据支持的比例 |
| metric_supported_rate | 指标名称被证据支持的比例 |
| fully_supported_rate | 数字、单位、指标都被支持的比例 |

这一步非常关键，因为它能把论文从“检索系统”推进到“可信证据支撑”。

## 八、第七步：整理开题报告中的实验表达

开题报告中建议这样写实验部分：

```text
本文先以中文上市公司年度报告为实验对象，构建面向长文档财务问答的证据检索数据集。
当前已完成 20 份年度报告的解析，共得到 5327 个页面和 99304 个细粒度证据节点。
在此基础上，构建 160 条覆盖首页信息、主要会计数据、现金流、研发、资产负债和风险文本的问题。
初步实验比较了 BM25 页级检索和 Page->Region 两阶段检索方法。
实验结果显示，两阶段方法在 Page Recall、MRR 和 Region Hit 上均优于 BM25 baseline。
后续将进一步引入语义向量模型和可信性验证模块，提高证据定位与答案支撑判断能力。
```

这段话的重点是：

1. 有真实数据。
2. 有具体数量。
3. 有标准化处理。
4. 有 baseline。
5. 有改进方法。
6. 有评价指标。
7. 有后续研究方向。

## 九、第八步：准备开题答辩展示材料

建议准备 4 张核心实验展示页：

### 第 1 张：数据构建流程

展示：

```text
PDF -> Page -> Node -> QA -> Retrieval -> Evaluation
```

配数量：

```text
20 PDFs
5327 pages
99304 nodes
160 QA
```

### 第 2 张：问题类型分布

展示问题覆盖：

```text
报告年度/标题
营业收入
归母净利润
现金流
研发投入
资产总额
风险文本
同比变化
```

### 第 3 张：检索结果对比

展示 BM25 和 Page -> Region 的指标表。

### 第 4 张：案例分析

展示一个成功案例和一个失败案例。

成功案例说明系统已经能找到证据。

失败案例说明后续研究问题真实存在，不是为了做系统而做系统。

## 十、推荐执行顺序

建议接下来按这个顺序做：

1. 人工检查 `qa_annotations_v2.csv` 中 30 到 50 条。
2. 生成 `qa_annotations_v2_reviewed.csv`。
3. 修改 prepare 优先读取 reviewed 文件。
4. 重新跑 prepare、BM25、Page -> Region。
5. 补 Dense-page 实验。
6. 整理 6 个案例分析。
7. 做规则版可信性检查。
8. 更新开题报告实验部分。
9. 准备 4 张开题展示页。

其中最优先的是：

```text
人工校验标注
案例分析
可信性最小实验
```

因为这三项最能让老师看到“实质工作量”和“研究问题”。
