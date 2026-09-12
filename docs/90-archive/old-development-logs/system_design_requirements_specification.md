# 多模态长文档证据检索与可信生成系统设计需求规格说明书

## 1. 文档目的

本文档用于描述毕业论文项目“面向多模态长文档的多粒度证据检索与可信生成方法研究”对应实验系统的设计需求。该系统面向 PDF 长文档问答场景，重点支持文档解析、证据节点构建、证据图组织、页面—区域—证据集层次化检索、证据增强生成、分层可信验证、拒答决策和实验评估。

本文档既作为后续系统开发的需求说明，也作为论文方法设计、实验设计和答辩说明的依据。

## 2. 系统定位

### 2.1 系统名称

建议系统名称：

**MDR-EvidenceRAG：面向长文档的多粒度证据检索增强生成系统**

其中：

- `MDR` 表示 Multi-granularity Document Retrieval；
- `EvidenceRAG` 表示以证据组织、证据检索、证据引用和证据验证为核心的 RAG 系统。

### 2.2 系统研究定位

本系统不是从零训练多模态基础模型，也不是专门改进 OCR、表格识别或问答模型，而是在已有文档解析工具、文本检索模型、视觉检索模型和大语言模型能力基础上，研究以下核心问题：

1. 如何将 PDF 长文档中的页面、章节、段落、表格块、表格行和图表区域组织为可检索、可引用、可验证的多粒度证据图；
2. 如何从长文档中检索能够回答问题的最小充分证据集，而不是只检索单个相似文本片段；
3. 如何判断检索证据是否足以回答问题，以及生成答案是否被证据支持；
4. 如何在证据不足、证据冲突或引用不一致时进行二次检索或拒答。

### 2.3 系统应用场景

系统主要应用于需要从复杂 PDF 长文档中查找答案并复核证据来源的场景，包括：

- 中文上市公司年度报告分析；
- 招股说明书审阅；
- 审计报告与财务报告检索；
- 合同条款问答；
- 政策文件问答；
- 企业制度知识库问答；
- 科研论文与技术报告问答。

典型问题示例：

- 某公司 2023 年营业收入是多少？
- 某公司本年度研发投入金额是多少？
- 报告中披露的主要风险有哪些？
- 某合同中付款条件在哪一页？
- 某政策适用于哪些企业？

## 3. 系统范围

### 3.1 第一阶段必须实现的范围

第一阶段面向开题后论文实验主线，重点实现“证据检索”主贡献：

1. PDF 文档解析；
2. 页面级数据表构建；
3. 段落、表格块、表格行等证据节点构建；
4. 轻量级多粒度证据图表示；
5. 页面级候选召回；
6. 区域级证据节点检索；
7. 最小充分证据集选择；
8. 检索实验评价；
9. 错误分析和案例导出。

### 3.2 第二阶段应实现的范围

第二阶段在检索基础上扩展可信生成与验证：

1. evidence cards 构造；
2. 基于证据的生成回答；
3. 数值型问题一致性验证；
4. 表格型问题四元组验证；
5. 文本型问题证据覆盖度验证；
6. 引用一致性验证；
7. 二次检索和拒答机制；
8. 生成与可信性指标评估。

### 3.3 第三阶段可选扩展范围

第三阶段根据时间和算力选择性实现：

1. BGE-M3 向量检索；
2. BGE-reranker 或 Cross-Encoder 重排序；
3. LayoutLMv3 / LiLT 版面感知表示；
4. ColPali / ColQwen 页面视觉检索；
5. 图表区域检测和图表描述生成；
6. MMDocIR、LongDocURL、MMLongBench-Doc 等公开数据集适配；
7. FAISS、Milvus、Chroma 等持久化向量索引。

### 3.4 明确不作为主创新的内容

为控制论文边界，以下内容不作为本文主创新：

- 不从零预训练多模态基础模型；
- 不把 OCR 模型改进作为主要贡献；
- 不把复杂表格结构识别作为主要贡献；
- 不把图表数值抽取作为主要贡献；
- 不把端到端问答模型训练作为主要贡献；
- 不以构建大而全的工业 RAG 平台作为主要目标。

### 3.5 实验创新点

根据开题后导师意见，本文实验系统的创新点应从“大而全的 RAG 系统组合”收缩为围绕证据检索和证据可信性的三个递进问题：

```text
证据如何组织
  -> 如何检索最小充分证据集
  -> 如何验证证据是否足够、答案是否被支持、引用是否一致
```

#### 创新点一：构建面向检索、引用与验证闭环的轻量级多粒度证据图表示

传统固定长度文本切块容易破坏长文档中的页面结构、章节层级、表格归属关系和证据来源信息。本文不再仅将 PDF 切分为普通文本 chunk，而是将页面、章节、段落、表格块、表格行和图表区域等文档元素统一建模为 `evidence node`，并显式记录包含关系、阅读顺序、表格归属、标题层级和来源关系，形成轻量级证据图结构。

该创新点的核心不在于重新提出复杂图神经网络，而在于构建一种能够同时服务于检索、引用和验证的证据组织方式。每个证据节点保留页码、区域坐标、元素类型、文本内容、层级关系和来源信息，使文档内容从普通文本片段转化为可定位、可引用、可验证的证据单元。

需要通过实验回答的问题：

- 页面级、段落级、表格块级、表格行级等不同粒度对检索效果有何影响；
- 表格行级证据是否更有利于财务数值问题；
- 证据图中的包含关系、阅读顺序和表格归属关系是否有助于后续证据集选择；
- 引用到具体页码和证据节点是否能提升答案可复核性。

对应实验：

- 粒度消融实验；
- page-only vs paragraph-node vs table-row-node；
- single-node retrieval vs graph-aware candidate expansion；
- citation accuracy / region hit 分析。

#### 创新点二：设计证据充分性感知的页面—区域—证据集层次化检索与重排序方法

现有 Page→Region 检索往往关注单个候选节点的相似度排序，但真实长文档问答经常需要多个证据共同支撑回答。例如财务数值问题不仅需要数值，还需要指标名称、年份、单位和来源页码；文本解释类问题不仅需要相关句子，还需要关键实体、条件和结论。

因此，本文的核心方法不是只检索单个最相似节点，而是面向可回答性选择 `minimum sufficient evidence set`，即最小充分证据集。

本文对“最小充分证据集”的定义如下：

- **充分**：候选证据集能够覆盖回答问题所需的关键证据要素；
- **最小**：在满足证据要素覆盖的前提下，尽量减少冗余页面和冗余节点数量。

该方法采用层次化检索流程：

```text
页面级候选召回
  -> 候选页面内区域节点检索
  -> 证据要素覆盖度计算
  -> 候选 evidence set 组合
  -> 充分性与冗余度联合重排序
```

候选 evidence set 的得分应综合以下信号：

- 语义相关性；
- 页面召回得分；
- 节点检索得分；
- 节点类型匹配；
- 版面位置先验；
- 问题要素覆盖度；
- 单位一致性；
- 数值匹配；
- 冗余惩罚。

建议评分形式：

```text
EvidenceSetScore(q, S) =
  α · SemanticScore(q, S)
+ β · PagePrior(q, S)
+ γ · TypeMatch(q, S)
+ δ · SlotCoverage(q, S)
+ η · UnitConsistency(q, S)
- λ · Redundancy(S)
```

其中：

- `q` 表示问题；
- `S` 表示候选证据集；
- `SlotCoverage` 表示证据集是否覆盖回答问题所需证据要素；
- `Redundancy` 表示证据集冗余程度。

需要通过实验回答的问题：

- Page→Region 是否优于直接全局区域检索；
- 页面召回错误和区域定位错误分别占多大比例；
- oracle-page→region 能否显著优于 predicted-page→region；
- evidence set 是否优于 single-node；
- 证据充分性特征是否真正提升 Region Hit、Evidence Set Recall 和答案支持性。

对应实验：

- page-only；
- global-region；
- oracle-page→region；
- predicted-page→region；
- single-node vs evidence-set；
- 去掉 slot coverage 的消融；
- 去掉 unit consistency 的消融；
- 去掉 redundancy penalty 的消融。

#### 创新点三：形成面向证据充分性、答案支持性与引用一致性的分层可信验证机制

普通 RAG 往往只关注生成答案是否看似正确，但文档问答场景还需要判断：

- 检索证据是否足以回答问题；
- 生成答案是否被证据支持；
- 答案引用是否指向正确页码、区域或表格行；
- 当证据不足或证据冲突时是否应该拒答。

本文将可信验证拆分为三个层次：

1. **生成前证据充分性验证**：判断 evidence set 是否覆盖回答问题所需的关键证据要素；
2. **生成后答案支持性验证**：判断答案中的关键 claim 是否能被证据支持；
3. **引用一致性验证**：判断答案引用是否指向正确页码、区域或表格证据。

不同问题类型采用不同验证策略：

- 数值型问题：验证指标、年份、单位和数值是否一致；
- 表格型问题：验证“指标—年份—单位—数值”四元组；
- 文本型问题：结合证据覆盖度、NLI 或 LLM verifier 判断支持性；
- 不可回答问题：结合检索置信度、证据要素覆盖度和 verifier 判断是否拒答。

最终输出状态建议：

- `supported`
- `partially_supported`
- `insufficient`
- `conflict`
- `citation_mismatch`
- `unanswerable`

需要通过实验回答的问题：

- 证据充分性判断能否减少无依据生成；
- 引用一致性验证能否发现错误引用；
- 拒答机制能否降低不可回答问题误答率；
- 规则验证与 LLM verifier 结合是否比单独使用 LLM-as-judge 更稳定。

### 3.6 创新点与开发任务对应关系

| 创新点 | 必须开发的功能 | 必须完成的实验 |
|---|---|---|
| 轻量级多粒度证据图 | evidence node、evidence edge、父子关系、阅读顺序、表格归属 | 粒度消融、节点类型对比、引用准确性分析 |
| 最小充分证据集检索 | global-region、oracle-page→region、evidence set、slot coverage、unit consistency、redundancy penalty | page-only、global-region、oracle-page→region、single-node vs evidence-set、充分性特征消融 |
| 分层可信验证 | evidence cards、生成前充分性验证、答案支持性验证、引用一致性验证、拒答状态 | supported/insufficient/conflict/unanswerable 统计、拒答实验、错误分析 |

开发优先级应以第二个创新点为中心，即优先完成“证据充分性感知的页面—区域—证据集层次化检索与重排序方法”。第一个创新点是数据和结构基础，第三个创新点是下游验证闭环。

## 4. 用户角色

### 4.1 研究者

主要使用者是论文作者本人。关注内容包括：

- 数据处理是否可复现；
- 检索实验是否可配置；
- 输出指标是否完整；
- 错误分析是否方便；
- 论文表格和案例是否容易导出。

### 4.2 导师和评审专家

关注内容包括：

- 研究问题是否清晰；
- 创新点是否集中；
- 实验是否能够证明方法有效；
- 对比实验和消融实验是否充分；
- 系统是否具有可复现性。

### 4.3 潜在业务用户

潜在业务用户包括投研人员、审计人员、法务人员、企业知识库管理员等。关注内容包括：

- 能否快速找到答案；
- 能否定位到原文页码和区域；
- 答案是否有证据支持；
- 证据不足时是否会拒答；
- 是否便于人工复核。

## 5. 总体架构设计

### 5.1 系统总体流程

系统总体流程如下：

```text
PDF 长文档
  -> 文档解析
  -> 页面表构建
  -> 证据节点构建
  -> 轻量级证据图构建
  -> 页面级召回
  -> 区域级检索
  -> 最小充分证据集选择
  -> evidence cards 构造
  -> 证据增强生成
  -> 分层可信验证
  -> 输出答案、证据、引用和支持状态
```

### 5.2 系统核心模块

系统划分为以下模块：

| 模块 | 主要职责 | 当前状态 |
|---|---|---|
| 数据接入模块 | 管理原始 PDF、标注文件和数据集目录 | 已有基础 |
| 文档解析模块 | 提取页面文本、文本块、bbox、页码等 | 已有基础 |
| 证据节点构建模块 | 构建 paragraph、table_block、table_row 等节点 | 已有基础 |
| 证据图构建模块 | 建立页面、章节、段落、表格等关系 | 待增强 |
| 页面召回模块 | BM25、TF-IDF、BGE-M3 页面检索 | 已有 baseline |
| 区域检索模块 | 候选页面内节点检索 | 已有 baseline |
| 证据集选择模块 | 选择最小充分 evidence set | 待实现 |
| 重排序模块 | RRF、BGE-reranker、充分性特征融合 | 部分实现 |
| 生成模块 | 基于 evidence cards 生成回答 | 待实现 |
| 可信验证模块 | 支持性、充分性、引用一致性验证 | 待实现 |
| 评估模块 | 检索、生成、可信性、效率指标评估 | 已有基础 |
| 导出模块 | 输出论文表格、案例和错误分析 | 已有基础 |

## 6. 数据设计需求

### 6.1 数据目录结构

建议项目数据目录结构如下：

```text
data/
  raw/
    cn_annual_reports/
      pdfs/
      metadata.csv
      qa_annotations.csv
      qa_annotations_v2.csv
      qa_annotations_v2_reviewed.csv
    mmdocir/
  processed/
    cn_annual_reports/
      documents.parquet
      pages.parquet
      nodes.parquet
      queries.parquet
      evidence_edges.parquet        # 后续新增
      evidence_sets.parquet         # 后续新增
  interim/
    cn_annual_reports/
      extracted_blocks/
      page_images/
      region_images/
      chart_regions/
```

### 6.2 文档表 documents.parquet

`documents.parquet` 用于保存文档级元信息。

必需字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| doc_id | string | 文档唯一编号 |
| dataset | string | 数据集名称 |
| title | string | 文档标题 |
| source_path | string | 原始文件路径 |
| file_name | string | 文件名 |
| page_count | int | 页面数量 |
| metadata | json/string | 额外元数据 |

### 6.3 页面表 pages.parquet

`pages.parquet` 用于保存页面级信息。

必需字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| page_id | string | 页面唯一编号 |
| doc_id | string | 所属文档 |
| page_index | int | 页码索引 |
| page_number | int | 人类可读页码 |
| page_text | string | 页面文本 |
| ocr_text | string/null | OCR 文本 |
| image_path | string/null | 页面图像路径 |
| metadata | json/string | 页面元数据 |

### 6.4 证据节点表 nodes.parquet

`nodes.parquet` 是系统核心数据表，用于保存多粒度证据节点。

必需字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| node_id | string | 证据节点唯一编号 |
| doc_id | string | 所属文档 |
| page_id | string | 所属页面 |
| parent_id | string/null | 父节点编号 |
| node_type | string | 节点类型 |
| text | string | 节点文本 |
| bbox | list/array/null | 页面区域坐标 |
| reading_order | int/null | 阅读顺序 |
| image_path | string/null | 区域图像路径 |
| metadata | json/string | 节点元数据 |

节点类型建议：

| node_type | 说明 |
|---|---|
| page | 页面级节点 |
| section | 章节节点 |
| title | 标题节点 |
| paragraph | 段落节点 |
| table_block | 疑似表格块节点 |
| table_row | 表格行级文本证据节点 |
| chart_region | 图表区域节点 |
| figure_region | 图片区域节点 |
| footnote | 脚注节点 |

当前阶段已经实现：

- `paragraph`
- `table_block`
- `table_row`

后续需要增强：

- `section`
- `title`
- `chart_region`
- `figure_region`

### 6.5 证据边表 evidence_edges.parquet

`evidence_edges.parquet` 用于保存轻量级证据图中的边关系，后续需要新增。

必需字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| edge_id | string | 边唯一编号 |
| source_node_id | string | 起始节点 |
| target_node_id | string | 目标节点 |
| edge_type | string | 边类型 |
| weight | float | 边权重 |
| metadata | json/string | 额外信息 |

边类型建议：

| edge_type | 说明 |
|---|---|
| contains | 包含关系，如 page contains paragraph |
| belongs_to | 归属关系，如 table_row belongs_to table_block |
| next | 阅读顺序关系 |
| previous | 阅读顺序反向关系 |
| under_title | 标题层级关系 |
| same_page | 同页关系 |
| same_section | 同章节关系 |
| evidence_pair | 多证据协同关系 |
| source_of | 来源引用关系 |

### 6.6 查询表 queries.parquet

`queries.parquet` 用于保存问题、答案和证据标注。

必需字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| query_id | string | 问题编号 |
| dataset | string | 数据集 |
| question | string | 问题文本 |
| answer | string | 标准答案 |
| answer_type | string | 答案类型 |
| evidence_pages | list | 页级证据 |
| evidence_node_ids | list | 节点级证据 |
| metadata | json/string | 额外字段 |

建议在 `metadata` 中保留：

- `question_type`
- `difficulty`
- `source_section`
- `answer_unit`
- `raw_answer_value`
- `normalized_answer`
- `value_evidence_text`
- `unit_evidence_text`
- `value_evidence_pages`
- `unit_evidence_pages`
- `required_slots`

### 6.7 证据集表 evidence_sets.parquet

`evidence_sets.parquet` 用于保存候选最小充分证据集，后续需要新增。

必需字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| evidence_set_id | string | 证据集编号 |
| query_id | string | 对应问题 |
| node_ids | list | 证据节点列表 |
| page_ids | list | 覆盖页面 |
| set_score | float | 证据集综合得分 |
| sufficiency_score | float | 证据充分性得分 |
| redundancy_score | float | 冗余度 |
| support_status | string | 支持状态 |
| metadata | json/string | 额外信息 |

## 7. 功能需求

### 7.1 数据接入功能

#### FR-001 原始 PDF 管理

系统应支持将年度报告、招股说明书、合同、政策文件等 PDF 放入指定目录。

要求：

- 支持按数据集划分原始文件目录；
- 支持读取 `metadata.csv`；
- 支持记录文件名、标题、文档类型、年份、公司名称等元数据；
- 当目录为空时给出清晰提示。

#### FR-002 标注文件读取

系统应支持读取问答标注文件。

要求：

- 支持 `.csv`、`.xlsx`；
- 优先读取人工修订版本；
- 支持旧版标注回退；
- 支持将额外字段写入 `QueryRecord.metadata`。

当前优先级建议：

```text
qa_annotations_v2_reviewed.csv
qa_annotations_v2_reviewed.xlsx
qa_annotations_v2.csv
qa_annotations_v2.xlsx
qa_annotations.csv
qa_annotations.xlsx
```

### 7.2 文档解析功能

#### FR-003 原生 PDF 文本解析

系统应使用 PyMuPDF 对原生 PDF 进行逐页解析。

输出：

- 页面文本；
- 文本块；
- 文本块 bbox；
- 页面索引；
- 页面尺寸；
- 初步阅读顺序。

#### FR-004 扫描件 OCR 解析

系统后续应支持对扫描件或图片型 PDF 使用 OCR。

可选工具：

- PaddleOCR；
- Docling OCR；
- MinerU；
- PaddleOCR-VL。

输出：

- OCR 文本；
- 字符或文本块坐标；
- OCR 置信度；
- OCR 来源标记。

#### FR-005 图表区域解析

系统后续应支持图表区域处理。

第一阶段要求：

- 记录图表区域坐标；
- 保存图表区域图像路径；
- 抽取图表标题、图注和周围文本。

第二阶段可选：

- 使用视觉语言模型生成图表描述；
- 使用图表解析模型转换为结构化表格。

### 7.3 证据节点构建功能

#### FR-006 页面节点构建

系统应为每页构建页面级记录，并写入 `pages.parquet`。

要求：

- 页面 ID 稳定；
- 重复 prepare 后 ID 可复现；
- 页面文本不能为空时优先使用原生文本；
- 如果页面无文本，则记录为空并保留后续 OCR 扩展入口。

#### FR-007 段落节点构建

系统应根据文本块、换行和阅读顺序构建段落级 evidence node。

要求：

- 节点 ID 稳定；
- 节点绑定 `doc_id` 和 `page_id`；
- 节点保留 `node_type=paragraph`；
- 节点保留文本内容和 metadata。

#### FR-008 表格块节点构建

系统应识别疑似表格文本块，构建 `table_block` 节点。

识别依据可包括：

- 同一文本块内包含多个数字；
- 包含财务关键词；
- 呈现明显行列式文本；
- 位于财务报表或主要会计数据章节。

注意：

当前阶段的 `table_block` 是表格相关文本证据节点，不等同于完整二维结构化表格。

#### FR-009 表格行节点构建

系统应针对财务指标构建 `table_row` 节点。

重点指标包括：

- 营业收入；
- 归属于上市公司股东的净利润；
- 经营活动产生的现金流量净额；
- 研发投入；
- 研发费用；
- 资产总额；
- 负债合计；
- 基本每股收益。

要求：

- 优先将包含指标名、数值、单位的行切为独立节点；
- 如果单位在表头或页面上方，应记录单位候选；
- 节点 metadata 应记录 `unit_candidates`。

#### FR-010 图表区域节点构建

系统后续应构建 `chart_region` 节点。

要求：

- 保存图表区域坐标；
- 保存图表图像路径；
- 保存图表标题、图注、周围文本；
- 如果有视觉模型输出，应保存 `chart_caption` 或 `vlm_summary`。

### 7.4 轻量级证据图构建功能

#### FR-011 节点关系构建

系统应根据文档结构构建证据节点之间的关系。

必须支持：

- 页面包含段落；
- 页面包含表格块；
- 表格块包含表格行；
- 标题包含下属段落；
- 节点之间的阅读顺序。

#### FR-012 证据图存储

系统应将证据图关系保存为 `evidence_edges.parquet`。

要求：

- 边 ID 稳定；
- 支持边类型查询；
- 支持根据节点快速找到父节点、子节点和相邻节点；
- 支持后续检索和验证阶段调用。

### 7.5 页面级召回功能

#### FR-013 BM25 页面召回

系统应支持 BM25-page baseline。

输入：

- 用户问题；
- 页面文本列表。

输出：

- Top-k 页面；
- 页面得分；
- 页面排名。

说明：

当前实现采用内存中的 `SimpleBM25`，属于词项统计和倒排检索思想的轻量实现，不是 Elasticsearch 级别的持久化倒排索引。

#### FR-014 TF-IDF 页面召回

系统应支持 TF-IDF 页面召回作为离线 fallback。

要求：

- 无需联网；
- 可复现；
- 用于模型不可用时的 baseline。

#### FR-015 向量页面召回

系统后续应支持 BGE-M3 或其他 embedding 模型。

要求：

- 支持本地模型加载；
- 支持 query embedding 和 page embedding；
- 支持余弦相似度计算；
- 支持向量缓存；
- 支持后续接入 FAISS。

### 7.6 区域级检索功能

#### FR-016 全局区域检索

系统应支持 `global-region` baseline，即不经过页面召回，直接在所有 evidence nodes 上检索。

目的：

- 评估直接区域检索的效果；
- 与页面—区域层次化检索对比；
- 判断页面召回是否带来收益。

#### FR-017 预测页面到区域检索

系统应支持 `predicted-page→region`。

流程：

1. 使用页面检索器召回 Top-k 页面；
2. 过滤候选页面下的 evidence nodes；
3. 在候选 nodes 中进行区域检索；
4. 输出 Top-k evidence nodes 或 evidence set。

#### FR-018 Oracle 页面到区域检索

系统应支持 `oracle-page→region`。

流程：

1. 直接使用 gold evidence pages；
2. 只在正确页面内做区域检索；
3. 评价区域检索上限。

目的：

- 分析错误来自页面召回还是区域排序；
- 判断区域检索模块本身是否有效。

### 7.7 证据集选择功能

#### FR-019 证据要素抽取

系统应根据问题类型抽取或定义证据要素。

财务数值类问题的必要要素：

- 指标；
- 年份；
- 单位；
- 数值；
- 公司或报告主体。

文本解释类问题的必要要素：

- 关键实体；
- 条件；
- 原因；
- 结论；
- 来源章节。

风险类问题的必要要素：

- 风险名称；
- 风险描述；
- 风险影响；
- 来源章节。

#### FR-020 证据充分性评分

系统应对候选证据节点或证据集计算充分性得分。

建议特征：

| 特征 | 说明 |
|---|---|
| semantic_similarity | 问题与节点文本相似度 |
| page_score | 所属页面召回得分 |
| node_score | 节点检索得分 |
| type_match | 问题类型与节点类型是否匹配 |
| slot_coverage | 证据要素覆盖度 |
| unit_consistency | 单位是否一致 |
| numeric_match | 数值是否匹配 |
| section_prior | 章节位置先验 |
| redundancy_penalty | 冗余惩罚 |

候选公式：

```text
EvidenceSetScore(q, S) =
  α · SemanticScore(q, S)
+ β · PagePrior(q, S)
+ γ · TypeMatch(q, S)
+ δ · SlotCoverage(q, S)
+ η · UnitConsistency(q, S)
- λ · Redundancy(S)
```

其中：

- `q` 表示问题；
- `S` 表示候选证据集；
- `SlotCoverage` 表示证据集是否覆盖回答问题所需要素；
- `Redundancy` 表示证据集冗余程度。

#### FR-021 最小充分证据集选择

系统应从候选节点中选择最小充分证据集。

定义：

- “充分”指证据集能够覆盖回答问题所需的关键要素；
- “最小”指在满足证据覆盖的前提下尽量减少冗余页面和节点数量。

输出：

- evidence_set_id；
- node_ids；
- page_ids；
- sufficiency_score；
- redundancy_score；
- evidence_set_score。

### 7.8 重排序功能

#### FR-022 RRF 排序融合

系统应支持 RRF，即 Reciprocal Rank Fusion。

公式：

```text
RRF(d) = Σ 1 / (k + rank_i(d))
```

用途：

- 融合页面排序和节点排序；
- 融合 BM25、TF-IDF、BGE 等多路检索结果；
- 避免不同检索器分数尺度不一致。

#### FR-023 学习型或模型型重排序

系统后续应支持：

- BGE-reranker；
- Cross-Encoder；
- LLM reranker。

要求：

- 支持可插拔；
- 支持与 RRF 对比；
- 支持保存 rerank 分数；
- 支持消融实验。

### 7.9 Evidence Cards 构造功能

#### FR-024 Evidence Card 结构

系统应将检索得到的 evidence set 组织为 evidence cards。

每张 evidence card 应包含：

| 字段 | 说明 |
|---|---|
| card_id | 证据卡片编号 |
| doc_id | 来源文档 |
| source_title | 文档标题 |
| page_id | 页面编号 |
| page_number | 页码 |
| node_id | 节点编号 |
| node_type | 节点类型 |
| evidence_text | 证据文本 |
| bbox | 区域坐标 |
| retrieval_score | 检索得分 |
| sufficiency_score | 充分性得分 |
| answer_unit | 单位信息 |
| citation | 引用格式 |

#### FR-025 Evidence Card 输出格式

系统应支持将 evidence cards 输出为：

- JSON；
- Markdown；
- prompt 文本；
- parquet；
- 案例分析表格。

### 7.10 证据增强生成功能

#### FR-026 证据约束生成

系统应将 evidence cards 输入生成模型，并要求模型只基于证据回答。

生成约束：

- 不得使用证据外信息；
- 必须输出引用页码；
- 财务数值问题必须保留单位；
- 若证据不足，应输出无法回答或请求二次检索。

#### FR-027 生成模型适配

系统后续应支持多种生成模型：

- Qwen；
- DeepSeek；
- GLM；
- OpenAI API；
- 本地小模型。

生成模型不作为论文主创新，而作为下游验证模块。

### 7.11 分层可信验证功能

#### FR-028 生成前证据充分性验证

系统应在生成前判断 evidence set 是否足以回答问题。

输出状态：

- `sufficient`
- `insufficient`
- `conflict`

#### FR-029 生成后答案支持性验证

系统应在生成后判断答案是否被证据支持。

数值型验证：

- 指标是否一致；
- 年份是否一致；
- 单位是否一致；
- 数值是否一致；
- 证据页码是否正确。

文本型验证：

- claim 是否被证据覆盖；
- 证据文本是否包含关键实体；
- 证据文本是否包含关键条件；
- NLI/LLM verifier 是否判断支持。

#### FR-030 引用一致性验证

系统应检查生成答案中的引用是否指向正确页码、区域或表格证据。

输出状态：

- `citation_correct`
- `citation_mismatch`
- `citation_missing`

#### FR-031 拒答机制

系统应在以下情况执行二次检索或拒答：

- 检索置信度低；
- 证据要素覆盖不足；
- 数值或单位不一致；
- 多个证据之间冲突；
- verifier 判断不支持；
- 问题不可回答。

最终状态建议：

| 状态 | 说明 |
|---|---|
| supported | 答案被证据支持 |
| partially_supported | 答案部分被支持 |
| insufficient | 证据不足 |
| conflict | 证据冲突 |
| citation_mismatch | 引用不一致 |
| unanswerable | 不可回答 |

### 7.12 实验评估功能

#### FR-032 检索指标

系统应支持：

- Page Recall@1/5/10；
- Region Hit@1/5/10；
- Evidence Set Recall@k；
- MRR；
- nDCG@k；
- Evidence Type Hit@k。

#### FR-033 生成指标

系统后续应支持：

- EM；
- F1；
- ANLS；
- Numerical Accuracy；
- Unit Accuracy；
- Citation Accuracy。

#### FR-034 可信性指标

系统后续应支持：

- Correct Answer with Correct Evidence Rate；
- Unsupported Answer Rate；
- Abstention Precision；
- Abstention Recall；
- Abstention F1；
- False Refusal Rate；
- False Answer Rate；
- Citation Mismatch Rate。

#### FR-035 效率指标

系统应记录：

- 平均检索延迟；
- P95 延迟；
- 候选页面数量；
- 候选节点数量；
- evidence set 节点数量；
- 输入 token 数；
- VLM 调用次数；
- 存储空间。

## 8. 实验设计需求

### 8.1 必须完成的 baseline

系统必须支持以下 baseline：

| Baseline | 说明 |
|---|---|
| BM25-page | 页面级关键词检索 |
| Dense-page | 页面级语义检索 |
| Global-region | 全局节点检索 |
| Layout-aware chunk retrieval | 按版面节点直接检索 |
| Predicted-page→region | 预测页面后区域检索 |
| Oracle-page→region | 正确页面内区域检索 |
| Single-node retrieval | 单节点证据检索 |
| Evidence-set retrieval | 证据集检索 |

### 8.2 必须完成的消融实验

系统必须支持以下消融实验：

| 消融项 | 目的 |
|---|---|
| 去掉页面先验 | 验证 page score 作用 |
| 去掉节点类型先验 | 验证 node_type 作用 |
| 去掉 slot coverage | 验证证据要素覆盖作用 |
| 去掉 unit consistency | 验证单位一致性作用 |
| 去掉 redundancy penalty | 验证最小证据集约束作用 |
| single-node vs evidence-set | 验证证据集选择是否优于单节点 |
| predicted page vs oracle page | 分析页面召回误差影响 |

### 8.3 必须完成的错误分析

系统必须支持对错误样本进行分类。

错误类型建议：

- 页面召回错误；
- 区域定位错误；
- 节点切分错误；
- 表格行识别错误；
- 单位识别错误；
- 证据要素缺失；
- 答案生成错误；
- 引用错误；
- 证据不足但未拒答；
- 可回答问题误拒答。

## 9. 命令行接口需求

### 9.1 已有命令

当前系统已有命令：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
uv run mdr export-demo --run runs/retrieval/cn_page_region/latest
```

### 9.2 建议新增命令

#### 构建证据图

```bash
uv run mdr build-evidence-graph --dataset cn_annual_reports
```

输出：

```text
data/processed/cn_annual_reports/evidence_edges.parquet
```

#### 构建证据集

```bash
uv run mdr build-evidence-sets \
  --dataset cn_annual_reports \
  --config configs/evidence_sets/cn_sufficiency.yaml
```

输出：

```text
data/processed/cn_annual_reports/evidence_sets.parquet
```

#### 运行证据充分性感知检索

```bash
uv run mdr retrieve \
  --config configs/experiments/cn_evidence_set_retrieval.yaml
```

#### 运行可信验证

```bash
uv run mdr verify \
  --run runs/retrieval/cn_evidence_set_retrieval/latest
```

#### 导出错误分析

```bash
uv run mdr export-errors \
  --run runs/retrieval/cn_evidence_set_retrieval/latest
```

#### 导出论文表格

```bash
uv run mdr export-paper-tables \
  --run runs/retrieval/cn_evidence_set_retrieval/latest
```

## 10. 配置文件需求

### 10.1 检索配置

示例：

```yaml
experiment_name: cn_evidence_set_retrieval
dataset: cn_annual_reports
retriever:
  type: evidence_set
  page_retriever: dense_page
  region_retriever: dense_node
  page_top_k: 10
  region_top_k: 50
  evidence_set_top_k: 5
  scoring:
    semantic_weight: 0.40
    page_weight: 0.20
    type_match_weight: 0.10
    slot_coverage_weight: 0.20
    unit_consistency_weight: 0.10
    redundancy_penalty: 0.10
evaluation:
  metrics:
    - page_recall
    - region_hit
    - evidence_set_recall
    - mrr
    - ndcg
output_dir: runs/retrieval/cn_evidence_set_retrieval
```

### 10.2 验证配置

示例：

```yaml
experiment_name: cn_verification
dataset: cn_annual_reports
verification:
  pre_generation:
    min_sufficiency_score: 0.65
    min_slot_coverage: 0.75
  post_generation:
    numeric_tolerance: 0.001
    require_unit_match: true
    require_citation: true
  verifier:
    type: rule_then_llm
    llm_model: qwen
output_dir: runs/verification/cn_verification
```

## 11. 非功能需求

### 11.1 可复现性

系统必须保证实验可复现。

要求：

- 所有实验通过配置文件运行；
- 每次运行创建时间戳目录；
- 保存运行配置；
- 保存指标结果；
- 保存预测结果；
- 保存错误分析；
- 维护 `latest` 指向最新实验。

### 11.2 可扩展性

系统应支持新增：

- 新数据集；
- 新检索器；
- 新重排序器；
- 新验证器；
- 新评价指标；
- 新导出格式。

### 11.3 可诊断性

系统应支持定位错误来源。

要求：

- 查询级输出检索结果；
- 保存 page hit 和 node hit；
- 保存 evidence set；
- 保存充分性特征分数；
- 保存验证状态；
- 支持导出错误样本。

### 11.4 离线可运行

系统应保证无网络环境下可跑基础实验。

要求：

- BM25 和 TF-IDF 必须离线可用；
- 模型不可用时自动 fallback；
- 缺失数据时给出清晰提示；
- 不把网络下载作为必需步骤。

### 11.5 性能要求

第一阶段性能目标：

- 20 份中文年报数据可在普通笔记本上完成解析和检索；
- 基础检索实验单次运行时间应在可接受范围内；
- 后续接入向量模型时应支持 embedding 缓存；
- 后续大规模数据应支持 FAISS 等索引。

## 12. 当前项目状态

### 12.1 已完成内容

当前项目已经完成：

1. Python 包结构 `src/mmdocrag`；
2. uv 项目环境；
3. CLI 基础命令；
4. demo 数据集；
5. 中文年报 PDF 逐页解析；
6. `documents.parquet`、`pages.parquet`、`nodes.parquet`、`queries.parquet`；
7. paragraph、table_block、table_row 节点构建；
8. QA 标注生成和人工修订；
9. BM25-page baseline；
10. Dense-page/TF-IDF fallback baseline；
11. Page→Region baseline；
12. 检索指标评价；
13. 开题实验结果导出；
14. 运行记录和相关说明文档。

### 12.2 当前实验数据规模

中文年报当前规模：

| 项目 | 数量 |
|---|---:|
| 年报 PDF | 20 |
| 页面 | 5327 |
| 证据节点 | 99304 |
| QA 样本 | 160 |
| 节点类型 | paragraph、table_block、table_row |

### 12.3 当前不足

当前仍需补充：

1. 证据图边关系尚未单独存储；
2. 最小充分证据集尚未实现；
3. 证据充分性评分尚未实现；
4. Direct-region 和 oracle-page→region baseline 尚未实现；
5. BGE-M3 向量检索尚未真正落地；
6. BGE-reranker 尚未接入；
7. 生成模块尚未实现；
8. 分层可信验证尚未实现；
9. 拒答实验尚未实现；
10. 图表区域和视觉检索尚未形成实验结果。

## 13. 后续开发路线

### 13.0 开题后核心必须完成事项

开题后开发不应继续扩展“大而全”的系统功能，而应优先围绕论文主贡献完成一条可验证的实验主线：

```text
轻量级证据图
  -> 页面—区域检索 baseline
  -> 最小充分证据集选择
  -> 证据充分性消融实验
  -> 分层可信验证与拒答
```

#### 必须完成 A：重新跑通并固化已有实验

目的：

确认当前代码和数据仍然可复现，并作为后续实验基准。

必须完成：

1. 重新运行 `prepare cn_annual_reports`；
2. 重新运行 `BM25-page`；
3. 重新运行 `Dense-page`；
4. 重新运行 `Page→Region`；
5. 重新导出指标表；
6. 固化当前 baseline 结果，作为后续对比起点。

验收标准：

- 四个 parquet 标准表可重新生成；
- 三类已有检索实验可运行；
- `metrics.json`、`predictions.parquet`、`summary.md` 可正常输出；
- 指标与历史结果差异在可解释范围内。

#### 必须完成 B：补齐关键检索 baseline

目的：

回答导师指出的“当前 Page→Region 只能说明流程可跑通，缺少关键对照”的问题。

必须完成：

1. `global-region`：直接在所有 evidence nodes 上检索，不经过页面召回；
2. `oracle-page→region`：使用人工标注的正确页面，只评价区域定位能力；
3. `predicted-page→region`：使用模型预测页面，再进行区域定位；
4. `single-node retrieval`：只返回单个最相关节点；
5. `evidence-set retrieval`：返回一组能够覆盖问题要素的证据节点。

验收标准：

- 每个 baseline 都有独立配置文件；
- 每个 baseline 都能输出统一格式的 `predictions.parquet`；
- 评价脚本能计算 Page Recall、Region Hit、Evidence Set Recall、MRR 和 nDCG；
- 能区分页面召回错误和区域定位错误。

#### 必须完成 C：实现证据要素与充分性特征

目的：

把论文主创新从“普通 Page→Region 检索”推进到“证据充分性感知检索”。

必须完成的问题类型：

| 问题类型 | 必要证据要素 |
|---|---|
| 财务数值类 | 指标、年份、单位、数值、来源页 |
| 表格型问题 | 指标、列名/年份、单位、单元格值 |
| 文本解释类 | 关键实体、条件、原因或结论 |
| 风险描述类 | 风险名称、风险描述、来源章节 |

必须实现的特征：

1. `type_match`：问题类型与节点类型是否匹配；
2. `slot_coverage`：证据集是否覆盖必要证据要素；
3. `unit_consistency`：单位是否一致；
4. `numeric_match`：数值是否匹配；
5. `section_prior`：证据是否位于合理章节；
6. `redundancy_penalty`：证据集是否过度冗余。

验收标准：

- 每条 query 能得到问题类型；
- 每个候选节点或 evidence set 能输出充分性特征；
- 特征分数能写入结果 metadata；
- 可导出案例查看每个 evidence set 为什么被选中。

#### 必须完成 D：实现最小充分证据集选择

目的：

回答“系统不是只检索最相似片段，而是检索能够支撑回答的证据组合”。

必须完成：

1. 从候选节点中生成候选 evidence set；
2. 计算 evidence set 的语义相关性、要素覆盖度和冗余度；
3. 选择 Top-k evidence sets；
4. 保存 `evidence_sets.parquet`；
5. 支持 `single-node vs evidence-set` 对比实验。

验收标准：

- evidence set 至少包含 `query_id`、`node_ids`、`page_ids`、`sufficiency_score`、`redundancy_score`、`set_score`；
- 能说明每个 evidence set 覆盖了哪些证据要素；
- 能评价 gold evidence node 是否被 evidence set 覆盖；
- 能证明 evidence set 相比 single-node 是否更有利于答案支持性。

#### 必须完成 E：完成消融实验和错误分析

目的：

证明各个充分性特征是否真的有效，避免只做系统展示。

必须完成的消融：

1. 完整方法；
2. 去掉 `page_score`；
3. 去掉 `type_match`；
4. 去掉 `slot_coverage`；
5. 去掉 `unit_consistency`；
6. 去掉 `redundancy_penalty`；
7. single-node 替代 evidence-set；
8. predicted-page 替代 oracle-page。

必须完成的错误分析：

- 页面没召回；
- 页面召回正确但区域定位错误；
- 区域节点切分不合理；
- 表格行没抽准；
- 单位识别错误；
- evidence set 缺少关键要素；
- 证据冗余过多；
- gold 标注不完善。

验收标准：

- 有完整对比表；
- 有消融实验表；
- 有错误类型统计；
- 有 5-10 个典型案例分析；
- 能回答“方法提升来自哪个模块”。

#### 必须完成 F：最小可信验证闭环

目的：

不追求第一时间完成复杂生成系统，但必须让检索结果和可信验证衔接起来。

必须完成：

1. evidence cards 构造；
2. 生成前证据充分性判断；
3. 数值和单位一致性规则验证；
4. 引用页码和节点一致性验证；
5. `supported`、`insufficient`、`conflict`、`citation_mismatch` 状态输出；
6. 对部分问题进行拒答实验。

验收标准：

- 对财务数值类问题能自动判断数值和单位是否被证据支持；
- 对证据不足样本能输出 `insufficient`；
- 对引用错误样本能输出 `citation_mismatch`；
- 能导出可信验证统计表。

#### 暂缓实现事项

以下内容不作为开题后第一阶段开发重点：

1. 大规模 ColPali / ColQwen 视觉检索；
2. ViDoRe V3 全量实验；
3. OmniDocBench 解析评测；
4. 完整 LangChain 工程化 Agent；
5. 大规模 LLM verifier 自动评测；
6. 完整图表数值抽取；
7. 复杂前端系统。

这些内容可以作为论文后期扩展、案例分析或未来工作，不应影响检索主线完成。

### 13.1 第一轮：检索主线增强

目标：

完成论文主贡献所需的检索实验。

任务：

1. 新增 `global-region` baseline；
2. 新增 `oracle-page→region` baseline；
3. 新增 `layout-aware chunk retrieval` baseline；
4. 实现证据要素抽取；
5. 实现 slot coverage；
6. 实现 unit consistency；
7. 实现 evidence set 选择；
8. 完成充分性特征消融实验；
9. 导出新的实验表格和错误分析。

### 13.2 第二轮：强模型与公开数据集

目标：

提升实验说服力。

任务：

1. 接入 BGE-M3；
2. 接入 BGE-reranker；
3. 增加 embedding 缓存；
4. 适配 MMDocIR；
5. 在中文年报和 MMDocIR 上进行对比实验；
6. 分析不同数据集上的效果差异。

### 13.3 第三轮：可信验证与拒答

目标：

形成可信生成验证闭环。

任务：

1. 实现 evidence cards；
2. 实现基于证据的生成 prompt；
3. 实现数值一致性验证；
4. 实现单位一致性验证；
5. 实现引用一致性验证；
6. 实现二次检索；
7. 实现拒答状态输出；
8. 完成可信性指标评价。

### 13.4 第四轮：视觉与图表扩展

目标：

补充多模态能力。

任务：

1. 保存页面图像；
2. 保存区域图像；
3. 构建 chart_region 节点；
4. 接入页面视觉检索模型；
5. 选择小规模图表案例进行分析；
6. 在论文中作为扩展实验或案例分析呈现。

## 14. 验收标准

### 14.1 第一阶段验收标准

第一阶段完成时，应满足：

1. `prepare` 可稳定生成四类标准 parquet；
2. `nodes > pages`；
3. BM25-page、Dense-page、Page→Region 可运行；
4. global-region、oracle-page→region 可运行；
5. evidence set 检索可运行；
6. 能输出 Page Recall、Region Hit、Evidence Set Recall；
7. 能导出错误分析；
8. 能说明页面召回错误和区域定位错误的比例。

### 14.2 第二阶段验收标准

第二阶段完成时，应满足：

1. BGE-M3 可用于页面或节点 embedding；
2. BGE-reranker 可用于候选证据重排序；
3. 消融实验完整；
4. 中文年报实验表格完整；
5. 至少一个公开数据集完成基本实验；
6. 论文方法有效性有实验证据支撑。

### 14.3 第三阶段验收标准

第三阶段完成时，应满足：

1. evidence cards 可生成；
2. 生成回答可输出引用；
3. 数值和单位一致性验证可运行；
4. 引用一致性验证可运行；
5. 拒答机制可运行；
6. 可信性指标可计算；
7. 有典型案例分析。

## 15. 风险与应对措施

### 15.1 范围过大风险

风险：

系统涉及解析、检索、生成、验证和视觉模块，范围容易过大。

应对：

以检索为主贡献，可信验证作为第二阶段，视觉检索作为扩展实验。

### 15.2 视觉检索落地困难风险

风险：

ColPali、ColQwen 等视觉检索模型可能受显存、模型下载和运行环境限制。

应对：

第一阶段以文本和版面结构检索为主；视觉检索仅作为小规模扩展或案例分析。

### 15.3 数据标注不足风险

风险：

区域级证据和不可回答问题标注成本较高。

应对：

优先保证中文年报核心问题类型；采用规则辅助标注和人工抽样复核；公开数据集用于补充评估。

### 15.4 可信验证不稳定风险

风险：

LLM verifier 判断可能不稳定。

应对：

数值和表格问题优先使用规则验证；文本问题采用证据覆盖度、NLI/LLM verifier 和人工抽样复核结合。

### 15.5 解析错误影响实验风险

风险：

PDF 解析错误可能导致后续检索失败。

应对：

将错误分析拆分为解析错误、切分错误、检索错误、生成错误和验证错误，避免误判方法效果。

## 16. 论文写作对应关系

系统模块与论文章节的对应关系建议如下：

| 系统模块 | 论文章节 |
|---|---|
| 文档解析与数据标准化 | 第三章 |
| 多粒度证据图表示 | 第三章 |
| 页面—区域—证据集检索 | 第四章 |
| 证据充分性评分 | 第四章 |
| 可信验证与拒答 | 第五章 |
| 实验评估与错误分析 | 第六章 |

论文主线建议：

```text
证据图表示
  -> 最小充分证据集检索
  -> 分层可信验证
  -> 对比实验、消融实验、错误分析
```

## 17. 术语说明

| 术语 | 说明 |
|---|---|
| evidence node | 证据节点，表示页面、段落、表格行等证据单元 |
| evidence graph | 由证据节点及其关系构成的轻量级证据图 |
| evidence set | 为回答某个问题选择的一组证据节点 |
| minimum sufficient evidence set | 最小充分证据集，指覆盖回答要素且冗余较少的证据组合 |
| evidence card | 面向生成模型的结构化证据卡片 |
| Page Recall | 页级证据召回率 |
| Region Hit | 区域级证据命中率 |
| Slot Coverage | 证据要素覆盖度 |
| Citation Accuracy | 引用准确率 |
| Refusal | 证据不足时拒答 |

## 18. 总结

本系统的核心不是简单搭建一个完整 RAG 应用，而是围绕长文档问答中的“证据是否足够、证据是否可定位、答案是否被支持”展开实验系统设计。后续开发应优先保证检索主线可验证，即完成轻量级证据图、页面—区域—证据集检索、最小充分证据集选择和充分性消融实验。在此基础上，再扩展证据增强生成、分层可信验证和多模态视觉检索。

一句话概括系统目标：

> 将 PDF 长文档从普通文本切块转化为可检索、可引用、可验证的证据图，并从中检索最小充分证据集，支撑可信问答和拒答决策。
