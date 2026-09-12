# EXP-002 ColPali full Phase 1A baseline（正式）

## 1. 实验目的

- Phase 1A 全量 ColPali 页级 baseline，作为 1B 缺口诊断的对照
- Gate：本记录已完成；可以进入 Phase 1B 页面命中与区域命中缺口诊断

## 2. 环境

- Conda 环境：`colpali`；Python `C:\Users\WenJing\anaconda3\envs\colpali\python.exe`
- PyTorch `2.13.0+cu130`，CUDA 可用，`colpali_engine=0.3.18`
- 代码 commit：`fbf596f`；embedding 缓存 `artifacts/colpali/`

## 3. 数据和 split

- 数据集：`mmdocir_evaluation`
- split：无 / 全量文档内检索（`search_scope=document`）
- 规模：313 documents、20,395 pages、170,338 nodes、1,658 queries；预测 30,112 hits

## 4. 配置文件

- `configs/experiments/mmdocir_colpali.yaml`
- `colpali_page, search_scope=document, model=vidore/colpali, top_k=20`
- `image_batch_size=1, query_batch_size=2, score_batch_size=4, use_embedding_cache=true`

## 5. 运行命令

```powershell
conda activate colpali
& "C:\Users\WenJing\anaconda3\envs\colpali\Scripts\mdr.exe" retrieve --config configs\experiments\mmdocir_colpali.yaml
& "C:\Users\WenJing\anaconda3\envs\colpali\Scripts\mdr.exe" evaluate --run runs\retrieval\mmdocir_colpali\20260912_221714
```

本次按当前代码重新执行 retrieve 与 evaluate；评价通过 query ID 和 data_counts 对齐校验。

## 6. 代码 commit

- `fbf596f`（工作区提交后运行）

## 7. 输出目录

- `runs/retrieval/mmdocir_colpali/20260912_221714`（`latest.txt` 指向）
- 历史无效 run：`20260831_163643`、`20260831_163043`，仅作排错参考

## 8. 关键指标（复评原样抄）

- Page R@1/5/10：`0.5724 / 0.8390 / 0.9047`
- MRR / nDCG@5 / nDCG@10：`0.6890 / 0.6932 / 0.7231`
- Region Hit@5：`NA`（页级方法不返回 `node_id`，将在区域方法中评估）

该结果是当前代码、full processed 数据和 `vidore/colpali` checkpoint 下的正式 Phase 1A 页面级 baseline。由于方法只输出页面，不产生区域级命中结论。

## 9. 错误信息

- 无；Hugging Face 未认证提示不影响本次使用缓存模型

## 10. 结果解释

- 支持假设：确定 ColPali 页面级 baseline 分母；尚未验证 H1-H4
- A/B/C/D：待 1B 诊断

## 11. 是否可用于论文 + 下一步

- 可用于论文：是（Phase 1A 页面级 baseline；区域指标不适用）
- 下一步：设计并运行 Phase 1B 页面命中 vs 证据区域命中缺口诊断
- Gate：1A 已完成；在 1B 的 A/B/C/D 统计完成前，不进入 1C 或训练网络
