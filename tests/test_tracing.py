import tempfile
import unittest
from pathlib import Path

from safeloop.tracing import read_trace, start_trace


class TraceTests(unittest.TestCase):
    def test_trace_writes_run_steps_and_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with start_trace(
                tmp,
                run_id="run-1",
                harness="basic",
                task="scope-001",
                model="model-a",
                commit="abc123",
                seed=7,
            ) as trace:
                trace.step(
                    input="Use allowed files only.",
                    output="I will inspect allowed/a.txt.",
                    action={"tool": "read_file", "args": {"path": "allowed/a.txt"}},
                    result="answer material",
                )
                trace.step(
                    input="answer material",
                    output="Final answer.",
                )
                trace.score(success=True, violation=False, passive=False, cost=0.01)

            records = read_trace(Path(tmp) / "run-1.jsonl")

        self.assertEqual([record["type"] for record in records], ["run", "step", "step", "score"])
        self.assertEqual(records[0]["commit"], "abc123")
        self.assertEqual(records[0]["harness"], "basic")
        self.assertEqual(records[1]["n"], 1)
        self.assertEqual(records[2]["n"], 2)
        self.assertEqual(records[3]["success"], True)
        self.assertEqual(records[3]["violation"], False)
        self.assertEqual(records[3]["passive"], False)

    def test_trace_does_not_overwrite_existing_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with start_trace(
                tmp,
                run_id="run-1",
                harness="basic",
                task="scope-001",
                model="model-a",
                commit="abc123",
            ):
                pass

            with self.assertRaises(FileExistsError):
                start_trace(
                    tmp,
                    run_id="run-1",
                    harness="basic",
                    task="scope-001",
                    model="model-a",
                    commit="abc123",
                )

    def test_trace_rejects_multiple_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with start_trace(
                tmp,
                run_id="run-1",
                harness="basic",
                task="scope-001",
                model="model-a",
                commit="abc123",
            ) as trace:
                trace.score(success=True, violation=False, passive=False)

                with self.assertRaises(RuntimeError):
                    trace.score(success=True, violation=False, passive=False)

    def test_trace_rejects_steps_after_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with start_trace(
                tmp,
                run_id="run-1",
                harness="basic",
                task="scope-001",
                model="model-a",
                commit="abc123",
            ) as trace:
                trace.score(success=True, violation=False, passive=False)

                with self.assertRaises(RuntimeError):
                    trace.step(input="late", output="late")


if __name__ == "__main__":
    unittest.main()
