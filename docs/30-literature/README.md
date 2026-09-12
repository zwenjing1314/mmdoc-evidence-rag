# 文献一句话表（SSOT）

> Status: working | Scope: 相关工作 | SSOT: 是
> 每篇必须回答五问：是否用 OCR？是否用 BBox？布局注入位置？是否更新局部 patch？是否报告区域级定位？详细笔记在 `docs/literature/`（待压缩归档）。

| 文献 | 一句话 | OCR | BBox | 注入位置 | 更新局部 patch | 区域定位评估 |
| --- | --- | --- | --- | --- | --- | --- |
| MMDocIR | 长文档多模态检索基准，页级+布局级双粒度标注，本文主评测集 | - | 是（标注） | - | - | 是（2638 布局标签） |
| ColPali / ColBERT | 纯视觉多向量 + MaxSim 页级检索，干掉 OCR 流水线 | 否 | 否 | 无 | 是（端到端训练） | 否（只到页） |
| RegionRAG | 训练型：全局+局部 patch 对齐 + 推理期显著区域提议 | 否 | 是（训练标签/伪标签） | 训练损失 + 推理分组 | 是 | 是 |
| Snappy（Patch-to-Region） | 推理期把 patch 相关性传播到已有 OCR BBox，不训练不改文档表示 | 是 | 是 | 推理期打分 | 否 | 是（BBox 级） |
| ColParse | 布局解析替代均匀网格，多向量按语义组件组织，解决存储+切碎问题 | 是（解析） | 是 | 表示层（向量组织） | 是（重训） | 部分 |
| Beyond Bag-of-Patches | 训练期用 GPT-5 全局结构描述教 global token 学版式，推理纯视觉 | 否 | 否 | 训练期辅助损失（global token） | 否（局部不动） | 否（页级） |
| 本文候选 | query 无关、文档侧、OCR/Layout 节点到原始 patch 的稀疏软融合 | 是 | 是 | 文档侧离线融合 | 是（增量 Delta） | 是（IoU≥0.5） |

使用规则：写论文 related work 时以本表为准；若发现行有误，改本表并同步 `docs/literature/` 对应笔记。
