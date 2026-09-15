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
Set-Location -LiteralPath $ProjectRoot
# This repository has exactly one runtime environment.  Ignore an activated
# Conda/venv shell and make every uv invocation target the project .venv.
Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
$env:UV_PROJECT_ENVIRONMENT = Join-Path $ProjectRoot ".venv"
if (-not $env:UV_SYSTEM_CERTS) { $env:UV_SYSTEM_CERTS = "true" }

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
  $gitCommit = Get-GitCommit
  Write-Host ""
  Write-Host "[$ExpId]"
  Write-Host "  ProjectRoot: $ProjectRoot"
  Write-Host "  Environment: $EnvName"
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

function Assert-MmdocirFullData {
  if (-not $env:UV_CACHE_DIR) { $env:UV_CACHE_DIR = ".uv-cache" }
  $check = "import polars as pl, sys; root='data/processed/mmdocir_evaluation'; counts={name: pl.read_parquet(f'{root}/{name}.parquet').height for name in ['documents','pages','nodes','queries']}; print('full data counts:', counts); expected={'documents':313,'pages':20395,'nodes':170338,'queries':1658}; sys.exit(0 if counts == expected else 1)"
  Write-Host "CHECK: data/processed/mmdocir_evaluation must be the frozen full MMDocIR preparation"
  & uv run --extra colpali python -c $check
  if ($LASTEXITCODE -ne 0) {
    throw "MMDocIR full data check failed. Run uv run mdr prepare --dataset mmdocir_evaluation without --limit-docs."
  }
}

function Invoke-Mdr {
  param([string[]]$MdrArgs)
  if (-not $env:UV_CACHE_DIR) { $env:UV_CACHE_DIR = ".uv-cache" }
  $fullCmd = "uv run --extra colpali mdr " + ($MdrArgs -join " ")
  Write-Host "RUN: $fullCmd"
  & uv run --extra colpali mdr @MdrArgs
}

function Assert-UvColpaliCuda {
  $probe = & uv run --extra colpali python -c "import torch, colpali_engine; print(torch.__version__); print(torch.cuda.is_available())"
  if ($LASTEXITCODE -ne 0 -or $probe[-1].ToString().Trim() -ne "True") {
    throw "uv ColPali environment is not CUDA-enabled. Run 'uv sync --dev --extra colpali' and verify torch CUDA support."
  }
}

function Invoke-ColpaliMdr {
  param([string[]]$MdrArgs)
  # ColPali uses the same uv project environment as every other task.
  Assert-UvColpaliCuda
  Write-Host "RUN: uv run --extra colpali mdr $($MdrArgs -join ' ')"
  & uv run --extra colpali mdr @MdrArgs
}

switch ($Task) {
  "help" {
    Write-Host "tasks: demo | demo-bm25 | cn-bm25-test | cn-bm25-dev | mmdocir-smoke | mmdocir-full | mmdocir-bm25 | evaluate-mmdocir | check"
    Write-Host "Each task uses the project .venv and prints its commit, config, dataset/split, and output. See docs/02-commands.md."
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
    Show-ExpHeader -ExpId "EXP-001" -EnvName "uv + colpali extra (CUDA)" -Config "configs/experiments/mmdocir_colpali_smoke.yaml" -Dataset "mmdocir_evaluation" -SplitName "-" -Output "runs/retrieval/mmdocir_colpali_smoke/<timestamp>"
    Write-Host "prepare: writing the 1-document smoke dataset to data/processed/mmdocir_evaluation_smoke"
    Invoke-Mdr @("prepare","--dataset","mmdocir_evaluation","--limit-docs","1","--output-dataset","mmdocir_evaluation_smoke")
    Invoke-ColpaliMdr @("retrieve","--config","configs/experiments/mmdocir_colpali_smoke.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/mmdocir_colpali_smoke/latest")
  }
  "mmdocir-full" {
    if (-not $env:HF_HOME) { $env:HF_HOME = "artifacts/hf_cache" }
    Assert-FileExists "configs/experiments/mmdocir_colpali.yaml" "full baseline config, see configs/README.md"
    Assert-FileExists "data/processed/mmdocir_evaluation/documents.parquet" "run mdr prepare --dataset mmdocir_evaluation without --limit-docs"
    Assert-MmdocirFullData
    Show-ExpHeader -ExpId "EXP-002" -EnvName "uv + colpali extra (CUDA)" -Config "configs/experiments/mmdocir_colpali.yaml" -Dataset "mmdocir_evaluation" -SplitName "-" -Output "runs/retrieval/mmdocir_colpali/<timestamp>"
    Write-Host "Phase 1A full baseline top_k=20; embedding cache: artifacts/colpali/"
    Invoke-ColpaliMdr @("retrieve","--config","configs/experiments/mmdocir_colpali.yaml")
    Invoke-Mdr @("evaluate","--run","runs/retrieval/mmdocir_colpali/latest")
  }
  "mmdocir-bm25" {
    Assert-FileExists "data/processed/mmdocir_evaluation/documents.parquet" "run mdr prepare --dataset mmdocir_evaluation without --limit-docs"
    Assert-MmdocirFullData
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
