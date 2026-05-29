from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from mmdocrag.paths import project_root


# 反序列化 yaml 数据
def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

# 把 YAML 配置文件读成 Python 字典之后，再把里面的环境变量占位符替换成真实路径后的字典
def expand_env(value: Any) -> Any:
    if isinstance(value, str):
        expanded = value
        for key, env_value in os.environ.items():
            expanded = expanded.replace("${" + key + "}", env_value)
        expanded = expanded.replace("${MMDOC_RAG_DATA_ROOT}", str(project_root() / "data"))
        expanded = expanded.replace("${MMDOC_RAG_RUNS_ROOT}", str(project_root() / "runs"))
        expanded = expanded.replace("${MMDOC_RAG_ARTIFACT_ROOT}", str(project_root() / "artifacts"))
        return expanded
    if isinstance(value, dict):
        return {key: expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_env(item) for item in value]
    return value

# 反序列化 yaml 字典数据
def load_config(path: Path) -> dict[str, Any]:
    return expand_env(load_yaml(path))
