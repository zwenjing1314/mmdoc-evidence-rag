# MMDocIR 外部验证记录（SSOT 引用页）

> Status: working | Scope: MMDocIR evaluation（313 文档 / 20395 页 / 170338 节点 / 1658 问题，`search_scope=document`） | SSOT: 是
> 来源：`docs/paper/04_mmdocir_results.md`（原位保留）。中文冻结 test 与本记录不混合。

- 页面级（`BAAI/bge-m3, max_length=512, batch_size=2`）：BM25 R@5 `0.7521`；Dense `0.7304`；Hybrid `0.7600` 最好，MRR `0.6143`、nDCG@5 `0.6083`
- 口径：页面 gold 全覆盖 1658；布局精确 gold 仅 1598/1658，页面与布局指标分开报；页面方法无 `node_id`，`region_hit@5` 不适用
- 运行记录：BM25/Dense/Hybrid 三 run 目录见 `04_mmdocir_results.md`；ColPali 全量见 `experiments/registry.csv` EXP-002
- 下一步：`configs/experiments/mmdocir_layout_node_bge_m3.yaml` 布局节点基线（Phase 1B 预备）；耗时以 `experiment_elapsed` 为准
- 详情表见 `docs/paper/04_mmdocir_results.md`
