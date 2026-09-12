# 中文年报实验 V2 修改记录

## 一、为什么要做这次修改

上一版中文年报实验已经可以完成基本流程：

```text
PDF 年报
-> pages.parquet
-> nodes.parquet
-> queries.parquet
-> 检索
-> 评价
```

但是它仍然有三个明显问题：

1. `nodes` 数量和 `pages` 数量一样多，说明每一页只生成了一个整页节点，还没有真正做到细粒度证据定位。
2. `qa_annotations.csv` 中的数值答案缺少单位字段，而年报中的单位经常写在表格上方，例如“单位：元”，不是直接跟在数字后面。
3. 问题集中在前几页，且问题类型比较雷同，不足以体现长文档检索、财务表格定位和可信证据支撑的实验价值。

所以本次 V2 修改的目标是：把中文年报实验从“页级可跑通”升级为“开题展示可解释、可评价、可继续扩展”的细粒度实验版本。

## 二、本次修改完成了什么

### 1. 将 nodes 从整页切成段落和表格块

修改位置：

```text
src/mmdocrag/datasets/adapters.py
```

原来的逻辑是：

```text
1 个 page -> 1 个 page_text node
```

现在改成：

```text
1 个 page -> 多个 paragraph / table_block / table_row node
```

节点类型包括：

| node_type | 含义 |
|---|---|
| `paragraph` | 普通段落文本 |
| `table_block` | 疑似表格或包含多个数字的文本块 |
| `table_row` | 包含关键财务指标的表格行 |

重点识别的财务指标包括：

```text
营业收入
归属于上市公司股东的净利润
经营活动产生的现金流量净额
研发投入
研发费用
资产总额
负债合计
```

节点编号也改成稳定格式：

```text
{page_id}_n001
{page_id}_n002
{page_id}_n003
```

这样重复运行 `prepare` 时，节点 ID 更稳定，方便做证据映射和结果复现。

### 2. 新增 V2 标注生成命令

新增 CLI 命令：

```bash
uv run mdr build-cn-annotations --questions-per-doc 8 --limit-docs 20
```

输出文件：

```text
data/raw/cn_annual_reports/qa_annotations_v2.csv
```

原始 `qa_annotations.csv` 保留不动。后续 `prepare` 会优先读取 `qa_annotations_v2.csv`，如果没有该文件，再回退读取旧版 `qa_annotations.csv`。

### 3. 给 QA 增加单位字段和证据文本字段

新版标注文件保留旧字段，并新增了这些字段：

| 字段 | 作用 |
|---|---|
| `answer_unit` | 答案单位，例如“元”“万元” |
| `raw_answer_value` | 原始数值 |
| `normalized_answer` | 规范化后的答案 |
| `value_evidence_text` | 指标值所在证据文本 |
| `unit_evidence_text` | 单位所在证据文本 |
| `value_evidence_pages` | 指标值所在页 |
| `unit_evidence_pages` | 单位所在页 |
| `question_type` | 问题类型 |
| `difficulty` | 难度 |
| `source_section` | 来源章节 |

这样可以处理年报里常见的情况：

```text
表格上方：单位：元
表格行中：营业收入 233,432,768,960.43
```

最终答案可以写成：

```text
233,432,768,960.43 元
```

这比只写数字更适合后续做可信性实验，因为模型不仅要找到数字，还要确认单位是否有证据支持。

### 4. 支持“值”和“单位”的两处定位

年报中的单位和数值不一定在同一个位置。本次实现中，单位查找逻辑支持：

```text
当前指标附近查找单位
-> 如果找不到，则向前两页查找最近的“单位：xxx”
```

这可以覆盖一部分跨页续表场景，例如第一页表格标题写了“单位：元”，下一页继续展示指标行。

注意：代码不会自动把“万元”换算成“元”，而是保留报告原始单位，避免引入换算错误。

### 5. 扩展问题规模和问题分布

新版目标是每份年报生成约 8 条问题，20 份年报共生成 160 条问题。

问题覆盖类型包括：

| 类型 | 示例 |
|---|---|
| 首页信息 | 报告年度、报告标题 |
| 主要会计数据 | 营业收入、归母净利润 |
| 现金流 | 经营活动产生的现金流量净额 |
| 研发 | 研发投入或研发费用 |
| 资产负债 | 资产总额 |
| 风险文本 | 风险相关内容 |
| 对比问题 | 营业收入同比增减幅度 |

这样问题不再只集中在前几页，实验更能体现长文档检索的难度。

### 6. 细粒度证据节点映射

新版 `prepare` 会根据以下信息将 QA 映射到具体 node：

```text
value_evidence_text
unit_evidence_text
raw_answer_value
answer
question 中的财务关键词
```

如果能匹配到具体节点，则写入：

```text
node_match_status = matched
```

如果匹配不到，则使用页面内第一个节点兜底，并写入：

```text
node_match_status = fallback
```

这次真实运行结果是：

```text
matched: 160
fallback: 0
missing: 0
```

说明 160 条 QA 都成功映射到了真实细粒度 node。

## 三、真实运行结果

运行命令：

```bash
uv run mdr build-cn-annotations --questions-per-doc 8 --limit-docs 20
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

生成结果：

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

这说明现在已经不是“一页一个节点”，而是完成了初步细粒度切分。

## 四、检索实验结果

本次 V2 数据比之前更难，因为问题更多，分布更广，不再只集中在前几页。

当前结果：

| 方法 | Page Recall@1 | Page Recall@5 | MRR | nDCG@5 | Region Hit@5 |
|---|---:|---:|---:|---:|---:|
| BM25-page | 0.0250 | 0.1500 | 0.0682 | 0.0330 | 0.0000 |
| Page -> Region | 0.1750 | 0.2313 | 0.1936 | 0.0957 | 0.2062 |

结果说明：

1. BM25 页级检索是很弱的 baseline。
2. Page -> Region 明显优于 BM25，说明“先找页面，再找细粒度证据块”的方向是有效的。
3. V2 数据难度提升后，指标下降是正常现象，反而更接近真实论文实验。

## 五、验证情况

已运行：

```bash
uv run ruff check src tests
uv run pytest
```

测试结果：

```text
10 passed
```

新增测试覆盖：

1. 页面切分后 `nodes > pages`。
2. 表格指标行能识别为 `table_row`。
3. `单位：元` 能写入 `answer_unit` 和 `unit_evidence_text`。
4. `qa_annotations_v2.csv` 能被读取。
5. `evidence_node_ids` 能映射到真实 node。

## 六、目前仍需注意的问题

1. V2 标注仍然是规则生成，不等于完全人工金标准。
2. 数值题需要人工抽查，尤其是负数、括号、单位、跨页续表。
3. 风险类文本题目前只是截取风险相关段落，答案还需要人工润色。
4. 当前的 `table_row` 是基于文本规则识别，不是完整的视觉表格结构识别。
5. `Region` 当前定义为段落/表格行文本块，还不是精确 bbox 区域。

## 七、这次修改对开题报告的意义

这次修改后，可以在开题前明确展示已经完成的实质工作：

1. 已经构建了中文年报数据处理流程。
2. 已经完成 20 份年报的逐页解析。
3. 已经生成 99304 个细粒度证据节点。
4. 已经构建 160 条带单位和证据文本的 QA。
5. 已经完成 BM25 与 Page -> Region 两组检索实验。
6. 已经得到可量化指标和可分析失败案例。

这比单纯写“计划使用 RAG”要扎实得多，也更容易向老师说明：目前已经有真实数据、真实代码、真实实验结果，后续是在这个基础上继续提升。
