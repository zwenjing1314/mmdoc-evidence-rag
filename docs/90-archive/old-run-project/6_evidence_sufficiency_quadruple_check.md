# 证据充分性评价与四元组校验实验记录

更新时间：2026-06-01

## 1. 当前实验进度核实

当前中文年报实验 latest run 已核实，最新总实验表与 `runs/retrieval/*/latest/metrics.json` 保持一致。

| 实验 | latest run | Region Hit@5 | Page Recall@5 |
|---|---|---:|---:|
| BM25-page | `20260526_202335` | 0.0000 | 0.2812 |
| Dense-page | `20260531_211450` | 0.0000 | 0.2938 |
| Hybrid-page | `20260531_211203` | 0.0000 | 0.3375 |
| Page→Region | `20260531_211229` | 0.1875 | 0.2500 |
| Hybrid-Page→Region | `20260531_212155` | 0.1938 | 0.3563 |
| Global-Region | `20260531_212333` | 0.2562 | 0.2625 |
| Evidence Set Region | `20260601_105551` | 0.4062 | 0.4250 |
| Oracle-Page→Region | `20260531_212726` | 0.9812 | 1.0000 |

核实结论：

1. 当前实验没有出现指标来源混乱的问题，`current_experiment_results.md` 已更新为最新矩阵。
2. Evidence Set Region 的提升是真实存在的：Region Hit@5 从 `Hybrid-Page→Region` 的 0.1938 提升到 0.4062。
3. 当前仍有明显 Oracle gap：Oracle-Page→Region 的 Region Hit@5 为 0.9812，说明候选证据质量仍有提升空间。
4. 工作树中仍包含未提交的新代码和文档，后续如果需要版本管理，应单独提交一次 evidence set 与 sufficiency 相关改动。

补充：2026-06-01 后续已完成数值定位增强和引用一致性修正，`Evidence Set Region` 最新 run 更新为：

```text
runs/retrieval/cn_evidence_set_region/20260601_181204
```

最新指标为：

| 指标 | 数值 |
|---|---:|
| Page Recall@5 | 0.8125 |
| Region Hit@5 | 0.8063 |
| sufficiency_rate | 0.7875 |
| citation_mismatch_rate | 0.0750 |

## 2. 本次新增内容

本次新增了一个独立评价命令：

```bash
UV_CACHE_DIR=.uv-cache uv run mdr verify-evidence --run runs/retrieval/cn_evidence_set_region/latest --top-k 5
```

该命令用于评价检索出的 evidence set 是否足以支持答案，不替代原有 `evaluate` 检索指标。

输出文件位于：

```text
runs/retrieval/cn_evidence_set_region/latest/evidence_sufficiency_metrics.json
runs/retrieval/cn_evidence_set_region/latest/evidence_sufficiency_cases.csv
runs/retrieval/cn_evidence_set_region/latest/evidence_sufficiency_summary.md
```

## 3. 评价逻辑

本次实现的评价分为两层。

第一层是证据充分性评价，判断 TopK evidence set 是否覆盖回答所需的关键信息。

第二层是“指标-年份-单位-数值”四元组校验，主要用于财务数值类问题。

对于 `numeric` 和 `comparison` 问题，系统检查：

| 项目 | 含义 |
|---|---|
| metric | 证据中是否包含问题对应的财务指标，例如营业收入、归母净利润、经营活动现金流量净额 |
| year | 证据中是否包含问题年份，例如 2025 |
| unit | 证据中是否包含答案单位，例如元、万元、亿元、% |
| value | 证据中是否包含标注答案中的数值 |
| citation | 返回节点是否命中 gold evidence node |

对于 `fact` 等非数值问题，不强行套用财务四元组，只检查答案值和引用是否匹配，避免把“报告年度/报告标题”误判成财务指标问题。

## 4. 状态定义

| 状态 | 含义 |
|---|---|
| sufficient | 关键信息全部覆盖，且引用节点命中 gold node |
| citation_mismatch | 关键信息覆盖完整，但引用节点没有命中 gold node |
| partial | 覆盖了一部分关键信息，但仍缺少指标、年份、单位或数值 |
| insufficient | 关键信息覆盖不足 |

## 5. 最新充分性评价结果

运行对象：

```text
runs/retrieval/cn_evidence_set_region/latest
```

Evidence TopK：

```text
5
```

结果：

| 指标 | 数值 |
|---|---:|
| sufficiency_rate | 0.7875 |
| partial_or_sufficient_rate | 0.8938 |
| citation_mismatch_rate | 0.0750 |
| avg_required_item_coverage | 0.9422 |
| region_hit@5 | 0.8063 |
| sufficient | 126 |
| partial | 17 |
| citation_mismatch | 12 |
| insufficient | 5 |

## 6. 暴露的问题

当前结果说明系统已经能覆盖较多相关证据要素，并且在结构化数值扫描和首页锚点加入后，证据充分性已经明显提升。

主要问题如下：

1. 数值缺失仍是剩余主要问题，但已从 97 次下降到 20 次。
2. 引用不一致从 34 条下降到 12 条。
3. 单位缺失从 4 次下降到 2 次，说明单位识别不是当前最大瓶颈。
4. 当前剩余问题更集中，适合进入失败样例专项分析阶段。

## 7. 当前判断

目前实验没有方向性偏差，反而进入了更接近论文核心问题的阶段：

```text
检索命中率 → 证据集合是否充分 → 答案是否被证据支持 → 是否应该生成或拒答
```

但也要注意，当前 Evidence Set Region 还不是完整可信 RAG，只完成了检索和证据充分性评价的第一版。

后续最应该继续做：

1. 对 `value` 缺失的样例做专项分析，重点查财务表格行、同指标多处出现和单位换算问题。
2. 增加四元组抽取式重排序：优先选择同时包含“指标-年份-单位-数值”的节点或节点组合。
3. 区分 `citation_mismatch` 的原因：是标注 gold node 不唯一，还是检索到了错误章节。
4. 在生成前加入充分性阈值：如果 evidence set 缺少数值或引用不一致，则进入二次检索或拒答。
