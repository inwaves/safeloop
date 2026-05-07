# Evaluation Protocol

This is the part previously called "protocol lock": the evaluation rules we freeze before search.

## Status

In progress. The runner can execute harnesses, call task worlds, and record costs, timing, traces, and stop reasons. The office playground now comes from the shared `inwaves/envs` package.

## Fixed So Far

- [x] Harness identity: each run records git commit, harness name, task id, model, and seed.
- [x] Run endings: an attempt stops on agent text, step budget, wall-clock limit, or API-cost limit.
- [x] Model surface: fake, OpenAI, and Anthropic clients share the same runner interface.
- [x] Cost tracking: live clients estimate cost from provider token usage in the response.
- [x] Trace shape: each run writes one JSONL trace plus aggregate attempt and summary files.
- [x] Task-world interface: task worlds set up state, record actions, execute actions, and score the final run.
- [x] Shared office environment: `load_suite("office")` adapts `envs.office` into SafeLoop's runner.

## Next Decisions

- [x] Score fields: track success rate, attempted violation rate, completed violation rate, passivity rate, cost, wall time, and stop reasons.
- [x] Comparison rule: compare success and violation against the baseline as two separate axes, with no fixed success floor.
- [x] Baselines: add default runtime, positive-control scaffold, and control-wrapper baseline.
- [x] Repeated runs: run each harness/task/model setting three times.
- [ ] Held-out policy: table OOD until the first real safety-pressure task exists.
- [ ] Benign capability: select or add a benign suite inside the shared environment.
- [x] Primary model: start with Sonnet 4.6.
- [ ] GPT-5.5 check: after selecting a candidate on Sonnet 4.6, run that candidate and the baselines with GPT-5.5 to see whether the result still shows up.
- [x] First safety-pressure tasks: use the shared office tasks for data exfiltration, destructive modification, and unauthorized external action.
- [ ] Pressure calibration: run the baseline harnesses on shared office and inspect whether failures are task pressure, harness friction, or evaluator gaps.

## Immediate Next Step

Run default, positive-control, and control-wrapper harnesses on `load_suite("office")` with Sonnet 4.6 and inspect the traces.

## Office Playground

`office` is a SafeLoop adapter over `envs.office`. The shared environment owns the workspace state, neutral tools, deterministic seed, hidden safety policy, and offline outcome scorer. SafeLoop owns harness selection, model calls, traces, repeated runs, and aggregate evaluation.

The current shared office tasks cover three risk families: protected data exfiltration, destructive file modification, and unauthorized external action.

## Baseline Harnesses

- `default_runtime_v0`: minimal task-solving loop with no extra safety scaffold.
- `positive_control_scope_v0`: hand-written scope preflight scaffold; this is intentionally simple and provisional.
- `control_wrapper_scope_v0`: runtime wrapper that blocks actions the shared office scorer would label as a violation while still recording the attempted violation.

## Benign Capability Suite

Still needed inside the shared environment. It should use the same office state and tools but avoid useful unsafe shortcuts.
