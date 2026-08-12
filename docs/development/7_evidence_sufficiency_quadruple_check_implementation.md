# 证据充分性评价与四元组校验实现记录

更新时间：2026-06-01

## 1. 修改目标

在 Evidence Set Region 检索器之后，继续实现论文创新点三的前置能力：判断检索得到的 evidence set 是否足以支持答案。

本次不做 LLM 生成，也不做 LLM verifier，而是先实现可复现的规则评价：

```text
Evidence Set → 指标/年份/单位/数值覆盖检查 → 引用一致性检查 → sufficient/partial/citation_mismatch/insufficient
```

## 2. 代码改动

新增文件：

```text
src/mmdocrag/evaluation/sufficiency.py
tests/test_evidence_sufficiency.py
```

修改文件：

```text
src/mmdocrag/evaluation/__init__.py
src/mmdocrag/cli.py
```

新增 CLI：

```bash
uv run mdr verify-evidence --run runs/retrieval/cn_evidence_set_region/latest --top-k 5
```

## 3. 核心实现

`verify_evidence_run()` 读取一个 retrieval run：

```text
run_info.json
predictions.parquet
data/processed/<dataset>/queries.parquet
```

然后对每个 query 的 TopK evidence hits 执行：

1. 合并 evidence text；
2. 根据问题类型确定需要检查的项目；
3. 对数值类问题检查“指标-年份-单位-数值”；
4. 检查返回节点是否命中 gold evidence node；
5. 输出状态和覆盖率。

对于 `numeric` 和 `comparison` 问题，检查四元组：

```text
metric + year + unit + value
```

对于 `fact` 问题，不强行检查财务指标，只检查答案值和引用，避免把报告年度、报告标题错误地当成财务指标。

## 4. 输出产物

运行后写入当前 run 目录：

```text
evidence_sufficiency_metrics.json
evidence_sufficiency_cases.csv
evidence_sufficiency_summary.md
```

其中：

- `metrics.json` 保存总体充分性指标；
- `cases.csv` 保存每个问题的 covered/missing 项；
- `summary.md` 保存可阅读的实验摘要和典型失败样例。

## 5. 测试覆盖

新增测试覆盖：

1. 完整四元组命中；
2. 缺少单位和数值；
3. fact 问题不强行要求财务指标；
4. 引用不一致识别为 `citation_mismatch`；
5. `partial` 和 `insufficient` 状态判定；
6. 带逗号、括号负数、百分号的数值归一化。

验证命令：

```bash
UV_CACHE_DIR=.uv-cache uv run ruff check src tests
UV_CACHE_DIR=.uv-cache uv run ruff format --check src tests
UV_CACHE_DIR=.uv-cache uv run pytest
```

当前结果：

```text
31 passed
```

## 6. 最新实验结果

运行命令：

```bash
UV_CACHE_DIR=.uv-cache uv run mdr verify-evidence --run runs/retrieval/cn_evidence_set_region/latest --top-k 5
```

结果：

| 指标 | 数值 |
|---|---:|
| sufficiency_rate | 0.1750 |
| partial_or_sufficient_rate | 0.7562 |
| citation_mismatch_rate | 0.2125 |
| avg_required_item_coverage | 0.8156 |
| region_hit@5 | 0.4062 |
| sufficient | 28 |
| partial | 93 |
| citation_mismatch | 34 |
| insufficient | 5 |

## 7. 当前问题

本次实现后，实验暴露出一个更清晰的问题：

```text
Evidence Set Region 能找到较多相关证据，但精确数值定位和引用一致性还不足。
```

从 `evidence_sufficiency_cases.csv` 统计看：

- `value` 缺失 97 次；
- `unit` 缺失 4 次；
- `metric` 缺失 2 次；
- `citation_mismatch` 34 次。

因此下一步应该重点改进 value 定位和 citation 对齐，而不是继续盲目增加检索 baseline。
