# LayoutPatch 新项目骨架（生成器清单）

> 用途：新项目只创建下列文件/目录。本文件本身留在旧仓库 `docs/` 作为清单，新项目不需要它。
> 标注说明：[x] = 本次已生成；[ ] = 迁移时从旧仓库复制或首周创建。

## 已生成的骨架文件

```text
[x] layoutpatch/README.md                  项目门面（含 Phase 状态与约束速记）
[x] layoutpatch/docs/RULES.md              项目开发规范（从 PROJECT_RULES.md 改造：包名/任务名已换）
[x] layoutpatch/docs/00-index.md           SSOT 导航（六类信息去向）
[x] layoutpatch/docs/handoff.md            交接记录（空模板，首版待填）
[x] layoutpatch/docs/THESIS_SPEC.md        占位（迁移时用旧 THESIS_RESEARCH_ROUTE_DRAFT.md 覆盖）
[x] layoutpatch/docs/PAPER_SPEC.md         占位（迁移时用旧 SMALL_PAPER_DEV_SPEC.md 覆盖）
[x] layoutpatch/docs/MIGRATION.md          迁移清单（从旧仓库 docs/MIGRATION.md 复制）
```

## 迁移时复制的文件（不改名）

```text
[ ] docs/THESIS_SPEC.md   ← 旧 docs/THESIS_RESEARCH_ROUTE_DRAFT.md
[ ] docs/PAPER_SPEC.md    ← 旧 docs/SMALL_PAPER_DEV_SPEC.md
[ ] docs/01-quickstart.md、02-commands.md（改任务名与路径后入库）
[ ] .cursor/rules/*.mdc 六条（00/01/02/10/20/30）+ .cursor/skills/mmdoc-evidence-research/
[ ] experiments/registry.csv + templates/ + 两份 EXP 记录
[ ] docs/reproduction/colpali_vidore_v1_reproduction_20260830.md
[ ] configs/datasets/mmdocir.yaml + 五个 mmdocir 实验 config + configs/README.md
[ ] 代码按 src/layoutpatch/ 包名重接（见下）
[ ] docs/literature/ + docs/30-literature/README.md
```

## 首周创建（新项目专属，旧仓库没有的）

```text
[ ] pyproject.toml（包名 layoutpatch，CLI 命令 lp，其余复用旧 pyproject 的锁版本与 cu130 源）
[ ] .python-version  .gitignore  .env.example  CHANGELOG.md  CONTRIBUTING.md
[ ] tasks.ps1（统一任务入口，任务名沿用 mmdocir-prepare / colpali-full / check 等）
[ ] tests/ 空目录 + smoke
[ ] docs/02-commands.md 首版（prepare / retrieve / evaluate / check 四条起步）
```

## src/ 目标结构（Phase 2 全部落地后的形状，先只建需要的）

```text
src/layoutpatch/
├── __init__.py
├── cli.py                  # lp 命令入口（typer）
├── config.py  paths.py  schemas.py  io.py        # 骨架四件（从旧 mmdocrag 改包名）
├── datasets/
│   └── adapters.py         # MMDocIR prepare（对数 313/20395/170338/1658）
├── retrieval/
│   ├── pipeline.py  scoring.py
│   ├── colpali.py          # 冻结 ColPali 编码 + MaxSim + embedding cache
│   └── fusion/             # Phase 2 新增
│       ├── sparse_fusion.py
│       ├── gate.py
│       ├── fused_index.py
│       └── region_scoring.py
├── layout/                 # Phase 1B 前新增
│   ├── nodes.py            # TextLayoutEncoder → T [M,D]
│   └── correspondence.py   # W 计算（三选一）+ 行归一化 + 空行标记
└── evaluation/
    ├── metrics.py  pipeline.py
    ├── region_metrics.py   # IoU Hit@0.5 + Text Recall/F1 + A/B/C/D + 分层
    └── audit.py            # 坐标审计（机器门限 + 叠图）
```

## 目录纪律提醒（来自 RULES.md）

- 根目录条目超过 25 个必须整理；新增顶层条目先在 RULES.md 白名单登记；
- runs/ data/ artifacts/ 永不进 git；
- 禁止新建 change log / current results 类流水账文件；
- 新会话从 docs/handoff.md 接上下文。
