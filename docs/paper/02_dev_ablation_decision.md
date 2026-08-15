# Dev 消融结果与最终方法选择

本记录使用公司级 `dev` split：4 家公司、32 个问题。所有运行均使用：

```text
BAAI/bge-small-zh-v1.5
dense_max_seq_length=128
output_top_k=5
max_evidence_nodes=3
```

## 1. 消融结果

| 方法 | Region Hit@5 | Sufficiency Rate | Partial or Sufficient | Citation Mismatch | Required Item Coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full Evidence Set | 0.7500 | 0.7500 | 0.8438 | 0.1563 | 0.9766 |
| w/o Hybrid-page | 0.7500 | 0.7500 | 0.8125 | 0.1875 | 0.9844 |
| w/o Global-region | 0.7188 | 0.7188 | 0.8438 | 0.1563 | 0.9688 |
| w/o Numeric Scan | 0.5000 | 0.5000 | 0.7812 | 0.2188 | 0.9297 |
| w/o Slot Coverage | 0.8125 | 0.3750 | 0.9062 | 0.0625 | 0.8047 |
| Single-node | 0.7812 | 0.4688 | 0.9062 | 0.0938 | 0.8672 |

## 2. 选择结论

最终 test 使用 `configs/experiments/cn_evidence_set_region.yaml` 的默认配置，不再调整以下设置：

```yaml
use_hybrid_page: true
use_global_region: true
use_structured_scan: true
use_cover_anchor: true
use_slot_coverage: true
selection_mode: greedy
```

理由：

1. 结构化数值扫描对 Region Hit@5 与 Sufficiency Rate 都有最大贡献。
2. Global-region 候选提升了至少一个 dev 问题的节点命中与充分性。
3. Slot Coverage 和 greedy evidence set 的目标是“充分证据”，不只是单个 gold node 命中；移除后 Region Hit@5 更高，但充分性显著下降。
4. Hybrid-page 没有提高本 dev split 的核心命中率，但减少了 citation mismatch，因此保留。

## 3. Test 使用规则

从本记录创建后，`test` 只用于最终的 baseline、完整方法和已预先指定的必要消融。不得依据 test 指标改变候选来源、阈值、权重、Top-K 或选择策略；若需要改动，必须回到 dev 并新建方法版本。
