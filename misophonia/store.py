"""Persist user-enrolled example sounds locally, without network access."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf


class TargetStore:
    def __init__(self, base: Path | None = None):
        self.base = base or Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "MisophoniaDesktop"
        self.samples = self.base / "samples"
        self.index = self.base / "profiles.json"
        self.samples.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[dict[str, str]]:
        if not self.index.exists():
            return []
        records = json.loads(self.index.read_text(encoding="utf-8"))
        return [item for item in records if (self.samples / item["file"]).is_file()]

    def _save(self, records: list[dict[str, str]]) -> None:
        self.index.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_file(self, source: str | Path) -> dict[str, str]:
        source = Path(source)
        info = sf.info(str(source))
        if info.duration < 0.2 or info.duration > 30:
            raise ValueError("登録音は0.2秒～30秒のファイルにしてください。")
        if info.channels not in (1, 2):
            raise ValueError("登録音はモノラルかステレオにしてください。")
        new_id = uuid.uuid4().hex
        ext = source.suffix.lower()
        if ext not in (".wav", ".flac", ".ogg"):
            raise ValueError("登録可能な形式はWAV / FLAC / OGGです。")
        filename = new_id + ext
        shutil.copy2(source, self.samples / filename)
        record = {"id": new_id, "name": source.stem, "file": filename}
        records = self.list()
        records.append(record)
        self._save(records)
        return record

    def add_recording(self, audio: np.ndarray, rate: int) -> dict[str, str]:
        new_id = uuid.uuid4().hex
        filename = new_id + ".wav"
        sf.write(str(self.samples / filename), audio, rate, subtype="PCM_16")
        record = {"id": new_id, "name": "録音 " + new_id[:6], "file": filename}
        records = self.list()
        records.append(record)
        self._save(records)
        return record

    def delete(self, ids: set[str]) -> None:
        records = self.list()
        remaining = []
        for record in records:
            if record["id"] in ids:
                (self.samples / record["file"]).unlink(missing_ok=True)
            else:
                remaining.append(record)
        self._save(remaining)

    def path(self, record: dict[str, str]) -> Path:
        return self.samples / record["file"]
