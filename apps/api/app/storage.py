import hashlib
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Protocol


class DocumentStorage(Protocol):
    def store(self, data: bytes) -> str: ...
    def read(self, digest: str) -> bytes: ...


class LocalStorage:
    def __init__(self, directory: Path):
        self.directory = directory

    def _path(self, digest: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid document asset ID")
        return self.directory / f"{digest}.pdf"

    def store(self, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        destination = self._path(digest)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if destination.exists():
            return digest
        with NamedTemporaryFile(dir=self.directory, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            try:
                temporary.write(data)
                temporary.close()
                os.replace(temporary_path, destination)
            finally:
                temporary_path.unlink(missing_ok=True)
        return digest

    def read(self, digest: str) -> bytes:
        return self._path(digest).read_bytes()
