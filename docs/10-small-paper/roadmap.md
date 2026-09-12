# 研究路线与任务边界（SSOT 引用页）

> Status: working | Scope: 小论文 → 大论文路线 | SSOT: 是
> 来源：`docs/paper/research_positioning_and_roadmap.md`（原位保留）。方向以 `docs/10-small-paper/plan.md` 为准，本篇只收结论。

- 主线：ColPali 作视觉页级 baseline + 候选主干；MMDocIR 作页后区域证据检验；不复现训练，不做 OCR 主贡献
- 复现事实：`vidore/colpali` 在 RTX 3080 Ti 可跑；ViDoRe V1 宏平均 nDCG@5 `80.00%`（官方 81.3），见 `docs/reproduction/`
- 边界：ColPali 输出页级分，无显式区域语义；缺口在 H1-H4，验证方式见该文第 4 节
- 四类错误：A 页中区中 / B 页中区 miss（最直接动机）/ C 页 miss 别的方法中 / D 双失败
- 候选最小链路：冻 ColPali → 按 layout box 聚合 region → query-region MaxSim → 页区融合；OCR/VLM 融合待诊断后定
- 训练边界：MMDocIR evaluation 不能同批训练+测试；先无训练/固定规则
- 可接受结果：页区双升 / 页持平区升 / 仅表格图像升 / 无提升则改模块（见该文 8.3 节）
