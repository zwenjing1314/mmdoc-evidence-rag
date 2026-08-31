# 从 ColPali 复现到毕业论文：研究问题与验证路线

## 1. 本文档回答什么

本毕业论文不是“复现 ColPali”，也不是“把 OCR、VLM 文本和布局框全部输入一个模型”。

论文的研究主线是：以 ColPali 为视觉页面检索基线，分析其在长文档证据检索中的任务边界；再利用 MMDocIR 提供的页面和布局区域标注，验证结构感知的多粒度检索是否能改善页面检索后的证据定位。

本文档将以下三类内容严格分开：

| 类别 | 含义 |
| --- | --- |
| 已完成事实 | 已运行、已记录、可复查的工作 |
| 架构事实 | 从 ColPali 原始设计可以直接得出的任务边界 |
| 研究假设 | 需要通过 MMDocIR 实验验证，不能预先当作结论 |

## 2. 已完成的 ColPali 复现是什么

已完成的是 ColPali **预训练模型的推理和评测复现**，不包括从头训练。

```text
官方代码 + vidore/colpali checkpoint
+ ViDoRe V1 测试集 + 官方评测工具
-> 页面检索结果与 nDCG@5 等指标
```

已获得的事实：

1. `vidore/colpali` 能在 RTX 3080 Ti 上完成页面图片编码、query 编码和 MaxSim 打分。
2. 已在 ViDoRe V1 的 10 个测试集完成全量评测，宏平均 nDCG@5 为 80.00%。
3. 该结果接近官方 README 列出的 81.3；具体环境、命令和分项指标已记录在 `docs/reproduction/`。

这一步的意义不是获得自己的创新，而是确认以下基础能力可用：

```text
页面图片 -> 多个视觉 patch 向量
query 文本 -> 多个文本 token 向量
MaxSim -> 页面相关性排序
```

因此，ColPali 是本研究的**视觉页面检索 baseline 和候选视觉主干**。

## 3. ColPali 给出的启发与任务边界

ColPali 证明：不必先把文档完全转为 OCR 文本；页面图片本身可用于检索，并能保留表格、图像和排版等视觉信息。

但其原始任务单位是“页面”。对于一个 query 和一个 page，模型输出一个页级相关性分数：

```text
query + page image -> one page score
```

原始 ColPali 的视觉 patch 会平铺参与 MaxSim。它没有显式建模：

```text
哪些 patch 属于同一个段落、表格或图像？
哪个区域才是支持答案的证据？
区域的类型、坐标、面积和阅读顺序是什么？
区域的 OCR 或 VLM 文本应怎样参与检索？
```

这不是说 ColPali “做错了”，而是其原始论文要解决的是视觉**页面检索**，并未把“结构化区域证据定位”作为核心输出任务。

## 4. 待验证的问题

本论文的候选研究问题是：

> 在长文档检索中，视觉页面检索虽然可以召回包含答案的页面，但无结构的 patch 级匹配可能无法稳定区分页面内真正的证据区域与标题、页眉、其他相似数字或无关表格。能否利用已有布局节点，把视觉 patch 组织为具有语义边界的区域表示，从而同时提高页面检索和区域级证据定位？

尚未验证的研究假设包括：

| 编号 | 假设 | 需要怎样验证 |
| --- | --- | --- |
| H1 | ColPali 在 MMDocIR 中存在“正确页 Top-K 命中，但正确区域未有效定位”的案例 | 对照页面 gold 和 layout-region gold |
| H2 | 将视觉 patch 按 layout box 聚合为区域向量，能改善区域级检索 | ColPali 与区域聚合版本对比 |
| H3 | 区域类型和空间位置等结构信息能进一步减少干扰区域 | 加/去结构编码的消融实验 |
| H4 | OCR/VLM 区域文本可补足纯视觉表示的细粒度语义 | 加/去区域文本融合的消融实验 |

若 H1 不成立，或后续模块不能带来稳定收益，就必须修改研究主张；不能为了预设网络强行解释结果。

## 5. 为什么用 MMDocIR 验证

ViDoRe V1 用于复现 ColPali 的原始页面检索能力，但它无法充分验证“页面内哪个区域是证据”。MMDocIR 同时提供以下信息：

| MMDocIR 信息 | 在本论文中的作用 |
| --- | --- |
| 长文档与多页页面库 | 验证长文档页面检索 |
| 页面图片 | 保留视觉检索输入 |
| 页面 gold | 评价是否找对页面 |
| layout box 与区域类型 | 定义段落、表格、图像等候选证据区域 |
| layout-region gold | 评价是否定位到正确证据区域 |
| OCR/VLM 页面或节点文本 | 提供区域语义增强候选信息 |
| 问题类型和文档领域 | 分析文本、表格、图像、布局、跨页问题的差异 |

因此，MMDocIR 与 ColPali 的关联是：

```text
ColPali 提供页级视觉检索能力。
MMDocIR 提供检验页级检索之后能否找到区域证据的标注。
```

MMDocIR 不用于证明 ColPali 论文有错误，而是用于证明：在更复杂的长文档证据检索任务中，原始页级视觉检索是否存在可由结构信息弥补的缺口。

## 6. 预期错误案例是什么

以下是需要从 MMDocIR 实验中统计和展示的四类现象：

| 类型 | 页面检索 | 区域定位 | 对研究的意义 |
| --- | --- | --- | --- |
| A | 正确页命中 | 正确区域命中 | ColPali 已足够的样例 |
| B | 正确页命中 | 正确区域未命中 | 结构区域模块最直接的动机 |
| C | 正确页未命中，但文本节点方法命中 | 区域可能命中 | 说明 OCR/VLM 文本可能需要参与融合 |
| D | 页面和区域均未命中 | 均失败 | 需要分析 query、视觉质量或跨页证据问题 |

尤其是 B 类案例。例如一个问题的 gold 是“第 12 页中间的财务表格”，ColPali 可能将第 12 页排入 Top-5，但该页的分数由标题、页眉、其他数字或相似表格 patch 驱动。原始模型无法指出真正的表格区域，也无法用区域 gold 衡量这个缺口。

## 7. 候选方法：结构引导的分层多粒度检索

以下是候选设计，不是已经证明有效的最终网络。

```text
query
  -> query token vectors Q

page image
  -> frozen ColPali patch vectors P

layout boxes
  -> Patch-to-Region Aggregation
  -> region visual vectors R

region type / bbox / reading order
  -> Structure Encoding
  -> structure-aware vectors R'

optional OCR / VLM node text
  -> Region Semantic Fusion
  -> enriched vectors R''

page-level MaxSim(Q, P)
region-level MaxSim(Q, R'')
  -> Page-Region Hierarchical Fusion
  -> ranked pages + ranked evidence regions
```

信息不是一次性拼接输入，而是各司其职：

| 输入 | 作用 |
| --- | --- |
| 页面图片 | 表格线、字体、图像、颜色、相对位置等视觉证据 |
| ColPali patch | 页级视觉多向量基础表示 |
| layout box | 将无结构 patch 对齐为段落、表格、图像等区域 |
| 节点类型、坐标、顺序 | 建模区域结构关系 |
| OCR 文本 | 精确文字语义补充 |
| VLM 文本 | 图像或表格等非纯文字区域的语义补充 |

第一版只应实现最小链路：

```text
冻结 ColPali
-> patch 按 layout box 聚合为 region vector
-> query-region MaxSim
-> 融合页级和区域级分数
```

OCR/VLM 融合、训练型结构编码和更强 VLM 主干都应在最小链路的诊断结果出来后再决定。

## 8. 实验如何证明研究主张

### 8.1 基线诊断

在 MMDocIR 的相同 query、相同候选页面、相同 gold 下比较：

```text
BM25-page
BGE-M3 Dense-page
Hybrid-page
ColPali-page
```

输出：页级指标、区域命中统计、四类错误案例，以及按文本/表格/图像/布局/跨页问题分组的结果。

### 8.2 方法比较

| 实验组 | 要证明什么 |
| --- | --- |
| ColPali | 原始视觉页级 baseline |
| ColPali + Region Aggregation | layout box 聚合是否有效 |
| + Structure Encoding | 坐标、类型、顺序是否有效 |
| + Page-Region Fusion | 两层分数融合是否有效 |
| + OCR/VLM Fusion | 区域文本是否提供额外价值 |
| Full model | 组合效果与代价 |

### 8.3 指标

| 层级 | 核心指标 |
| --- | --- |
| 页面级 | Recall@1、Recall@5、nDCG@5、MRR |
| 区域级 | Region Recall@1、Region Recall@5、Region MRR |
| 证据集 | 多页/多区域问题的覆盖率或现有 sufficiency 指标 |
| 分组分析 | 文本、表格、图像、布局、跨页、不同领域 |

可接受的研究结果不只有“所有指标都提高”：

```text
页级和区域级均提升：支持完整主张。
页级持平、区域级提升：支持“改善证据定位”的主张。
仅表格/图像类提升：形成有边界的多模态场景结论。
无稳定提升：修改模块或缩小研究问题。
```

## 9. 数据与训练边界

当前本地 MMDocIR 是 evaluation set。不能用同一批 gold 标注训练、调模块参数，再将同一批数据作为最终测试结果。

因此第一版优先采取：

```text
冻结 ColPali + 无训练或固定规则的结构区域聚合与分数融合。
```

若后续训练轻量结构模块，必须先获得独立训练来源或建立严格的文档级 train/dev/test 划分，并将训练、模型选择和最终测试彻底隔离。

## 10. 当前下一步

现在不开始写完整自定义网络，也不急于加入 ColQwen2。按以下顺序推进：

1. 在 Windows GPU 机器上跑通主项目中的 ColPali MMDocIR smoke test。
2. 用相同数据设置获得 BGE-M3、Hybrid、ColPali 的页级结果。
3. 基于页面与区域 gold，统计 A/B/C/D 四类错误案例。
4. 只有确认 B 类或 C 类错误有稳定比例后，确定自己的最小结构模块。
5. 再画正式网络图、定义打分公式和消融实验。

这条路线的核心不是先凑出一个复杂网络，而是让每个模块都对应一个可观察、可量化的 ColPali 任务缺口。
