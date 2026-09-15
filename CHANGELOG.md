# Changelog

格式遵循 Keep a Changelog 思想：只记面向使用者的变更，不记每日流水。

## [Unreleased]

### Added

- 新增 `tasks.ps1` Windows 统一命令入口（demo / cn-bm25-test / mmdocir-smoke / check），每次任务打印 EXP 编号 + Config + Dataset/split + Output。
- 新增 `docs/00-index.md`、`01-quickstart.md`、`02-commands.md`、`03-glossary.md` 四篇 SSOT 入口。
- 新增 `docs/10-small-paper/`、`docs/20-experiments/`、`docs/30-literature/`、`docs/90-archive/` 新骨架与 `experiments/registry.csv` + 记录模板。
- 新增 `CONTRIBUTING.md` 开发流程与 Phase Gate。
- 新增 `docs/PROJECT_RULES.md`、`docs/SMALL_PAPER_DEV_SPEC.md`、`docs/THESIS_RESEARCH_ROUTE_DRAFT.md` 三份规范与 `docs/handoff.md` 交接记录。
- 新增 `.cursor/rules/`（00 核心铁律、01 沟通与交付、02 新技术准入、10 研究边界、20 实验协议、30 融合架构）与 `.cursor/skills/mmdoc-evidence-research/` 研究罗盘 skill。
- 新增 `docs/MIGRATION.md` 与 `docs/NEW_PROJECT_SCAFFOLD.md`：LayoutPatch 新仓库迁移清单与骨架说明。

### Changed

- 无（第 2 步只新增骨架，不删除、不改名旧文件）。
- `docs/00-index.md` 新增「项目规范与协作」一节（登记六条 rules 与 skill 路径）。
- `.cursor/rules/00-project-core.mdc`：原第 8 条语言规则先改为指向 01 号引用，后恢复为「语言底线」独立条款（第 8 条，明确不可被消息语言覆盖），与 01 号细则构成双层结构。
- `.cursor/rules/01-communication.mdc`：删除空 `globs:` 字段；新增第 5 节「规则加载探针」用于用户主动验证规则注入。
- `.cursor/rules/02-tech-approval.mdc`：删除空 `globs:` 字段。
- `.cursor/rules/01-communication.mdc`：移除已完成验证使命的临时「规则加载探针」章节，减少常驻规则上下文并保持文件职责单一。
