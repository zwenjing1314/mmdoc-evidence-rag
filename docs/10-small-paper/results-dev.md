# Dev 消融与选型（SSOT）

> Status: frozen | Scope: 中文年报 dev（4 公司 / 32 问题） | SSOT: 是
> 来源：`docs/paper/02_dev_ablation_decision.md`（原位保留）。本篇为 SSOT 引用页，不复制第二套表格。

- 数据与配置：`BAAI/bge-small-zh-v1.5`，`dense_max_seq_length=128`，`output_top_k=5`，`max_evidence_nodes=3`
- 结论：test 用 `configs/experiments/cn_evidence_set_region.yaml` 默认配置（hybrid/global/scan/cover/slot 全开，`selection_mode=greedy`）
- 理由：数值扫描贡献最大；global-region 至少改善一个 dev 问题；slot+greedy 保充分率而非单点命中；hybrid 降 mismatch
- 规则：test 只跑最终方法和预声明消融；按 test 改参必须回 dev 开新版本
- 详情表见 `docs/paper/02_dev_ablation_decision.md` 第 1-2 节
