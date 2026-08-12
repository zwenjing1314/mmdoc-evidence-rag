from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def data_root() -> Path:
    return Path(os.getenv("MMDOC_RAG_DATA_ROOT", project_root() / "data")).resolve()


def runs_root() -> Path:
    return Path(os.getenv("MMDOC_RAG_RUNS_ROOT", project_root() / "runs")).resolve()


def artifacts_root() -> Path:
    return Path(os.getenv("MMDOC_RAG_ARTIFACT_ROOT", project_root() / "artifacts")).resolve()


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root() / path
