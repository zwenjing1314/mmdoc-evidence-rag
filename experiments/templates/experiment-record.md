# 实验记录模板

> 复制本模板到 `docs/20-experiments/YYYY-MM-DD-主题.md`，一次实验一篇。

## 1. 头信息

- EXP-ID:
- 日期：
- 数据集 + split + query 数：
- Config（含 split override）：
- Run 目录：
- 后端（`run_info.json` / 实际 retriever）：

## 2. 命令

```powershell
./tasks.ps1 <task>
```

## 3. 指标（从 `metrics.json` 原样抄）

- Page R@1/5/10：
- MRR / nDCG@5：
- Region Hit@5：
- Sufficiency / mismatch（如有）：

## 4. 产物清单

- `predictions.parquet`：
- `config.json` / `run_info.json` / `metrics.json`：
- `errors.csv` / `summary.md`：

## 5. 结论与下一步

- 支持了哪个假设（H1-H4）：
- 属于 A/B/C/D 哪类：
- 下一步 EXP：
