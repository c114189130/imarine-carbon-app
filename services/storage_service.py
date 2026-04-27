import json
from pathlib import Path
from typing import Any, List


def ensure_json_file(filepath: Path, default_data: Any = None) -> None:
    if not filepath.exists():
        write_json(filepath, default_data if default_data is not None else [])


def read_json(filepath: Path, default: Any = None) -> Any:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(filepath: Path, data: Any) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)