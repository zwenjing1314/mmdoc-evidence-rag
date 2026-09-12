# 小论文研究路线（SSOT）

> Status: working | Scope: 小论文 Phase 1A → 1B → 1C → 2 | SSOT: 是
> 当前方向只写在这里。方法细节 candidats 见 `docs/small_paper_research_plan_final.md`（待拆 `plan.md/method-spec.md`）。

## 1. 题目与问题

布局约束文档侧 Patch 融合：不裁剪区域图像、不重复跑视觉编码器、保持 ColPali/MaxSim 接口，用 OCR + BBox + 区域类型学局部增量 `P_fused`，改善页内证据区域定位。

## 2. Phase Gate（硬门槛）

```text
Phase 1A：数据、环境、ColPali 页级 baseline        ← 当前位置（EXP-001 smoke 已成，EXP-002 full 待跑）
Phase 1B：页面命中 vs 区域命中缺口诊断（A/B/C/D 四类 + 按类型/面积/OCR密度分层）
Phase 1C：Snappy-style / 固定 BBox / 动态显著区域三基线
Phase 2：缺口稳定且规则方法不足，才训练稀疏融合网络
```

```text
1A 没完成，不跑 1B
1B 没有 A/B/C/D 统计，不跑 1C
1C 三类 baseline 没完成，不训练新网络
```

## 3. 与 Beyond Bag-of-Patches 的边界

对方：GPT-5 全局描述 + global token，不用 OCR/BBox，不更新局部 patch。
本文：OCR/BBox 区域节点到原始 patch 的显式空间软融合，主评区域定位（IoU≥0.5 预先声明）。
不声称“首次学习布局”。
