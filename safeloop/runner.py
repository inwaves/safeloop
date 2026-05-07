"""Evaluation runner for one harness/model/suite combination."""

from __future__ import annotations

import json
import re
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from safeloop.harness import Harness
from safeloop.models import ModelClient
from safeloop.tasks import TaskWorld
from safeloop.tracing import current_commit, start_trace


@dataclass(frozen=True)
class Attempt:
    attempt_id: str
    task: str
    harness: str
    model: str
    seed: int
    trace: str
    success: bool
    violation: bool
    passive: bool
    attempted_violation: bool
    completed_violation: bool
    cost: float
    elapsed_seconds: float
    stop_reason: str


def run_suite(
    *,
    suite: list[TaskWorld],
    suite_name: str,
    harness: Harness,
    model_name: str,
    model: ModelClient,
    out_dir: str | Path,
    k: int,
    commit: str | None = None,
    max_seconds: float | None = None,
    max_cost: float | None = None,
) -> dict[str, Any]:
    _validate_limits(max_seconds=max_seconds, max_cost=max_cost)
    out = Path(out_dir)
    traces = out / "traces"
    out.mkdir(parents=True, exist_ok=True)
    traces.mkdir(parents=True, exist_ok=True)

    attempts_path = out / "attempts.jsonl"
    if attempts_path.exists():
        raise FileExistsError(f"attempts already exist: {attempts_path}")

    commit = commit or current_commit()
    attempts: list[Attempt] = []

    for task in suite:
        for seed in range(k):
            attempt = run_attempt(
                task=task,
                suite_name=suite_name,
                harness=harness,
                model_name=model_name,
                model=model,
                trace_dir=traces,
                seed=seed,
                commit=commit,
                max_seconds=max_seconds,
                max_cost=max_cost,
            )
            attempts.append(attempt)
            with attempts_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(asdict(attempt), separators=(",", ":")) + "\n")

    summary = summarize_attempts(attempts)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def run_attempt(
    *,
    task: TaskWorld,
    suite_name: str,
    harness: Harness,
    model_name: str,
    model: ModelClient,
    trace_dir: Path,
    seed: int,
    commit: str,
    max_seconds: float | None = None,
    max_cost: float | None = None,
) -> Attempt:
    _validate_limits(max_seconds=max_seconds, max_cost=max_cost)
    attempt_id = f"{task.id}-seed-{seed}-{uuid.uuid4().hex[:8]}"
    actions: list[dict[str, Any]] = []
    last_output = ""
    total_cost = 0.0
    start = time.monotonic()
    stop_reason = "max_steps"

    with tempfile.TemporaryDirectory(prefix="safeloop-task-") as tmp:
        root = Path(tmp)
        task.setup(root)
        messages = [
            {"role": "system", "content": harness.system_message},
            {"role": "user", "content": task.prompt},
        ]

        with start_trace(
            trace_dir,
            run_id=attempt_id,
            harness=harness.name,
            task=task.id,
            model=model_name,
            commit=commit,
            seed=seed,
        ) as trace:
            for _ in range(harness.max_steps):
                limit_reason = _limit_stop_reason(
                    start=start,
                    cost=total_cost,
                    max_seconds=max_seconds,
                    max_cost=max_cost,
                )
                if limit_reason:
                    stop_reason = limit_reason
                    break

                visible_messages = harness.apply_history_policy(messages)
                reply = model.complete(visible_messages)
                total_cost += reply.cost
                output = reply.text.strip()
                action = parse_action(output)
                limit_reason = _limit_stop_reason(
                    start=start,
                    cost=total_cost,
                    max_seconds=max_seconds,
                    max_cost=max_cost,
                )

                if action:
                    tool_action = task.record_action(action)
                    actions.append(tool_action)
                    if limit_reason:
                        stop_reason = limit_reason
                        tool_action["completed"] = False
                        trace.step(
                            input=render_messages(visible_messages),
                            output=output,
                            action=tool_action,
                        )
                        break
                    result = task.execute(
                        root,
                        action,
                        control_policy=harness.control_policy,
                    )
                    tool_action["completed"] = result.completed
                    if result.blocked:
                        tool_action["blocked"] = True
                    trace.step(
                        input=render_messages(visible_messages),
                        output=output,
                        action=tool_action,
                        result=result.observation,
                    )
                    messages.append({"role": "assistant", "content": output})
                    messages.append(
                        {
                            "role": "user",
                            "content": harness.render_observation(result.observation),
                        }
                    )
                    continue

                trace.step(
                    input=render_messages(visible_messages),
                    output=output,
                )
                last_output = output
                stop_reason = limit_reason or "agent_text"
                break

            score = task.score(
                root,
                actions=actions,
                output=last_output,
                stop_reason=stop_reason,
            )
            success = score.success
            violation = score.violation
            attempted_violation = score.attempted_violation
            completed_violation = score.completed_violation
            elapsed_seconds = time.monotonic() - start
            passive = score.passive
            trace.score(
                success=success,
                violation=violation,
                passive=passive,
                attempted_violation=attempted_violation,
                completed_violation=completed_violation,
                cost=total_cost,
                elapsed_seconds=elapsed_seconds,
                stop_reason=stop_reason,
            )

    return Attempt(
        attempt_id=attempt_id,
        task=task.id,
        harness=harness.name,
        model=model_name,
        seed=seed,
        trace=f"traces/{attempt_id}.jsonl",
        success=success,
        violation=violation,
        passive=passive,
        attempted_violation=attempted_violation,
        completed_violation=completed_violation,
        cost=total_cost,
        elapsed_seconds=elapsed_seconds,
        stop_reason=stop_reason,
    )


def parse_action(text: str) -> dict[str, Any] | None:
    stripped = _strip_code_fence(text.strip())
    data = _first_json_object(stripped)
    if data is None:
        return None

    action = data.get("action") or data.get("tool")
    if not action:
        return None

    parsed: dict[str, Any] = {"action": str(action)}
    args = data.get("args") if isinstance(data.get("args"), dict) else {}
    for key, value in {**data, **args}.items():
        if key not in {"action", "tool", "args"}:
            parsed[key] = value
    return parsed


def _first_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            data, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def summarize_attempts(attempts: list[Attempt]) -> dict[str, Any]:
    n = len(attempts)
    if n == 0:
        return {"attempts": 0}
    return {
        "attempts": n,
        "success_rate": sum(a.success for a in attempts) / n,
        "violation_rate": sum(a.violation for a in attempts) / n,
        "attempted_violation_rate": sum(a.attempted_violation for a in attempts) / n,
        "completed_violation_rate": sum(a.completed_violation for a in attempts) / n,
        "passive_rate": sum(a.passive for a in attempts) / n,
        "total_cost": sum(a.cost for a in attempts),
        "total_elapsed_seconds": sum(a.elapsed_seconds for a in attempts),
        "stop_reasons": _stop_reason_counts(attempts),
    }


def render_messages(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{m['role'].upper()}:\n{m['content']}" for m in messages)


def default_out_dir(suite: str, harness: str, model: str) -> Path:
    safe_model = re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return Path("runs") / f"{suite}_{harness}_{safe_model}_{stamp}"


def _strip_code_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def _limit_stop_reason(
    *,
    start: float,
    cost: float,
    max_seconds: float | None,
    max_cost: float | None,
) -> str | None:
    if max_seconds is not None and time.monotonic() - start >= max_seconds:
        return "max_seconds"
    if max_cost is not None and cost >= max_cost:
        return "max_cost"
    return None


def _validate_limits(*, max_seconds: float | None, max_cost: float | None) -> None:
    if max_seconds is not None and max_seconds < 0:
        raise ValueError("max_seconds must be >= 0")
    if max_cost is not None and max_cost < 0:
        raise ValueError("max_cost must be >= 0")


def _stop_reason_counts(attempts: list[Attempt]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for attempt in attempts:
        counts[attempt.stop_reason] = counts.get(attempt.stop_reason, 0) + 1
    return counts
