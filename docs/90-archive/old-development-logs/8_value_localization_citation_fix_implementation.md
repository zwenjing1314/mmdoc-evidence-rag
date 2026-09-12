# 数值定位增强与引用一致性修正实现记录

更新时间：2026-06-01

## 1. 修改目标

上一轮证据充分性评价发现两个主要问题：

- `value` 缺失较多：系统经常能找到指标、年份和单位，但没有精确定位到答案数值所在节点；
- `citation_mismatch` 较多：部分证据内容相关，但引用节点没有命中 gold evidence node。

本次修改目标是增强 `Evidence Set Region`，但仍遵守一个原则：

```text
检索阶段不使用 gold answer、raw_answer_value、evidence_node_ids。
```

因此，本次只使用问题文本、节点文本、节点类型、页面上下文和文档结构信息做增强。

## 2. 核心改动

### 2.1 结构化数值扫描候选

新增 `structured_numeric_scan` 候选来源。对于 `numeric` 和 `comparison` 问题，系统会在当前文档全部节点中扫描可能的财务表格证据。

评分信号包括：

- 节点是否包含问题指标；
- 节点是否包含数值形态；
- 同页上下文是否包含年份、单位和表头；
- 节点类型是否为 `table_row` 或 `table_block`；
- 是否存在“项目、2025、2024、本年比上年增减、单位”等表格上下文；
- 是否属于审计说明、风险说明等叙述性干扰内容。

这一步解决的问题是：很多正确的财务指标行本身没有写“单位：元”或“2025 年”，这些信息在同页表头中，因此需要把“节点文本 + 同页上下文”一起用于定位。

### 2.2 首页锚点候选

新增 `cover_anchor` 候选来源。对于报告年度、报告标题、首页标题类问题，系统会强制加入该文档第一页的前若干节点。

这一步解决的问题是：封面类问题经常被目录页、页眉或正文中的“年度报告”干扰，导致引用节点不在首页。

### 2.3 定位分数增强

在候选节点综合分中新增：

- `structured_score`
- `structured_rank`
- `cover_rank`
- `localization_score`

并写入 `RetrievalHit.metadata`，方便后续分析每个证据节点为什么被选中。

### 2.4 数值匹配评价修正

证据充分性评价中发现一个问题：长表格文本被压缩后，正则会把相邻数字粘连，导致明明包含标准答案数值却被误判为 `value` 缺失。

本次修正了 `value_in_text()`：

- 先做去空格、去逗号的直接子串匹配；
- 再回退到数字 token 归一化匹配；
- 支持括号负数、百分号和千分位逗号。

## 3. 最新实验结果

运行命令：

```bash
UV_CACHE_DIR=.uv-cache uv run mdr retrieve --config configs/experiments/cn_evidence_set_region.yaml
UV_CACHE_DIR=.uv-cache uv run mdr evaluate --run runs/retrieval/cn_evidence_set_region/latest
UV_CACHE_DIR=.uv-cache uv run mdr verify-evidence --run runs/retrieval/cn_evidence_set_region/latest --top-k 5
```

最新 run：

```text
runs/retrieval/cn_evidence_set_region/20260601_181204
```

检索指标：

| 指标 | 修改后 |
|---|---:|
| Page Recall@1 | 0.4250 |
| Page Recall@5 | 0.8125 |
| Page Recall@10 | 0.8125 |
| MRR | 0.5529 |
| nDCG@5 | 0.4405 |
| nDCG@10 | 0.4405 |
| Region Hit@5 | 0.8063 |

证据充分性指标：

| 指标 | 修改后 |
|---|---:|
| sufficiency_rate | 0.7875 |
| partial_or_sufficient_rate | 0.8938 |
| citation_mismatch_rate | 0.0750 |
| avg_required_item_coverage | 0.9422 |
| sufficient | 126 |
| partial | 17 |
| citation_mismatch | 12 |
| insufficient | 5 |

## 4. 与上一版对比

| 指标 | 上一版 | 当前版 | 变化 |
|---|---:|---:|---:|
| Region Hit@5 | 0.4062 | 0.8063 | +0.4001 |
| sufficiency_rate | 0.1750 | 0.7875 | +0.6125 |
| citation_mismatch_rate | 0.2125 | 0.0750 | -0.1375 |
| sufficient 数量 | 28 | 126 | +98 |
| citation_mismatch 数量 | 34 | 12 | -22 |

## 5. 当前剩余问题

修改后仍有少量问题：

- `value` 缺失 20 次；
- `unit` 缺失 2 次；
- `citation_mismatch` 12 次；
- `insufficient` 5 次。

下一步建议对这些剩余失败样例单独分析，判断是：

1. 标注 gold node 不唯一；
2. 表格切分导致数值和指标分离；
3. 同一指标在多个章节反复出现；
4. 单位换算或亿元/万元/元表达不一致；
5. 问题本身需要跨节点或跨页证据。

## 6. 测试

新增/更新测试覆盖：

- 结构化数值扫描优先表格行而不是审计叙述；
- 同页表头上下文能够提升财务行得分；
- 首页锚点候选能修正封面类引用；
- 密集表格文本中的大数值能被正确匹配。

验证结果：

```text
ruff check passed
ruff format --check passed
35 passed
```
