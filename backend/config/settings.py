from __future__ import annotations

import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_ROOT = PROJECT_ROOT / "data"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _read_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if not path.exists():
        return data
    stack: list[tuple[int, dict[str, Any]]] = [(-1, data)]
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        elif value.startswith("[") and value.endswith("]"):
            parent[key] = [item.strip().strip('"').strip("'") for item in value[1:-1].split(",") if item.strip()]
        else:
            parent[key] = _parse_scalar(value)
    return data


def load_env_file(path: Path | None = None) -> None:
    path = path or PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_rag_config() -> dict[str, Any]:
    load_env_file()
    cfg = _read_simple_yaml(BACKEND_ROOT / "config" / "rag.yaml")
    vector = cfg.setdefault("vector_store", {})
    splitter = cfg.setdefault("splitter", {})
    embedding = cfg.setdefault("embedding", {})
    vector.setdefault("provider", os.getenv("RAG_VECTOR_PROVIDER", "keyword"))
    vector.setdefault("persist_directory", "outputs/chroma_db")
    vector.setdefault("collection_name", "fagent_knowledge")
    vector.setdefault("use_chroma", os.getenv("RAG_USE_CHROMA", "false").lower() == "true")
    splitter.setdefault("chunk_size", int(os.getenv("RAG_CHUNK_SIZE", "700")))
    splitter.setdefault("chunk_overlap", int(os.getenv("RAG_CHUNK_OVERLAP", "90")))
    cfg.setdefault("data_path", "data/knowledge")
    cfg.setdefault("allowed_file_types", ["txt", "md", "csv", "json", "pdf"])
    cfg.setdefault("top_k", int(os.getenv("RAG_TOP_K", "4")))
    embedding.setdefault("provider", os.getenv("EMBEDDING_PROVIDER", "keyword"))
    embedding.setdefault("model", os.getenv("EMBEDDING_MODEL", "local-keyword"))
    return cfg


def load_agent_config() -> dict[str, Any]:
    """Load the DeepSeek diagnosis configuration."""
    load_env_file()
    api_key = os.getenv("DIAGNOSIS_AGENT_API_KEY", "")
    return {
        "config_name": "DIAGNOSIS_AGENT",
        "llm_provider": os.getenv("DIAGNOSIS_AGENT_PROVIDER", "rule"),
        "llm_model": os.getenv("DIAGNOSIS_AGENT_MODEL", ""),
        "llm_api_key": api_key,
        "llm_base_url": os.getenv("DIAGNOSIS_AGENT_BASE_URL", ""),
        "reasoning_effort": os.getenv("DIAGNOSIS_AGENT_REASONING_EFFORT", "high"),
        "mode": "llm" if api_key else "rule",
    }


def load_document_agent_config() -> dict[str, Any]:
    """Load the PR #6 DashScope/Qwen document-analysis configuration."""
    load_env_file()
    api_key = os.getenv("DOCUMENT_AGENT_API_KEY", "")
    return {
        "config_name": "DOCUMENT_AGENT",
        "llm_provider": os.getenv("DOCUMENT_AGENT_PROVIDER", "dashscope"),
        "llm_model": os.getenv("DOCUMENT_AGENT_MODEL", "qwen-plus"),
        "llm_api_key": api_key,
        "llm_base_url": os.getenv(
            "DOCUMENT_AGENT_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        "reasoning_effort": "",
        "mode": "llm" if api_key else "disabled",
    }