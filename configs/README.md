# 配置注册表（SSOT）

> Status: working | Scope: `configs/` | SSOT: 是
> 冻结配置永不原地修改，要改复制 `-v2.yaml`。新命名 `…__phase*__….yaml` 先建副本验证，再标旧配置 deprecated。

| config | 数据集/阶段 | 状态 | 说明 |
| --- | --- | --- | --- |
| `experiments/mmdocir_colpali_smoke.yaml` | mmdocir / Phase 1A smoke | working | EXP-001，小样本 `top_k=5`，只验流程 |
| `experiments/mmdocir_colpali.yaml` | mmdocir / Phase 1A full | working | EXP-002 待跑，`top_k=20`，保守 batch 见文件注释 |
| `experiments/mmdocir_bm25_page.yaml` | mmdocir / Phase 1A | working | BM25 对照 |
| `experiments/mmdocir_dense_page_bge_m3.yaml` | mmdocir / Phase 1A | working | Dense 对照（需本地 bge-m3） |
| `experiments/mmdocir_hybrid_page_bge_m3.yaml` | mmdocir / Phase 1A | working | Hybrid 对照 |
| `experiments/mmdocir_layout_node_bge_m3.yaml` | mmdocir / Phase 1B 预备 | working | 布局节点基线，下一步 |
| `experiments/demo_page_region.yaml` | demo | working | 最小闭环 |
| `experiments/cn_bm25_page.yaml` | cn / frozen test | frozen | 默认 test；dev 用 `--split dev` |

旧 `e01–e04_*` 命名保留，待新命名副本验证成功后再标 deprecated（见整理文本第 7 步）。
