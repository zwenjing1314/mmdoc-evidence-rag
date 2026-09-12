# 关于可信性实验、RAG 和论文工作量的疑问解答

本文记录一个非常关键的问题：

> 可信性实验到底要用什么模型或技术？要不要用 RAG？为什么现在感觉不到技术和可研究的东西？这个开题方向能不能支撑毕业大论文工作量？

这个问题很重要，因为它关系到论文后续到底是“普通工程项目”，还是“有实验、有对比、有研究问题的硕士论文”。

## 1. 先给结论

这个开题方向本身没有废，也不是不能做。

它可以支撑毕业论文，但前提是不能只停留在：

```text
搭一个 RAG 系统
调用一个大模型回答问题
```

而要把它做成：

```text
围绕多模态长文档证据检索、证据定位、证据支持性判断和拒答机制的实验研究
```

也就是说，论文的重点不是“我做了一个问答 Demo”，而是：

```text
不同证据粒度、不同检索策略、不同验证机制，会如何影响答案的正确性、证据的正确性和无依据回答风险？
```

只要实验设计围绕这个问题展开，它就是有研究价值的。

## 2. 为什么现在会感觉“没技术含量”

当前项目已经完成的内容主要是：

```text
项目结构
环境配置
数据目录
demo 流程
parquet 标准表
中文年报初步 QA 标注
基础检索 CLI
```

这些都是地基。

地基本身不会让人立刻感觉“论文味很浓”，因为它们更多是工程准备工作。

真正开始体现研究性的部分还没有完全展开，主要包括：

```text
MMDocIR 真实数据标准化
检索方法对比
区域级证据定位实验
答案生成实验
证据支持性验证
证据不足拒答
消融实验
错误分析
```

所以你现在的感觉是正常的：

```text
不是题目没有技术含量，
而是项目目前还处在数据接入和 baseline 阶段，
还没有进入核心实验比较阶段。
```

## 3. 可信性实验要不要用 RAG

要用。

你的可信性实验是建立在 RAG 之上的。

如果没有 RAG，就没有：

```text
检索证据
证据引用
证据是否支持答案
证据不足是否拒答
```

普通问答模型只输出答案，很难判断它到底依据了什么。

而 RAG 的核心流程是：

```text
用户问题
  ↓
检索外部文档证据
  ↓
把证据交给大模型
  ↓
生成答案
```

你的论文不是简单使用 RAG，而是要研究：

```text
Evidence-centered RAG
```

也就是“以证据为中心”的 RAG。

## 4. 普通 RAG 和你的 RAG 有什么区别

普通 RAG 通常是：

```text
PDF 转文本
  ↓
固定长度切 chunk
  ↓
向量检索
  ↓
LLM 生成答案
```

它的问题是：

1. 表格结构可能丢失。
2. 图表区域可能丢失。
3. 页码和区域位置不清楚。
4. 答案看似正确，但引用证据可能错误。
5. 证据不足时模型仍然可能强行回答。

你的方法应该是：

```text
PDF / 长文档
  ↓
页面、段落、表格、图表、bbox 等多粒度证据节点
  ↓
页面级粗召回
  ↓
区域级细定位
  ↓
Evidence Cards
  ↓
基于证据生成答案
  ↓
证据充分性判断
  ↓
答案支持性判断
  ↓
回答 / 二次检索 / 拒答
```

这就不是普通 RAG 了，而是：

```text
带证据定位和可信验证闭环的多粒度文档 RAG
```

## 5. 可信性实验要用什么模型或技术

可信性实验不一定要训练新模型。

硕士论文完全可以使用现有模型和工具，重点研究：

```text
如何组织证据
如何检索证据
如何验证答案是否被证据支持
如何在证据不足时拒答
```

可以用到的技术包括下面几类。

## 6. 技术一：Text-only RAG

这是最基础的 baseline。

流程：

```text
PDF 文本 / OCR 文本
  ↓
文本切块
  ↓
BM25 或向量检索
  ↓
LLM 回答
```

作用：

```text
作为普通 RAG 基线，用来证明你的多粒度证据方法是否更好。
```

它回答的问题是：

> 如果只用普通文本 chunk，效果如何？

## 7. 技术二：Page-only RAG

流程：

```text
问题
  ↓
召回相关页面
  ↓
把页面文本交给 LLM
  ↓
生成答案
```

作用：

```text
作为页面级证据基线。
```

它回答的问题是：

> 只找到正确页面，不定位具体区域，是否足够支持可信回答？

## 8. 技术三：Page -> Region Evidence RAG

这是你论文的核心方法之一。

流程：

```text
问题
  ↓
页面级粗召回
  ↓
候选页面内区域级检索
  ↓
返回段落 / 表格 / 图表 / bbox
  ↓
组织 Evidence Cards
  ↓
生成答案
```

作用：

```text
减少整页上下文冗余，提高证据定位精度。
```

它回答的问题是：

> 页面-区域两阶段检索是否比只做页面检索更能找到正确证据？

## 9. 技术四：Evidence Cards

Evidence Card 是证据卡片。

它不是模型，而是一种证据组织方式。

每个 evidence card 可以包含：

```text
query_id
evidence_id
doc_id
page_id
node_id
node_type
bbox
evidence_text
score
source
```

示例：

```json
{
  "query_id": "q001",
  "evidence_id": "docA_p10_table2",
  "page_id": "docA_p10",
  "node_type": "table",
  "bbox": [80, 120, 520, 360],
  "text": "营业收入 17,949,195,361.73 元",
  "score": 0.87
}
```

作用：

```text
让 LLM 不是直接面对一大段混乱文本，
而是面对结构化、可引用、可定位的证据。
```

## 10. 技术五：规则校验

规则校验特别适合数值型问题。

例如问题是：

```text
三安光电 2025 年营业收入是多少？
```

生成答案是：

```text
17,949,195,361.73 元
```

规则可以检查：

1. 这个数字是否出现在 evidence text 中。
2. 单位是否一致。
3. 证据页是否是标注页。
4. 答案是否和证据中的候选数字匹配。

这种方法不需要训练模型，但很实用。

它能降低：

```text
答案正确但证据不支持
证据正确但模型抄错数字
证据不足仍强行回答
```

## 11. 技术六：LLM-as-Judge 支持性判断

可以使用大语言模型做支持性判断。

输入：

```text
Question
Evidence
Answer
```

输出：

```text
supported
unsupported
insufficient
conflicting
```

示例 prompt：

```text
你是一个证据核查器。
请判断给定答案是否能被证据直接支持。

问题：三安光电2025年营业收入是多少？
证据：营业收入 17,949,195,361.73 元。
答案：三安光电2025年营业收入为17,949,195,361.73元。

请输出：
1. supported / unsupported / insufficient / conflicting
2. 简短理由
```

作用：

```text
判断答案是否真的被证据支持。
```

注意：

LLM-as-Judge 本身也可能不稳定，所以论文里最好配合：

```text
规则校验 + LLM 判断 + 人工抽样复核
```

这样更可信。

## 12. 技术七：证据充分性判断

答案支持性判断问的是：

```text
答案是否被当前证据支持？
```

证据充分性判断问的是：

```text
当前证据是否足够回答这个问题？
```

两者不同。

例如：

```text
问题：公司 2025 年营业收入和归母净利润分别是多少？
```

如果只检索到营业收入，没有检索到归母净利润，那么：

```text
证据不足
```

这时不应该强行回答完整问题。

系统应该：

```text
二次检索
或
拒答
或
回答部分信息并声明缺少证据
```

## 13. 技术八：拒答机制

拒答机制是可信生成的重要部分。

普通 RAG 很容易出现：

```text
没找到证据，但模型仍然编一个答案
```

你的方法应该允许系统输出：

```text
当前证据不足，无法可靠回答。
```

或者：

```text
未在检索证据中找到支持该结论的信息。
```

这就是“可信”的体现。

拒答机制可以基于：

1. 检索分数低。
2. 没有命中证据页。
3. 答案数字不在证据中。
4. LLM 判断为 insufficient / unsupported。
5. 多条证据互相冲突。

## 14. 可信性实验可以怎么设计

可以设计下面几组方法：

| 方法 | 描述 |
|---|---|
| Text-only RAG | 普通文本切块检索生成 |
| Page-only RAG | 只召回页面作为证据 |
| Page -> Region RAG | 页面召回后定位区域证据 |
| Page -> Region + Rule Verify | 加入数值/文本规则校验 |
| Page -> Region + LLM Verify | 加入 LLM 支持性判断 |
| Ours Full | 检索、证据卡片、规则校验、LLM 判断、拒答机制 |

这样你就不是只做一个系统，而是在比较不同机制的效果。

## 15. 可信性实验指标

可以使用这些指标：

```text
Answer Accuracy
Evidence Accuracy
Correct Answer with Correct Evidence Rate
Unsupported Answer Rate
Abstention Precision
Abstention Recall
Abstention F1
False Refusal Rate
False Answer Rate
```

解释如下：

| 指标 | 含义 |
|---|---|
| Answer Accuracy | 答案是否正确 |
| Evidence Accuracy | 引用证据是否正确 |
| Correct Answer with Correct Evidence Rate | 答案和证据是否同时正确 |
| Unsupported Answer Rate | 无证据支持却回答的比例 |
| Abstention Precision | 拒答中有多少是真的应该拒答 |
| Abstention Recall | 应该拒答的问题中有多少被拒答 |
| Abstention F1 | 拒答综合指标 |
| False Refusal Rate | 明明能答却拒答的比例 |
| False Answer Rate | 不该答却答错或编造的比例 |

这些指标能够把“可信”从口号变成可测量的实验结果。

## 16. 可以做的一张核心实验表

论文中可以有这样一张表：

| 方法 | 答案正确率 | 证据正确率 | 答案和证据同时正确 | 无依据回答率 | 拒答 F1 |
|---|---:|---:|---:|---:|---:|
| Text-only RAG | | | | | |
| Page-only RAG | | | | | |
| Page -> Region RAG | | | | | |
| Page -> Region + Rule Verify | | | | | |
| Page -> Region + LLM Verify | | | | | |
| Ours Full | | | | | |

这张表一出来，论文就会有明显的研究味。

## 17. 毕业论文工作量够不够

够。

但工作量不能只靠：

```text
写代码调用模型
```

而要体现在：

1. 数据标准化。
2. 多粒度证据构建。
3. 多种检索方法对比。
4. 生成方法对比。
5. 可信验证机制。
6. 拒答机制。
7. 消融实验。
8. 错误分析。

如果做完整，工作量完全够硕士毕业论文。

## 18. 最小毕业版本应该包含什么

至少包括：

### 18.1 数据处理

```text
MMDocIR 标准化
中文年报小数据集
documents/pages/nodes/queries 四张表
```

### 18.2 检索实验

```text
BM25-page
Dense-page
Layout-node
Page -> Region
Hybrid
```

指标：

```text
Recall@k
MRR
nDCG
Region Hit
```

### 18.3 生成实验

```text
Text-only RAG
Page-only RAG
Page -> Region Evidence RAG
```

指标：

```text
答案正确率
证据正确率
答案+证据同时正确率
```

### 18.4 可信性实验

```text
无验证 RAG
规则验证
LLM 支持性判断
证据不足拒答
```

指标：

```text
Unsupported Answer Rate
Abstention Precision / Recall / F1
False Refusal Rate
Correct Answer with Correct Evidence Rate
```

### 18.5 案例分析

至少分析：

```text
成功案例
错误证据案例
答案正确但引用错误案例
证据不足但模型强答案例
拒答正确案例
拒答错误案例
```

## 19. 开题报告应该怎么改表达

不要只写：

```text
本文拟构建一个框架。
```

要写得更实：

```text
目前已完成数据集接入、统一数据结构设计、中文年报初步问题标注和检索实验平台最小闭环。后续将在 MMDocIR 和中文年报数据上，比较不同证据粒度、检索策略和可信验证机制对答案可靠性与证据正确性的影响。
```

这样老师会更容易接受。

## 20. 当前项目下一步应该做什么

最重要的三步：

### 第一步：精修 MMDocIR adapter

目标：

```text
准确生成 documents/pages/nodes/queries
```

特别是：

```text
queries.parquet 的 evidence_page_ids
queries.parquet 的 evidence_bboxes
nodes.parquet 的 node_type / bbox / text
```

### 第二步：跑第一张真实检索结果表

先跑：

```text
BM25-page
Page -> Region
```

比较：

```text
Page Recall@k
MRR
nDCG
Region Hit@k
```

### 第三步：做可信性小闭环

先做简单但有效的版本：

```text
答案数字是否出现在证据中
证据是否包含问题关键词
LLM 判断 answer 是否 supported
证据不足时拒答
```

这三步做完，论文核心就会变得清楚。

## 21. 最终一句话总结

这个开题方向是可以做的。

它的研究价值不在于“调用一个 RAG 框架”，而在于：

```text
如何在多模态长文档中找到正确证据、
如何定位证据区域、
如何让答案被证据支持、
如何在证据不足时拒答。
```

只要把这些做成实验表、消融实验和案例分析，就能支撑毕业论文工作量。

