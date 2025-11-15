"""Helpers to read cached ingestion artifacts for reporting layers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class CachedEntry:
    source_id: str
    language: Optional[str]
    clean_path: Path
    raw_path: Path
    fetched_at: str
    text_preview: List[str]
    metadata: Dict[str, object]
    metadata_path: Path

    def read_full_text(self) -> str:
        try:
            return self.clean_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""


class CachedSourceRepository:
    """Index metadata files emitted by the SourceFetcher."""

    def __init__(self, cache_root: Optional[Path] = None):
        root = Path(cache_root or Path(__file__).resolve().parents[2] / "data" / "cache_store")
        self.meta_dir = root / "metadata"
        self.root = root

    def get_recent_entries(self, limit: Optional[int] = None) -> List[CachedEntry]:
        if not self.meta_dir.exists():
            return []
        files = sorted(self.meta_dir.glob("**/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if limit is not None:
            files = files[:limit]

        entries: List[CachedEntry] = []
        for file_path in files:
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            entries.append(
                CachedEntry(
                    source_id=payload.get("source_id", "unknown"),
                    language=payload.get("language"),
                    clean_path=Path(payload.get("clean_path", "")),
                    raw_path=Path(payload.get("raw_path", "")),
                    fetched_at=payload.get("fetched_at", ""),
                    text_preview=payload.get("text_preview", []),
                    metadata=payload.get("metadata", {}),
                    metadata_path=file_path,
                )
            )
        return entries
