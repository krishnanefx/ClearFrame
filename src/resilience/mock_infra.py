"""Mock SQS/DynamoDB infrastructure for resilience tests."""

from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class MockSQSQueue:
    name: str
    maxsize: int = 1000
    _queue: queue.Queue = field(init=False)

    def __post_init__(self) -> None:
        self._queue = queue.Queue(maxsize=self.maxsize)

    def send_message(self, body: Dict[str, Any]) -> None:
        self._queue.put_nowait({"body": body, "timestamp": time.time()})

    def receive_messages(self, max_messages: int = 1) -> list[Dict[str, Any]]:
        messages = []
        for _ in range(max_messages):
            try:
                messages.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return messages


@dataclass
class MockDynamoTable:
    name: str
    file_path: Path
    lock: threading.Lock = field(default_factory=threading.Lock)

    def put_item(self, item: Dict[str, Any]) -> None:
        with self.lock:
            rows = self._read_all()
            rows.append(item)
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text(json.dumps(rows, indent=2))

    def _read_all(self) -> list[Dict[str, Any]]:
        if not self.file_path.exists():
            return []
        try:
            return json.loads(self.file_path.read_text())
        except json.JSONDecodeError:
            return []
