# 开题后后续开发说明书

更新时间：2026-05-29

本文档用于说明开题完成后，项目接下来应该优先完成哪些工作、为什么要做这些工作、需要增加和修改哪些模块，以及如何让论文系统区别于“直接把 PDF 输入大模型问答”的方式。

## 1. 当前项目定位需要收紧

当前项目已经完成了中文年报实验的基础闭环：

1. PDF 文档解析。
2. 页面级数据表构建。
3. 段落、表格块和表格行级证据节点构建。
4. 中文年报问答标注。
5. BM25-page、Dense-page、Page to Region 检索 baseline。
6. 单文档内部检索。
7. Page Recall、MRR、nDCG、Region Hit 等基础评价。

但当前系统还不能只定位为：

```text
PDF 问答助手
```

因为通用大模型已经可以直接读取 PDF 并回答一些问题。后续论文系统应明确定位为：

```text
面向长文档问答的可控证据检索、证据定位、证据集合构建与可信验证框架。
```

重点不是证明“大模型能不能答出来”，而是证明：

1. 答案来自哪里。
2. 证据页是否正确。
3. 证据节点是否正确。
4. 引用是否和答案一致。
5. 证据不足时是否能够拒答。
6. 一批文档和一批问题上能否批量评价、复现和分析错误。

## 2. 后续第一优先级

接下来第一阶段最应该完成的是：

```text
从“返回单个检索节点”升级为“构建可回答问题的 evidence set，并进行证据充分性验证”。
```

原因：

1. 这是区别于直接问大模型的核心价值。
2. 它和导师修改后的第二个创新点直接对应。
3. 它能解释为什么不是只做 BM25、Dense 或 Page to Region。
4. 它为后续可信生成、引用检查和拒答机制打基础。

当前 Page to Region 返回的是若干排序后的节点：

```text
query -> Top-K nodes
```

后续应该升级为：

```text
query -> candidate nodes -> evidence set -> sufficiency status
```

其中 evidence set 是一组最小充分证据，不是单个节点。

## 3. 为什么不能只和 DeepSeek 比“能否回答”

直接将 PDF 和问题输入 DeepSeek，可能得到答案和文字定位。但它存在几个论文实验难以接受的问题：

| 问题 | DeepSeek 直接问 PDF | 本项目应解决的方向 |
| --- | --- | --- |
| 可复现性 | 模型输出可能变化 | 固定数据、配置、指标和运行结果 |
| 可评价性 | 很难批量统计证据定位是否正确 | 用 gold pages、gold nodes 和指标评价 |
| 可解释性 | 不知道先看了哪些页面 | 保留候选页面、候选节点和分数 |
| 引用准确性 | 可能给出模糊章节或错误出处 | 输出 page_id、node_id、bbox、evidence_text |
| 证据充分性 | 可能证据不足仍回答 | 增加 sufficiency 判断和拒答 |
| 批量处理 | 更像单次交互 | 支持多文档、多问题批量实验 |
| 私有部署 | 外部平台可能有数据安全问题 | 本地解析、索引、检索和评估 |

因此，论文中不应该说“本文系统比 DeepSeek 更会回答”，而应该说：

```text
本文研究重点是让长文档问答过程可检索、可定位、可引用、可验证和可评价。
```

## 4. 第一阶段开发任务：Evidence Set

### 4.1 要解决的问题

当前系统返回的是 Top-K 节点列表，但很多问题需要多个证据共同支持。

例如：

```text
比亚迪 2025 年营业收入是多少？
```

可能需要：

1. 指标名称：营业收入。
2. 年份：2025。
3. 数值：803,964,958,000.00。
4. 单位：元。
5. 来源页：主要会计数据和财务指标。

如果只返回一个节点，可能只包含数值，不包含单位；或者包含单位，不包含具体指标行。因此应选择一个 evidence set。

### 4.2 新增数据结构建议

建议在 `src/mmdocrag/schemas.py` 中增加：

```python
class EvidenceSet(StrictRecord):
    query_id: str
    evidence_set_id: str
    doc_id: str
    nodes: list[EvidenceCard] = Field(default_factory=list)
    coverage: dict[str, bool] = Field(default_factory=dict)
    sufficiency_score: float = 0.0
    sufficiency_status: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)
```

其中：

| 字段 | 作用 |
| --- | --- |
| `query_id` | 对应哪个问题 |
| `evidence_set_id` | 证据集合 ID |
| `doc_id` | 所属文档 |
| `nodes` | 证据节点列表 |
| `coverage` | 问题要素覆盖情况 |
| `sufficiency_score` | 证据充分性分数 |
| `sufficiency_status` | `sufficient`、`insufficient`、`conflict` 等 |
| `metadata` | 额外信息 |

### 4.3 新增模块建议

建议新增目录：

```text
src/mmdocrag/evidence/
```

建议新增文件：

```text
src/mmdocrag/evidence/__init__.py
src/mmdocrag/evidence/requirements.py
src/mmdocrag/evidence/set_builder.py
src/mmdocrag/evidence/sufficiency.py
```

模块职责：

| 文件 | 作用 |
| --- | --- |
| `requirements.py` | 从问题和标注中抽取需要覆盖的要素 |
| `set_builder.py` | 从候选节点中选择 evidence set |
| `sufficiency.py` | 判断证据集合是否足以回答问题 |

### 4.4 第一版规则

第一版先不要复杂化，可以先做规则版。

数值型问题需要覆盖：

```text
指标名称
年份
数值
单位
```

文本型问题需要覆盖：

```text
问题关键词
核心实体
答案片段
```

证据充分性状态建议：

| 状态 | 含义 |
| --- | --- |
| `sufficient` | 证据集合基本覆盖回答所需信息 |
| `partial` | 覆盖部分要素，但不完整 |
| `insufficient` | 证据不足，不能可靠回答 |
| `conflict` | 候选证据之间存在冲突 |

### 4.5 验收标准

第一阶段完成后，应能输出：

```text
runs/evidence_sets/实验名/latest/evidence_sets.parquet
runs/evidence_sets/实验名/latest/sufficiency_metrics.json
runs/evidence_sets/实验名/latest/cases.md
```

最小验收：

1. 每个 query 都能生成一个 evidence set。
2. 每个 evidence set 至少包含 page_id、node_id、node_type、text、score。
3. 数值型问题能判断指标、年份、数值、单位是否覆盖。
4. 能统计 sufficient、partial、insufficient 的数量。
5. 能导出若干案例供人工检查。

## 5. 第二阶段开发任务：关键基线补齐

为了证明 Page to Region 和 evidence set 不是自然组合，需要补几个关键对照实验。

### 5.1 global-region

含义：

```text
不经过页面召回，直接在单篇文档所有 nodes 中检索。
```

作用：

对比“先页面后区域”是否有必要。

新增配置：

```text
configs/experiments/cn_global_region.yaml
```

### 5.2 oracle-page -> region

含义：

```text
假设页面召回已经正确，只在 gold evidence pages 内检索节点。
```

作用：

分析区域定位能力的上限。

如果 oracle-page 效果高，但 predicted-page 效果低，说明主要瓶颈在页面召回。

### 5.3 predicted-page -> region

含义：

```text
当前实际 Page to Region 流程。
```

作用：

和 oracle-page 对比，判断页面召回误差对区域定位的影响。

### 5.4 single-node vs evidence-set

含义：

```text
比较只选一个最高分节点，与选择一组证据节点。
```

作用：

证明 evidence set 是否比单节点更适合回答财务数值、单位和解释类问题。

## 6. 第三阶段开发任务：图表和图片信息

### 6.1 当前状态

当前系统没有真正存储图片或图表本身。

当前 `pages.parquet` 中：

```text
page_image_path 为空
```

当前 `nodes.parquet` 中：

```text
image_path 为空
```

当前图表信息只有在以下情况下才会进入系统：

```text
图表里的文字能被 PyMuPDF 当成文本抽取出来。
```

折线、柱状、饼图、趋势等视觉内容当前无法理解。

### 6.2 为什么需要补图表信息

题目中有“多模态长文档”，如果一直只做文本检索，会被质疑：

```text
你的多模态体现在哪里？
```

补图表和图片信息，不是第一优先级，但必须作为后续扩展任务。

### 6.3 建议实现路径

第一步：渲染页面图像。

新增输出目录：

```text
data/processed/cn_annual_reports/page_images/
```

每页保存为：

```text
{doc_id}_p{page_index}.png
```

并填充：

```text
PageRecord.page_image_path
```

第二步：裁剪证据节点区域图像。

根据 `EvidenceNode.bbox` 从页面图像中裁剪：

```text
data/processed/cn_annual_reports/node_images/
```

并填充：

```text
EvidenceNode.image_path
```

第三步：识别图表候选区域。

第一版可以先规则判断：

1. 页面中有“图”“趋势”“占比”“变化”等关键词。
2. PyMuPDF 提取到 image block。
3. 大块非文本区域附近有图表标题。

新增节点类型：

```text
chart_region
image_region
```

第四步：图表信息进入 evidence node。

建议 `chart_region` 节点保存：

```text
node_type = "chart_region"
bbox = 图表区域坐标
text = 图表标题、图例文字、附近说明文字
image_path = 图表裁剪图片路径
metadata = {
  "chart_caption": "...",
  "nearby_text": "...",
  "extraction_method": "pymupdf_image_block"
}
```

### 6.4 图表阶段验收标准

完成后至少要能证明：

1. 每个页面有对应 `page_image_path`。
2. 部分节点有 `image_path`。
3. 能抽取或标记 `chart_region`。
4. 能在案例中展示“文本证据 + 区域截图”。
5. 检索结果中可以返回图表区域节点。

注意：

第一版不要求真正理解折线图数值。先做到“图表区域可定位、可展示、可作为视觉证据”即可。

## 7. 第四阶段开发任务：可信生成与拒答

### 7.1 生成前验证

在回答前判断：

```text
当前 evidence set 是否足够回答问题。
```

如果不足，输出：

```text
insufficient
```

而不是强行回答。

### 7.2 生成后验证

生成答案后检查：

1. 答案中的数值是否出现在证据中。
2. 单位是否和证据一致。
3. 指标名称是否对应。
4. 引用的 page_id、node_id 是否包含答案。

### 7.3 拒答机制

拒答条件可以先做规则版：

1. Page Recall 候选分数低于阈值。
2. evidence set 覆盖要素不足。
3. 数值和单位冲突。
4. 引用节点不包含答案。

输出状态：

```text
supported
partially_supported
insufficient
conflict
citation_mismatch
unanswerable
```

## 8. 建议新增 CLI

为了让实验流程清晰，建议后续增加：

```bash
uv run mdr build-evidence-sets --run runs/retrieval/cn_page_region/latest
```

作用：

```text
读取检索结果 predictions.parquet，构建 evidence_sets.parquet。
```

建议再增加：

```bash
uv run mdr verify --evidence-run runs/evidence_sets/cn_page_region/latest
```

作用：

```text
进行证据充分性、答案支持性和引用一致性验证。
```

后续完整流程可以变成：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
uv run mdr build-evidence-sets --run runs/retrieval/cn_page_region/latest
uv run mdr verify --evidence-run runs/evidence_sets/cn_page_region/latest
```

## 9. 建议新增目录

建议逐步增加：

```text
src/mmdocrag/evidence/
src/mmdocrag/verification/
src/mmdocrag/vision/
configs/experiments/cn_global_region.yaml
configs/experiments/cn_oracle_page_region.yaml
configs/experiments/cn_hybrid_page.yaml
```

目录职责：

| 目录 | 作用 |
| --- | --- |
| `evidence` | evidence set 构建与充分性判断 |
| `verification` | 答案支持性、引用一致性和拒答 |
| `vision` | 页面渲染、区域截图、图表区域处理 |

## 10. 优先级排序

建议按下面顺序做。

### P0：必须先做

1. 补 `global-region` baseline。
2. 补 `oracle-page -> region` baseline。
3. 实现 evidence set 第一版。
4. 实现证据充分性规则判断。

原因：

这些直接支撑论文核心创新点，且不依赖外部大模型。

### P1：第二批做

1. 实现 hybrid retrieval：BM25 + Dense + RRF。
2. 实现 single-node vs evidence-set 对照实验。
3. 输出 evidence cards。
4. 实现数值型答案支持性验证。

原因：

这些能让实验更完整，能体现方法增量。

### P2：第三批做

1. 页面图像渲染。
2. 节点区域截图。
3. 图表区域节点 `chart_region`。
4. 可视化 evidence card。

原因：

这些体现多模态，但可以在核心检索和验证稳定后再做。

### P3：后续扩展

1. BGE-M3 真正向量检索。
2. BGE-reranker 重排序。
3. ColPali / ColQwen 视觉页面检索。
4. LLM verifier。

原因：

这些会提升效果，但依赖模型环境、算力和更复杂工程。

## 11. 论文中可以形成的实验组

后续论文实验可以组织为：

| 实验组 | 方法 | 目的 |
| --- | --- | --- |
| E1 | BM25-page | 关键词页面检索 baseline |
| E2 | Dense-page | 语义页面检索 baseline |
| E3 | Hybrid-page | 关键词和语义融合 |
| E4 | Global-region | 直接区域检索 |
| E5 | Predicted-page -> region | 两阶段检索 |
| E6 | Oracle-page -> region | 区域定位上限 |
| E7 | Single-node evidence | 单节点证据 |
| E8 | Evidence-set | 最小充分证据集合 |
| E9 | Evidence-set + verifier | 证据充分性和答案支持性验证 |
| E10 | Evidence-set + chart/image region | 多模态区域证据扩展 |

这样论文工作量会更清楚：

```text
不是做一个 PDF 问答工具，而是逐步研究检索粒度、检索范围、证据集合、证据充分性和多模态证据对结果可靠性的影响。
```

## 12. 与大模型直接读 PDF 的区别

最终系统需要能输出下面这种结构化结果：

```json
{
  "question": "比亚迪2025年营业收入是多少？",
  "answer": "803,964,958,000 元",
  "evidence_set": [
    {
      "page_id": "比亚迪：2025年年度报告_p8",
      "node_id": "比亚迪：2025年年度报告_p8_n023",
      "node_type": "table_row",
      "bbox": [80.1, 120.2, 520.4, 146.8],
      "text": "营业收入 803,964,958,000.00 ...",
      "image_path": "..."
    }
  ],
  "coverage": {
    "metric": true,
    "year": true,
    "value": true,
    "unit": true
  },
  "support_status": "supported",
  "citation_status": "matched"
}
```

这类输出和直接问大模型的区别是：

1. 每个答案都有结构化证据。
2. 每条证据能追溯到页面、节点和坐标。
3. 能判断证据是否足够。
4. 能批量统计正确率。
5. 能分析错误来自页面召回、区域定位、证据集合还是答案生成。

## 13. 最近一次具体开发建议

下一次写代码建议从下面任务开始：

```text
实现 global-region 和 oracle-page -> region 两个检索 baseline。
```

原因：

1. 改动范围比 evidence set 小。
2. 能直接补齐导师指出的关键实验缺口。
3. 能帮助判断当前 Page to Region 的瓶颈在哪里。

完成后再做：

```text
Evidence Set V1：基于候选 nodes 的规则式最小充分证据集合选择。
```

这样路线比较稳，不会一下子跳到大模型生成和复杂多模态。

