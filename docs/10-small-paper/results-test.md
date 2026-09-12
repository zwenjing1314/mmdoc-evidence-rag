# 冻结 Test 主表（SSOT 引用页）

> Status: frozen | Scope: 中文年报 test（4 公司 / 32 问题） | SSOT: 是
> 来源：`docs/paper/03_test_results.md`（原位保留）。本篇只写结论与引用，不复制第二套主表。

- 主结论：Full Evidence Set 页 R@5 `0.8750`、充分率 `0.8750`；`w/o Slot Coverage` / `Single-node` 的 Region Hit@5 更高（`0.9375`）但充分率腰斩，证明目标是充分证据集而非单点命中
- 节点消融：mixed-node 必须，单类型（paragraph / table_block / table_row）均崩
- 运行目录对照：见 `03_test_results.md` 第 4 节 16 个 `runs/retrieval/cn_*/test/...` 目录
- 边界：test 仅 32 问题，需补 bootstrap/显著性 + 人工审计 + 公开集验证（见该文第 5 节）
- 规则：本表冻结；任何改参必须回 dev 开新版本，不得原地改 test
