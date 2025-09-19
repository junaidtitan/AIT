"""Local checkpoint helpers for LangGraph pipelines."""

from __future__ import annotations

import asyncio
import threading
from collections import ChainMap
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    PendingWrite,
)
from langchain_core.runnables.config import RunnableConfig

from src.config import settings


def _thread_id_from_config(config: RunnableConfig) -> str:
    configurable = dict(config).get("configurable", {}) or {}
    thread_id = configurable.get("thread_id")
    if thread_id:
        return str(thread_id)
    run_id = config.get("run_id")
    if run_id:
        return str(run_id)
    return "default"


def _checkpoint_id_from_config(config: RunnableConfig) -> Optional[str]:
    configurable = dict(config).get("configurable", {}) or {}
    checkpoint_id = configurable.get("checkpoint_id")
    return str(checkpoint_id) if checkpoint_id else None


class FileCheckpointSaver(BaseCheckpointSaver):
    """Persist checkpoints as JSON files inside a directory."""

    def __init__(self, directory: Path) -> None:
        super().__init__()
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()


    def _jsonify(self, value):
        if isinstance(value, ChainMap):
            merged = {}
            for mapping in value.maps:
                merged.update(self._jsonify(mapping))
            return merged
        if hasattr(value, "model_dump"):
            return self._jsonify(value.model_dump())
        if isinstance(value, dict):
            return {k: self._jsonify(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._jsonify(v) for v in value]
        if isinstance(value, tuple):
            return [self._jsonify(v) for v in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return repr(value)

    # ------------------------------------------------------------------
    # Synchronous helpers
    # ------------------------------------------------------------------

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = _thread_id_from_config(config)
        data = self._load_thread(thread_id)
        if not data["checkpoints"]:
            return None
        checkpoint_id = _checkpoint_id_from_config(config)
        if checkpoint_id and checkpoint_id in data["checkpoints"]:
            entry = data["checkpoints"][checkpoint_id]
        else:
            latest_id = sorted(data["checkpoints"].keys())[-1]
            entry = data["checkpoints"][latest_id]
        return CheckpointTuple(
            entry["config"],
            entry["checkpoint"],
            entry["metadata"],
            entry.get("parent_config"),
            entry.get("pending_writes", []),
        )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: Dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if config:
            thread_ids = [_thread_id_from_config(config)]
        else:
            thread_ids = [path.stem for path in self.directory.glob("*.json")]
        seen = set()
        for thread_id in thread_ids:
            if thread_id in seen:
                continue
            seen.add(thread_id)
            data = self._load_thread(thread_id)
            for checkpoint_id in sorted(data["checkpoints"].keys()):
                entry = data["checkpoints"][checkpoint_id]
                yield CheckpointTuple(
                    entry["config"],
                    entry["checkpoint"],
                    entry["metadata"],
                    entry.get("parent_config"),
                    entry.get("pending_writes", []),
                )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Dict[str, Any],
    ) -> RunnableConfig:
        thread_id = _thread_id_from_config(config)
        checkpoint_id = checkpoint["id"]
        with self._lock:
            data = self._load_thread(thread_id)
            entry = {
                "config": self._jsonify(self._sanitise_config(config)),
                "checkpoint": checkpoint,
                "metadata": self._jsonify(dict(metadata)),
                "parent_config": None,
                "pending_writes": [],
            }
            if isinstance(metadata, dict) and metadata.get("parent_config") is not None:
                entry["parent_config"] = self._jsonify(metadata.get("parent_config"))
            data["checkpoints"][checkpoint_id] = entry
            self._save_thread(thread_id, data)
        return config

    def put_writes(
        self,
        config: RunnableConfig,
        writes: list[PendingWrite],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = _thread_id_from_config(config)
        with self._lock:
            data = self._load_thread(thread_id)
            if not data["checkpoints"]:
                return
            latest_id = sorted(data["checkpoints"].keys())[-1]
            pending = [self._jsonify(write) for write in writes]
            data["checkpoints"][latest_id].setdefault("pending_writes", []).extend(pending)
            self._save_thread(thread_id, data)

    def delete_thread(self, thread_id: str) -> None:
        path = self.directory / f"{thread_id}.json"
        if path.exists():
            path.unlink()

    # ------------------------------------------------------------------
    # Async wrappers
    # ------------------------------------------------------------------

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return await asyncio.to_thread(self.get_tuple, config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: Dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ):
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Dict[str, Any],
    ) -> RunnableConfig:
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: list[PendingWrite],
        task_id: str,
        task_path: str = "",
    ) -> None:
        await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        await asyncio.to_thread(self.delete_thread, thread_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _thread_path(self, thread_id: str) -> Path:
        return self.directory / f"{thread_id}.json"

    def _load_thread(self, thread_id: str) -> Dict[str, Any]:
        path = self._thread_path(thread_id)
        if not path.exists():
            return {"checkpoints": {}}
        data = self.serde.loads(path.read_bytes())
        if "checkpoints" not in data:
            data["checkpoints"] = {}
        return data

    def _save_thread(self, thread_id: str, data: Dict[str, Any]) -> None:
        path = self._thread_path(thread_id)
        path.write_bytes(self.serde.dumps(data))

    def _sanitise_config(self, config: RunnableConfig) -> RunnableConfig:
        cfg = dict(config)
        if "callbacks" in cfg:
            cfg["callbacks"] = None
        return cfg


def get_default_checkpointer(workflow: str) -> FileCheckpointSaver | None:
    base_dir = settings.LANGGRAPH_CHECKPOINT_DIR
    if not base_dir:
        return None
    path = Path(base_dir)
    path.mkdir(parents=True, exist_ok=True)
    return FileCheckpointSaver(path / workflow)
