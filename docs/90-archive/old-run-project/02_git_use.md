# Git 使用流程

## 1. 日常完整流程

```bash
cd /Users/zhouwenjing/Documents/WorkTransfer/PythonProject/mmdoc-evidence-rag

# 查看状态和远程
git status
git remote -v
git branch -vv

# 获取远程最新信息
git fetch origin

# 查看修改
git diff
git diff --stat

# 提交本地修改
git add -A
git status
git commit -m "说明本次修改"

# 推送当前分支
git push origin main
```

## 2. 推荐的安全流程

不直接改远程 `main` 时，使用独立分支：

```bash
git switch -c codex/my-change
git add -A
git commit -m "说明本次修改"
git push -u origin codex/my-change
```

然后在 GitHub 创建 Pull Request，审核后合并。

提交前可创建本地备份分支：

```bash
git branch backup-before-change
```

## 3. 用本地版本覆盖远程 main

只有确认远程新提交可以丢弃时才使用：

```bash
git fetch origin
git log --oneline --left-right main...origin/main
git add -A
git commit -m "同步本地项目最新版本"
git push --force-with-lease origin main
```

优先使用 `--force-with-lease`，不要直接使用 `--force`。强制推送会改写远程历史。

## 4. 常用命令

```bash
# 查看提交记录
git log --oneline --decorate -10

# 查看某次提交
git show <commit>

# 查看分支
git branch -a

# 切换已有分支
git switch main

# 查看远程分支
git ls-remote --heads origin

# 暂存指定文件
git add README.md docs/run_project/02_git_use.md

# 取消暂存，不删除文件
git restore --staged <file>

# 放弃某个未提交文件的修改，谨慎使用
git restore <file>
```

## 5. 本项目当前 Git 状态

最近一次检查结果：

```text
远程：origin -> https://github.com/zwenjing1314/mmdoc-evidence-rag.git
当前分支：main
跟踪分支：origin/main
备份分支：backup-before-github-sync
当前提交：2d25bb7 完善项目运行文档与研究 skill
```

当前 `main` 与 `origin/main` 指向同一提交；新建的本文件尚未提交。

本项目之前存在大量未提交修改，主要包括：

- `README.md` 更新；
- `src/mmdocrag` 代码修改；
- `pyproject.toml` 和 `uv.lock` 依赖修改；
- `skills/mmdoc-evidence-research/`；
- `docs/run_project/01_run_command.md`。

## 6. 本次使用过的检查命令

```bash
git remote -v
git branch -vv
git status --short
git log --oneline --decorate -8
git rev-parse --show-toplevel
git config --get remote.origin.url
git diff --stat
git diff --summary
git ls-tree -r --name-only HEAD
git ls-remote --heads origin
```

最后一条命令需要联网；网络不可用时会出现 DNS 或连接失败，不代表远程地址配置错误。

## 7. 本项目建议提交命令

确认 `git diff` 内容无误后：

```bash
git add README.md \
  docs/run_project/01_run_command.md \
  docs/run_project/02_git_use.md \
  skills/mmdoc-evidence-research \
  pyproject.toml uv.lock

git commit -m "完善项目运行文档与研究 skill"
git push origin main
```

如果还要提交其他源码或配置修改，可改用：

```bash
git add -A
git commit -m "说明本次修改"
git push origin main
```

提交前注意检查文件权限变化：

```bash
git diff --summary
```

如果大量普通文件出现 `100644 => 100755`，说明文件被批量标记为可执行文件，应先确认是否需要保留这些权限变化。

## 8. 小论文阶段：论文分支与标签

小论文采用“一个长期分支 + 若干固定标签”的方式管理：

- 分支 `paper/evidence-set-retrieval`：小论文实验和代码的日常开发分支；
- 标签 `paper-v0.1-baseline`、`paper-v0.2-ablation`、`paper-v1.0-submission`：某个可复现实验状态的永久标记；
- `main`：保持为稳定主线。在小论文代码没有验证前，不直接向 `main` 提交。

### 8.1 第一次创建并推送论文分支

先确认当前修改内容，避免把无关文件带入论文分支：

```bash
git status
git diff
```

从当前稳定的 `main` 创建论文分支并切换过去：

```bash
git switch -c paper/evidence-set-retrieval
```

将新分支推送到 GitHub，并建立本地与远程的跟踪关系：

```bash
git push -u origin paper/evidence-set-retrieval
```

之后每次进入项目，先确认自己在论文分支：

```bash
git branch --show-current
git status
```

预期分支名为 `paper/evidence-set-retrieval`。如需回到主线：

```bash
git switch main
```

### 8.2 每次修改代码后的标准流程

每完成一个清晰的小任务，例如“新增一个消融配置”或“修复 evidence set 排序”，执行：

```bash
# 1. 查看改了什么
git status
git diff

# 2. 只暂存本次任务相关文件（推荐）
git add src/mmdocrag/retrieval/pipeline.py \
  configs/experiments/cn_evidence_set_region.yaml \
  tests/test_retrieval_metrics.py

# 3. 再次核对将要提交的内容
git diff --staged

# 4. 提交：一句中文说明“做了什么”
git commit -m "新增证据集检索消融实验"

# 5. 上传到 GitHub 的论文分支
git push
```

只有当你已经确认本次所有修改都属于同一个任务时，才使用：

```bash
git add -A
```

不要在不检查的情况下使用 `git add -A`，尤其不要把 `.env`、原始数据、模型缓存或临时实验结果提交进仓库。

### 8.3 每轮实验前后的固定做法

实验前先记录当前代码版本：

```bash
git status
git rev-parse HEAD
```

运行实验后，在实验记录 Markdown 中写入：Git commit、配置文件路径、数据版本、模型名称、随机种子和运行目录。`runs/`、`artifacts/`、`data/` 已被 `.gitignore` 忽略，不应直接上传；应提交配置、运行命令、结果汇总表和生成图表的脚本。

当某一轮实验已经完整通过测试并可复现时，先提交并推送全部代码与文档，再创建标签：

```bash
git status
git add <本轮相关代码、配置、测试、文档>
git commit -m "固定小论文 baseline 实验"
git push

git tag -a paper-v0.1-baseline -m "固定小论文 baseline 实验版本"
git push origin paper-v0.1-baseline
```

查看所有论文版本标签：

```bash
git tag -n
```

论文投稿前的最终可复现版本使用新标签，不修改旧标签：

```bash
git tag -a paper-v1.0-submission -m "小论文投稿复现版本"
git push origin paper-v1.0-submission
```

### 8.4 小论文阶段的注意事项

1. 一次提交只解决一个问题：代码、配置、测试和对应说明可以放在同一提交中，但不要混入无关整理。
2. 不上传数据、模型缓存、密钥、`.env`、虚拟环境或完整 `runs/` 目录；论文结果用 Markdown/CSV 汇总和可再运行命令保留。
3. 每次改变模型、数据划分、检索参数或评价脚本，都应新建一次实验运行目录，不能覆盖已用于论文表格的结果。
4. 标签表示“冻结状态”。发现问题后继续提交修复并创建新标签，例如 `paper-v0.2-ablation`，不要删除或移动已记录在论文中的标签。
5. 需要将论文分支合回 `main` 时，先确认小论文阶段稳定，再执行 `git switch main`、`git merge paper/evidence-set-retrieval`，并推送；合并前应先运行测试。
