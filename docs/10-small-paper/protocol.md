# 实验评价协议（SSOT）

> Status: stable | Scope: 中文年报 + MMDocIR 评价 | SSOT: 是
> 评价口径只写在这里。`02-commands.md` 只写怎么跑，不重复口径。

来源：`docs/paper/01_experiment_protocol.md`（中文冻结划分）+ `src/mmdocrag/evaluation/` 实际实现。

## 1. 中文年报冻结协议

- QA：`data/raw/cn_annual_reports/qa_annotations_v2_reviewed.csv`（SHA 以 `01_experiment_protocol.md` 为准，程序每次校验，不一致即停）
- 划分：`configs/splits/cn_annual_reports_company_v1.yaml`（train 12/96、dev 4/32、test 4/32，`test_status: frozen`）
- 默认 split：中文配置默认 `test`；dev 调参必须显式 `--split dev`，输出进独立 `dev/` 目录
- 指标（`evaluate` 产物 `metrics.json` 原样抄）：Page Recall@k、MRR、nDCG、Region Hit；`verify-evidence --top-k 5` 另给充分率 / mismatch / 槽位覆盖
- 规则：train/dev 定权重、Top-K、阈值、方法版本后记 commit 冻结；test 只跑最终方法和预声明消融；按 test 改参必须回 dev 开新版本
- 论文引用格式：`dataset版本 + split + query数 + config路径 + run目录 + 日期 + 后端`

## 2. MMDocIR 外部验证协议

- 数据：313 文档、20395 页、170338 节点、1658 问题；`search_scope=document` 只评文档内定位，不评跨文档
- 页面 gold 覆盖全部 1658；布局精确 gold 仅 1598/1658，页面与布局指标分开报
- 页面级：Recall@k、MRR、nDCG（`evaluate` 产物）；布局级 MRR/nDCG 只在 1598 eligible queries 上算
- 正式结果见 `docs/paper/04_mmdocir_results.md`；耗时以日志 `experiment_elapsed` 为准

## 3. 防泄漏

- 候选 BBox 只能来自解析结果；gold 页 / node / 答案值只能用于 oracle 上界分析
- oracle 必须标 `oracle/upper-bound`，不与可部署方法并列排名
