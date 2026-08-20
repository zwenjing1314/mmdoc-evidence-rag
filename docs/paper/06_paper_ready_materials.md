# 小论文图表与结果材料

本文件将已完成实验整理为论文可直接使用的图、表和结论。主任务为：**面向中文年报问答的充分性感知多粒度证据集检索**。MMDocIR 只作为公开集外部检索验证，不宣称当前系统完成了通用视觉问答或跨文档检索。

## 图 1：方法架构图

图源文件：`artifacts/figures/evidence_set_region_architecture.mmd`。

建议图注：

> **Figure 1. Evidence Set Region retrieval framework.** The method fuses hybrid page retrieval, global region retrieval, and structured candidate extraction. A coverage-aware greedy selector composes a compact evidence set for a question's required semantic slots, followed by evidence sufficiency verification.

图中对应实现模块：

| 图中模块 | 代码职责 |
| --- | --- |
| Hybrid page retrieval | BM25 与 Dense 页级检索的 RRF 融合 |
| Global region retrieval | 在同一文档的全部节点中直接检索 |
| Structured candidate extraction | 数值扫描和封面锚点候选 |
| Coverage-aware selection | 按指标、年份、数值、单位、引用槽位选择紧凑证据集 |
| Sufficiency verification | 检查所需信息项覆盖与引用一致性 |

## 表 1：中文年报冻结测试主结果

数据：4 家公司、32 个问题；正式结果见 `03_test_results.md`。

| 方法 | Page R@5 | MRR | nDCG@5 | Region Hit@5 |
| --- | ---: | ---: | ---: | ---: |
| BM25-page | 0.4375 | 0.2657 | 0.2941 | - |
| Dense-page | 0.4062 | 0.2730 | 0.2919 | - |
| Hybrid-page | 0.5938 | 0.3351 | 0.3850 | - |
| Page -> Region | 0.3750 | 0.1208 | 0.0924 | 0.2500 |
| Hybrid-Page -> Region | 0.5312 | 0.0885 | 0.0615 | 0.1875 |
| Global-Region | 0.1250 | 0.0859 | 0.0567 | 0.1250 |
| **Evidence Set Region** | **0.8750** | **0.6104** | **0.4487** | **0.8750** |

建议表注：页面方法不输出布局节点，故区域指标不适用。完整方法在 Page R@5、MRR、nDCG@5 与 Region Hit@5 上均优于可部署基线。

## 表 2：充分性与关键消融

| 方法 | Region Hit@5 | Sufficiency Rate | Required Item Coverage |
| --- | ---: | ---: | ---: |
| Full Evidence Set | 0.8750 | **0.8750** | **0.9688** |
| w/o Hybrid-page | 0.8438 | 0.8125 | 0.9531 |
| w/o Global-region | 0.8750 | 0.8750 | 0.9688 |
| w/o Numeric Scan | 0.6875 | 0.6250 | 0.9219 |
| w/o Slot Coverage | **0.9375** | 0.4375 | 0.8203 |
| Single-node | **0.9375** | 0.5000 | 0.8359 |

核心论点：只优化单节点命中会提高 Region Hit@5，却显著降低证据充分率；因此充分证据集不是“命中一个相关节点”的同义词。

## 表 3：MMDocIR 外部验证

| 方法 | Page R@5 | Page R@10 | MRR | nDCG@5 |
| --- | ---: | ---: | ---: | ---: |
| BM25-page | 0.7521 | 0.8456 | 0.6084 | 0.6060 |
| Dense-page (BGE-M3) | 0.7304 | 0.8263 | 0.5732 | 0.5708 |
| Hybrid-page (BM25 + BGE-M3) | **0.7600** | **0.8727** | **0.6143** | **0.6083** |
| Dense layout-node (BGE-M3) | 0.7485 | 0.8317 | 0.3772 | 0.3714 |

布局节点方法额外获得 `Region Hit@5=0.5044`、`Region MRR=0.3719`，其区域级指标只在 1,598 个有精确布局金标的问题上计算。

## 表 4：公开集问题类型分析摘要

| 类型 | 问题数 | 最佳 Page R@5 | Layout-node Region Hit@5 | 解释 |
| --- | ---: | ---: | ---: | --- |
| text | 502 | 0.8924 (BM25) | 0.7377 | 文本与布局定位最稳定 |
| figure/chart | 433 | 0.7714 (Hybrid) | 0.3259 | 页面可定位，但视觉语义节点难定位 |
| multimodal | 327 | 0.8165 (Hybrid) | 0.4677 | 融合页级信号有效 |
| table | 183 | 0.7923 (Dense) | 0.4475 | 表格拆分与计算仍是限制 |
| metadata/web | 154 | 0.6364 (Layout-node) | 0.3961 | 元数据和版式信息较关键 |

完整分层数据见 `05_mmdocir_question_type_analysis.md`。

## 论文中的结论句

1. 充分性感知的 Evidence Set Region 在冻结中文年报测试上取得 0.8750 的 Sufficiency Rate，相比单节点选择的 0.5000 更能支持可验证回答。
2. 数值扫描和槽位覆盖是充分性提升的关键；去除数值扫描使充分率降至 0.6250，移除槽位覆盖虽提升单节点命中，却将充分率降至 0.4375。
3. 在 MMDocIR 上，Hybrid 页面检索的 Page R@5 为 0.7600，优于单独 BM25 和 Dense；布局节点检索在有精确金标的问题上达到 0.5044 的 Region Hit@5。
4. 当前系统对文本类局部证据最稳定；图表理解、全局统计和表格计算是明确的能力边界，而非已经解决的任务。

## 投稿前仍需补充的材料

1. 对 32 个中文 test 问题的主指标给出 bootstrap 置信区间，或明确说明样本量限制。
2. 从 `errors.csv` 人工抽取至少 20 个中文年报案例，核对证据充分性规则与真实财报证据是否一致。
3. 将 `.mmd` 图源导出为 SVG/PDF，再插入论文 Word 文档；不要直接使用低分辨率截图。
