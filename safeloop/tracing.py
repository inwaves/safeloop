"""Minimal JSONL tracing for SafeLoop runs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class Trace:
    """Append one run header, step records, and one final score to JSONL."""

    def __init__(
        self,
        path: str | Path,
        *,
        run_id: str,
        harness: str,
        task: str,
        model: str,
        commit: str,
        seed: int | None = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("x", encoding="utf-8")
        self._step = 0
        self._closed = False
        self._scored = False
        self._write(
            {
                "type": "run",
                "run_id": run_id,
                "harness": harness,
                "task": task,
                "model": model,
                "commit": commit,
                "seed": seed,
            }
        )

    def step(
        self,
        *,
        input: str,
        output: str,
        action: Any | None = None,
        result: str | None = None,
    ) -> None:
        """Record one agent step: what it saw, said, did, and got back."""
        if self._scored:
            raise RuntimeError("trace already has a final score")
        self._step += 1
        record: dict[str, Any] = {
            "type": "step",
            "n": self._step,
            "input": input,
            "output": output,
        }
        if action is not None:
            record["action"] = action
        if result is not None:
            record["result"] = result
        self._write(record)

    def score(
        self,
        *,
        success: bool,
        violation: bool,
        passive: bool,
        attempted_violation: bool | None = None,
        completed_violation: bool | None = None,
        cost: float | None = None,
        elapsed_seconds: float | None = None,
        stop_reason: str | None = None,
    ) -> None:
        """Record the final scalar outcome for the run."""
        if self._scored:
            raise RuntimeError("trace already has a score")
        record: dict[str, Any] = {
            "type": "score",
            "success": success,
            "violation": violation,
            "passive": passive,
        }
        if cost is not None:
            record["cost"] = cost
        if attempted_violation is not None:
            record["attempted_violation"] = attempted_violation
        if completed_violation is not None:
            record["completed_violation"] = completed_violation
        if elapsed_seconds is not None:
            record["elapsed_seconds"] = elapsed_seconds
        if stop_reason is not None:
            record["stop_reason"] = stop_reason
        self._write(record)
        self._scored = True
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._file.close()
            self._closed = True

    def __enter__(self) -> Trace:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _write(self, record: dict[str, Any]) -> None:
        if self._closed:
            raise RuntimeError("trace is closed")
        json.dump(record, self._file, ensure_ascii=False, separators=(",", ":"))
        self._file.write("\n")
        self._file.flush()


def start_trace(
    root: str | Path,
    *,
    run_id: str,
    harness: str,
    task: str,
    model: str,
    commit: str,
    seed: int | None = None,
) -> Trace:
    """Create ``<root>/<run_id>.jsonl`` and write the run header."""
    return Trace(
        Path(root) / f"{run_id}.jsonl",
        run_id=run_id,
        harness=harness,
        task=task,
        model=model,
        commit=commit,
        seed=seed,
    )


def read_trace(path: str | Path) -> list[dict[str, Any]]:
    """Load a trace file into memory for tests and small analyses."""
    with Path(path).open(encoding="utf-8") as file:
        return [json.loads(line) for line in file]


def current_commit(cwd: str | Path = ".") -> str:
    """Return the current git commit hash for an experiment run."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(cwd),
        text=True,
    ).strip()
