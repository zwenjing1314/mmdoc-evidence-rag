# Evidence Set 检索器实现记录

更新时间：2026-06-01

## 1. 修改原因

前一轮误差分析发现，`Hybrid-Page→Region` 的 `Region Hit@5` 只有 `0.1938`，而 `Global-Region` 为 `0.2562`，`Oracle-Page→Region` 达到 `0.9812`。这说明当前系统的主要问题不是节点库完全不可用，而是页面过滤和单节点排序会漏掉一部分可用证据。

因此，本次新增 `evidence_set_region` 检索器，目标是把论文创新点二落到代码上：从“单个节点排序”升级为“候选池召回 + 最小充分证据集选择”。

## 2. 核心方法

新方法不替换已有 baseline，而是新增一个可对比的方法：

```text
Hybrid-page TopK 页面内节点 + Global-Region TopK 节点
        ↓
候选节点去重
        ↓
region-level semantic scoring
        ↓
指标、年份、单位、数值形态、问题关键词覆盖度打分
        ↓
贪心选择最小充分 evidence set
```

候选池包含两部分：

- `Hybrid-page TopK` 页面内的所有候选节点；
- `Global-Region TopK` 直接节点检索结果。

节点通过 `node_id` 去重，并记录来源信息：

- `hybrid_page`
- `global_region`
- `page_rank`
- `global_rank`

## 3. 覆盖度设计

系统会从问题中抽取覆盖槽位：

- `metric:*`：如营业收入、归母净利润、经营活动现金流量净额、研发投入、资产总额、风险等；
- `year:*`：如 2025；
- `unit:*`：如元、万元、亿元、%、百分点；
- `numeric_shape`：判断节点是否包含金额、百分比、括号负数等数值形态；
- `keyword:*`：问题中的核心关键词。

注意：检索和排序不使用 `answer`、`raw_answer_value`、`normalized_answer`、`evidence_node_ids`，避免把标准答案泄漏给检索器。当前只允许使用 `answer_unit`，因为单位是问题类型约束，不是答案数值本身。

## 4. 代码修改

主要修改：

- `src/mmdocrag/retrieval/pipeline.py`
  - 新增 `evidence_set_region` 分支；
  - 新增候选池构建函数；
  - 新增覆盖槽位抽取和候选节点打分；
  - 新增最小充分证据集选择逻辑。

- `src/mmdocrag/schemas.py`
  - `RetrievalHit` 新增 `metadata` 字段，用于保存解释信息。

- `configs/experiments/cn_evidence_set_region.yaml`
  - 新增中文年报 evidence set 检索实验配置。

- `tests/test_retrieval_metrics.py`
  - 增加候选池合并、单文档隔离、覆盖度排序、最小证据集、防答案泄漏等测试。

- `tests/test_schemas_io.py`
  - 增加 `RetrievalHit.metadata` 的 parquet roundtrip 测试。

## 5. 运行命令

代码质量检查：

```bash
UV_CACHE_DIR=.uv-cache uv run ruff check src tests
UV_CACHE_DIR=.uv-cache uv run pytest
```

运行新实验：

```bash
UV_CACHE_DIR=.uv-cache uv run mdr retrieve --config configs/experiments/cn_evidence_set_region.yaml
UV_CACHE_DIR=.uv-cache uv run mdr evaluate --run runs/retrieval/cn_evidence_set_region/latest
```

## 6. 本次实验结果

最新运行目录：

```text
runs/retrieval/cn_evidence_set_region/20260601_105551
```

评价结果：

| 指标 | 数值 |
|---|---:|
| Page Recall@1 | 0.1562 |
| Page Recall@5 | 0.4250 |
| Page Recall@10 | 0.4250 |
| MRR | 0.2378 |
| nDCG@5 | 0.1638 |
| nDCG@10 | 0.1638 |
| Region Hit@5 | 0.4062 |

与前一轮主要 baseline 对比：

| 方法 | Page Recall@5 | Region Hit@5 |
|---|---:|---:|
| Hybrid-Page→Region | 0.3563 | 0.1938 |
| Global-Region | 0.2625 | 0.2562 |
| Evidence Set Region | 0.4250 | 0.4062 |
| Oracle-Page→Region | 1.0000 | 0.9812 |

可以看到，`Evidence Set Region` 相比 `Hybrid-Page→Region` 和 `Global-Region` 都有提升，说明“页面候选 + 全局节点候选 + 覆盖度选择”的方向是有效的。

## 7. 当前仍需注意的问题

当前方法仍然是规则增强的 evidence set 检索器，还没有接入 LLM 生成、证据充分性 verifier 和拒答机制。

从样例看，部分财务问题仍会被同一公司中其它包含相同指标词的章节干扰，例如业务回顾、审计说明或子公司收入描述。这说明下一步需要继续做：

- `single-node vs evidence-set` 对比实验；
- evidence set 级别的充分性指标；
- 针对“指标-年份-单位-数值”四元组的一致性校验；
- 生成前证据充分性判断和不可回答问题拒答实验。
