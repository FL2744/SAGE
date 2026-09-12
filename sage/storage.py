import json
import os
from contextlib import contextmanager
from pathlib import Path
import fcntl


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@contextmanager
def lock(project):
    project.mkdir(parents=True, exist_ok=True)
    with (project / ".lock").open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another SAGE process is using this project.")
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
