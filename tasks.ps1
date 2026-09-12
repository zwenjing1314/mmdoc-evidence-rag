# tasks.ps1 - Windows 统一命令入口（透明封装，不做黑盒）
# 用法：
#   ./tasks.ps1 help
#   ./tasks.ps1 demo
#   ./tasks.ps1 check
#   ./tasks.ps1 cn-bm25-test
#   ./tasks.ps1 mmdocir-smoke
#   ./tasks.ps1 mmdocir-full
#   ./tasks.ps1 mmdocir-bm25
#   ./tasks.ps1 evaluate-mmdocir -RunId runs/retrieval/mmdocir_colpali_smoke/latest

param(
  [Parameter(Position=0)]
  [ValidateSet("help","demo","demo-bm25","cn-bm25-test","cn-bm25-dev","mmdocir-smoke","mmdocir-full","mmdocir-bm25","evaluate-mmdocir","check")]
  [string]$Task = "help",
  [string]$RunId = "",
  [string]$Split = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Get-CondaEnv {
  if ($env:CONDA_DEFAULT_ENV) { return $env:CONDA_DEFAULT_ENV }
  return "n/a"
}

function Show-ExpHeader {
  param([string]$ExpId, [string]$EnvName, [string]$Config, [string]$Dataset, [string]$SplitName, [string]$Output)
  Write-Host ""
  Write-Host "[$ExpId]" -ForegroundColor Cyan
  Write-Host "  ProjectRoot: $ProjectRoot"
  Write-Host "  Environment: $EnvName ; conda=$(Get-CondaEnv) (uv managed, see pyproject.toml)"
  Write-Host "  Config:      $Config"
  Write-Host "  Dataset:     $Dataset / split=$SplitName"
  Write-Host "  Output:      $Output"
  Write-Host ""
}

function Invoke-Mdr {
  param([string[]]$MdrArgs)
  # 统一缓存位置，避免每次手写环境变量
  if (-not $env:UV_CACHE_DIR) { $env:UV_CACHE_DIR = ".uv-cache" }
  Write-Host "RUN: uv run mdr $($MdrArgs -join ' ')" -ForegroundColor DarkGray
  & uv run mdr @MdrArgs
}

switch ($Task) {
  "help" {
    Write-Host @"

可用任务：
  demo              demo 最小闭环 prepare -> retrieve -> evaluate -> export-demo
  demo-bm25         demo BM25 baseline
  cn-bm25-test      中文年报 test BM25（冻结划分，不调参）
  cn-bm25-dev       中文年报 dev BM25（调参用）
  mmdocir-smoke     MMDocIR ColPali smoke EXP-001（需 CUDA/MPS + 页面图片）
  mmdocir-full      MMDocIR ColPali full Phase 1A baseline（top_k=20）
  mmdocir-bm25      MMDocIR BM25 page baseline
  evaluate-mmdocir  评测指定 run: -RunId runs/retrieval/<exp>/<timestamp|latest>
  check             ruff + pytest

每次任务都会打印 [EXP-xxx] + Conda 环境 + Config + Dataset/split + Output。
结果登记到 experiments/registry.csv，详情见 docs/02-commands.md。
"@
  }
  "demo" {
    Show-ExpHeader -ExpId "EXP-DEMO" -EnvName "base (uv)" -Config "configs/experiments/demo_page_region.yaml" -Dataset "demo" -SplitName "-" -Output "runs/retrieval/demo_page_region/<timestamp>"
    Invoke-Mdr @("prepare","--dataset","demo")
    Invoke-Mdr @("retrieve","--config","configs/experiments/demo_page_region.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/demo_page_region/latest")
    Invoke-Mdr @("export-demo","--run","runs/retrieval/demo_page_region/latest")
    Write-Host "检查 runs/retrieval/demo_page_region/latest 下 predictions.parquet / metrics.json / summary.md" -ForegroundColor Green
  }
  "demo-bm25" {
    Show-ExpHeader -ExpId "EXP-DEMO-BM25" -EnvName "base (uv)" -Config "configs/experiments/demo_bm25_page.yaml" -Dataset "demo" -SplitName "-" -Output "runs/retrieval/demo_bm25_page/<timestamp>"
    Invoke-Mdr @("retrieve","--config","configs/experiments/demo_bm25_page.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/demo_bm25_page/latest")
  }
  "cn-bm25-test" {
    Show-ExpHeader -ExpId "EXP-CN-BM25-TEST" -EnvName "base (uv)" -Config "configs/experiments/cn_bm25_page.yaml" -Dataset "cn_annual_reports" -SplitName "test" -Output "runs/retrieval/cn_bm25_page/test/<timestamp>"
    Invoke-Mdr @("retrieve","--config","configs/experiments/cn_bm25_page.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/cn_bm25_page/test/latest")
    Write-Host "检查 run_info.json: data_split.name=test, query_count=32, test_status=frozen" -ForegroundColor Green
  }
  "cn-bm25-dev" {
    Show-ExpHeader -ExpId "EXP-CN-BM25-DEV" -EnvName "base (uv)" -Config "configs/experiments/cn_bm25_page.yaml --split dev" -Dataset "cn_annual_reports" -SplitName "dev" -Output "runs/retrieval/cn_bm25_page/dev/<timestamp>"
    Invoke-Mdr @("retrieve","--config","configs/experiments/cn_bm25_page.yaml","--split","dev")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/cn_bm25_page/dev/latest")
  }
  "mmdocir-smoke" {
    # ColPali 需要 GPU；CPU 会被 src/mmdocrag/retrieval/colpali.py 主动拒绝
    if (-not $env:HF_HOME) { $env:HF_HOME = "artifacts/hf_cache" }
    Show-ExpHeader -ExpId "EXP-001" -EnvName "colpali (uv --extra colpali, CUDA/MPS)" -Config "configs/experiments/mmdocir_colpali_smoke.yaml" -Dataset "mmdocir_evaluation" -SplitName "-" -Output "runs/retrieval/mmdocir_colpali_smoke/<timestamp>"
    Write-Host "前置：需先跑 mdr prepare --dataset mmdocir_evaluation 且 page_image_path 存在；MMDocIR 原始数据在项目外，见 docs/01-quickstart.md" -ForegroundColor Yellow
    Invoke-Mdr @("retrieve","--config","configs/experiments/mmdocir_colpali_smoke.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/mmdocir_colpali_smoke/latest")
  }
  "mmdocir-full" {
    if (-not $env:HF_HOME) { $env:HF_HOME = "artifacts/hf_cache" }
    Show-ExpHeader -ExpId "EXP-002" -EnvName "colpali (uv --extra colpali, CUDA/MPS)" -Config "configs/experiments/mmdocir_colpali.yaml" -Dataset "mmdocir_evaluation" -SplitName "-" -Output "runs/retrieval/mmdocir_colpali/<timestamp>"
    Write-Host "Phase 1A 全量 baseline（top_k=20），耗时以 experiment_elapsed 为准；embedding 缓存走 artifacts/colpali/" -ForegroundColor Yellow
    Invoke-Mdr @("retrieve","--config","configs/experiments/mmdocir_colpali.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/mmdocir_colpali/latest")
  }
  "mmdocir-bm25" {
    Show-ExpHeader -ExpId "EXP-MMDOCIR-BM25" -EnvName "base (uv)" -Config "configs/experiments/mmdocir_bm25_page.yaml" -Dataset "mmdocir_evaluation" -SplitName "-" -Output "runs/retrieval/mmdocir_bm25_page/<timestamp>"
    Invoke-Mdr @("retrieve","--config","configs/experiments/mmdocir_bm25_page.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/mmdocir_bm25_page/latest")
  }
  "evaluate-mmdocir" {
    if (-not $RunId) { throw "evaluate-mmdocir 需要 -RunId，例如 -RunId runs/retrieval/mmdocir_colpali_smoke/latest" }
    if (-not $env:HF_HOME) { $env:HF_HOME = "artifacts/hf_cache" }
    Show-ExpHeader -ExpId "EXP-EVAL" -EnvName "base (uv)" -Config "(reuse run config.json)" -Dataset "mmdocir_evaluation" -SplitName "-" -Output $RunId
    Invoke-Mdr @("evaluate","--run",$RunId)
  }
  "check" {
    Write-Host "[CHECK] ruff + pytest" -ForegroundColor Cyan
    if (-not $env:UV_CACHE_DIR) { $env:UV_CACHE_DIR = ".uv-cache" }
    & uv run ruff check src tests
    & uv run ruff format --check src tests
    & uv run pytest
  }
}
