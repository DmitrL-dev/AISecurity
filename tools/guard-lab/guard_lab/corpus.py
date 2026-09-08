"""Bounded JSONL loading. Inputs are data; errors never include their content."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
import unicodedata

MAX_BYTES = 4 * 1024 * 1024
MAX_ROWS = 1000
MAX_TEXT_BYTES = 16384


class CorpusError(ValueError):
    """A fixed, non-sensitive input error code."""


@dataclass(frozen=True, repr=False)
class Record:
    row_id: str
    text: str
    label: str
    split: str


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _read_regular(directory: Path, name: str) -> bytes:
    if not name or name in {".", ".."} or Path(name).name != name or "\\" in name:
        raise CorpusError("INVALID_PATH")
    try:
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
        with os.fdopen(fd, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise CorpusError("INVALID_PATH")
            raw = source.read(MAX_BYTES + 1)
    except (OSError, ValueError):
        raise CorpusError("INVALID_PATH") from None
    if len(raw) > MAX_BYTES:
        raise CorpusError("FILE_TOO_LARGE")
    return raw


def load_corpus(directory: Path, name: str) -> list[Record]:
    raw = _read_regular(directory, name)
    try:
        lines = raw.decode("utf-8").split("\n")
        if lines[-1] == "":
            lines.pop()
    except UnicodeError:
        raise CorpusError("INVALID_JSONL") from None
    if len(lines) > MAX_ROWS:
        raise CorpusError("TOO_MANY_RECORDS")
    records = []
    seen = {}
    for number, line in enumerate(lines, 1):
        try:
            value = json.loads(line, object_pairs_hook=_unique_keys)
        except (ValueError, RecursionError):
            raise CorpusError("INVALID_JSONL") from None
        if (not isinstance(value, dict) or set(value) != {"text", "label", "split"}
                or not isinstance(value["text"], str)
                or value["label"] not in ("benign", "attack")
                or value["split"] not in ("test", "calibration")):
            raise CorpusError("INVALID_RECORD")
        text = value["text"]
        try:
            if not text.strip() or len(text.encode("utf-8")) > MAX_TEXT_BYTES:
                raise ValueError
        except (UnicodeError, ValueError):
            raise CorpusError("INVALID_RECORD") from None
        identity = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
        if identity in seen:
            code = "SPLIT_OVERLAP" if seen[identity] != value["split"] else "DUPLICATE_TEXT"
            raise CorpusError(code)
        seen[identity] = value["split"]
        records.append(Record(f"row-{number:06}", text, value["label"], value["split"]))
    if not any(record.split == "test" for record in records):
        raise CorpusError("NO_TEST_RECORDS")
    return records
