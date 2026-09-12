# tasks.ps1 - Windows unified entry (transparent, not black box)
# Usage:
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

function Get-GitCommit {
  try {
    $c = git rev-parse --short HEAD
    if ($c) { return "$c".Trim() }
  } catch {
    Write-Host "warn: git rev-parse failed"
  }
  return "unknown"
}

function Show-ExpHeader {
  param([string]$ExpId, [string]$EnvName, [string]$Config, [string]$Dataset, [string]$SplitName, [string]$Output)
  $condaEnv = Get-CondaEnv
  $gitCommit = Get-GitCommit
  Write-Host ""
  Write-Host "[$ExpId]"
  Write-Host "  ProjectRoot: $ProjectRoot"
  Write-Host "  Environment: $EnvName ; conda=$condaEnv (uv managed, see pyproject.toml)"
  Write-Host "  GitCommit:   $gitCommit"
  Write-Host "  Config:      $Config"
  Write-Host "  Dataset:     $Dataset / split=$SplitName"
  Write-Host "  Output:      $Output"
  Write-Host ""
}

function Assert-FileExists {
  param([string]$Path, [string]$Hint)
  if (-not (Test-Path $Path)) {
    Write-Host "missing prerequisite: $Path"
    if ($Hint) { Write-Host "  -> $Hint" }
    throw "missing prerequisite: $Path"
  }
}

function Invoke-Mdr {
  param([string[]]$MdrArgs)
  if (-not $env:UV_CACHE_DIR) { $env:UV_CACHE_DIR = ".uv-cache" }
  $fullCmd = "uv run mdr " + ($MdrArgs -join " ")
  Write-Host "RUN: $fullCmd"
  & uv run mdr @MdrArgs
}

switch ($Task) {
  "help" {
    Write-Host "tasks: demo | demo-bm25 | cn-bm25-test | cn-bm25-dev | mmdocir-smoke | mmdocir-full | mmdocir-bm25 | evaluate-mmdocir | check"
    Write-Host "Each task prints EXP-id + conda env + git commit + config + dataset/split + output. See docs/02-commands.md."
  }
  "demo" {
    Show-ExpHeader -ExpId "EXP-DEMO" -EnvName "base (uv)" -Config "configs/experiments/demo_page_region.yaml" -Dataset "demo" -SplitName "-" -Output "runs/retrieval/demo_page_region/<timestamp>"
    Invoke-Mdr @("prepare","--dataset","demo")
    Invoke-Mdr @("retrieve","--config","configs/experiments/demo_page_region.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/demo_page_region/latest")
    Invoke-Mdr @("export-demo","--run","runs/retrieval/demo_page_region/latest")
    Write-Host "check: runs/retrieval/demo_page_region/latest has predictions.parquet / metrics.json / summary.md"
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
    Write-Host "check run_info.json: data_split.name=test, query_count=32, test_status=frozen"
  }
  "cn-bm25-dev" {
    Show-ExpHeader -ExpId "EXP-CN-BM25-DEV" -EnvName "base (uv)" -Config "configs/experiments/cn_bm25_page.yaml --split dev" -Dataset "cn_annual_reports" -SplitName "dev" -Output "runs/retrieval/cn_bm25_page/dev/<timestamp>"
    Invoke-Mdr @("retrieve","--config","configs/experiments/cn_bm25_page.yaml","--split","dev")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/cn_bm25_page/dev/latest")
  }
  "mmdocir-smoke" {
    if (-not $env:HF_HOME) { $env:HF_HOME = "artifacts/hf_cache" }
    Assert-FileExists "configs/experiments/mmdocir_colpali_smoke.yaml" "do not rename old config, see step 7"
    Show-ExpHeader -ExpId "EXP-001" -EnvName "colpali (uv --extra colpali, CUDA/MPS)" -Config "configs/experiments/mmdocir_colpali_smoke.yaml" -Dataset "mmdocir_evaluation" -SplitName "-" -Output "runs/retrieval/mmdocir_colpali_smoke/<timestamp>"
    Write-Host "prereq: run mdr prepare --dataset mmdocir_evaluation first; see docs/01-quickstart.md"
    Invoke-Mdr @("retrieve","--config","configs/experiments/mmdocir_colpali_smoke.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/mmdocir_colpali_smoke/latest")
  }
  "mmdocir-full" {
    if (-not $env:HF_HOME) { $env:HF_HOME = "artifacts/hf_cache" }
    Assert-FileExists "configs/experiments/mmdocir_colpali.yaml" "full baseline config, see configs/README.md"
    Show-ExpHeader -ExpId "EXP-002" -EnvName "colpali (uv --extra colpali, CUDA/MPS)" -Config "configs/experiments/mmdocir_colpali.yaml" -Dataset "mmdocir_evaluation" -SplitName "-" -Output "runs/retrieval/mmdocir_colpali/<timestamp>"
    Write-Host "Phase 1A full baseline top_k=20; embedding cache: artifacts/colpali/"
    Invoke-Mdr @("retrieve","--config","configs/experiments/mmdocir_colpali.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/mmdocir_colpali/latest")
  }
  "mmdocir-bm25" {
    Show-ExpHeader -ExpId "EXP-MMDOCIR-BM25" -EnvName "base (uv)" -Config "configs/experiments/mmdocir_bm25_page.yaml" -Dataset "mmdocir_evaluation" -SplitName "-" -Output "runs/retrieval/mmdocir_bm25_page/<timestamp>"
    Invoke-Mdr @("retrieve","--config","configs/experiments/mmdocir_bm25_page.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/mmdocir_bm25_page/latest")
  }
  "evaluate-mmdocir" {
    if (-not $RunId) { throw "evaluate-mmdocir needs -RunId, e.g. -RunId runs/retrieval/mmdocir_colpali_smoke/latest" }
    if (-not $env:HF_HOME) { $env:HF_HOME = "artifacts/hf_cache" }
    Show-ExpHeader -ExpId "EXP-EVAL" -EnvName "base (uv)" -Config "(reuse run config.json)" -Dataset "mmdocir_evaluation" -SplitName "-" -Output $RunId
    Invoke-Mdr @("evaluate","--run",$RunId)
  }
  "check" {
    Write-Host "[CHECK] ruff + pytest"
    if (-not $env:UV_CACHE_DIR) { $env:UV_CACHE_DIR = ".uv-cache" }
    & uv run ruff check src tests
    & uv run ruff format --check src tests
    & uv run pytest
  }
}
