#!/usr/bin/env python3
"""Recent files manager with persistence."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

MAX_RECENT_FILES = 10


class RecentFilesManager:
    """Manages a list of recently opened files."""

    def __init__(self, max_size: int = MAX_RECENT_FILES) -> None:
        self.max_size = max_size
        self._files: deque[str] = deque()
        self._config_path = Path.home() / ".image_processor" / "recent_files.json"
        self._load()

    def _load(self) -> None:
        if not self._config_path.is_file():
            return
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._files = deque(data[: self.max_size])
        except (json.JSONDecodeError, OSError):
            self._files.clear()

    def _save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(list(self._files), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add(self, path: Path | str) -> None:
        path_str = str(Path(path).expanduser().resolve())
        if path_str in self._files:
            self._files.remove(path_str)
        self._files.appendleft(path_str)
        while len(self._files) > self.max_size:
            self._files.pop()
        self._save()

    def get_all(self) -> list[str]:
        return list(self._files)

    def clear(self) -> None:
        self._files.clear()
        self._save()
