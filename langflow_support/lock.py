"""Simple file-based lock to serialize Langflow sync operations."""

from __future__ import annotations

import os
import socket
import time
from pathlib import Path
from contextlib import contextmanager

LOCK_PATH = Path("langflow/.edit.lock")


def _lock_contents() -> str:
    hostname = socket.gethostname()
    pid = os.getpid()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    return f"host={hostname}\npid={pid}\ntimestamp={timestamp}\n"


@contextmanager
def langflow_lock(timeout: float = 0.0):
    """Context manager acquiring the Langflow edit lock."""

    deadline = time.time() + timeout if timeout else None
    while True:
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, _lock_contents().encode("utf-8"))
            os.close(fd)
            break
        except FileExistsError:
            if deadline and time.time() > deadline:
                raise RuntimeError(
                    f"Langflow edit lock already held. Details:\n{LOCK_PATH.read_text()}"
                )
            time.sleep(0.2)

    try:
        yield
    finally:
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:  # pragma: no cover
            pass
