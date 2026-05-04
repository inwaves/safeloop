# Roadmap

SafeLoop should grow by earning stronger claims one step at a time.

The roadmap starts with the smallest experiment that can show the core effect, then adds only the work needed to explain, bound, and test that effect.

## Phase 0: Establish the Effect

Phase 0 asks whether harness search can find safer behavior on a training suite, whether that behavior survives a frozen held-out suite, and whether it remains visible under a cheap second-model spot check.

Phase 0 has three parts: trace substrate, protocol lock, and small search.

### Trace Substrate

Build the run archive first. Every run should store the harness component files, compiled runtime config, task snapshot, seed, model version, tool version, messages, tool calls, observations, state transitions, evaluator labels, scalar scores, cost, wall time, and replay metadata.

The archive should be queryable by candidate, task, failure type, evaluator axis, and model. Phase 1 ablations depend on this substrate.

### Protocol Lock

Before search, fix the harness representation, search budget, evaluator contract, baselines, thresholds, and held-out policy.

The Phase 0 harness representation should be a directory of editable component files that compile into the fixed runtime. The initial components are action surface, state representation, observation renderer, memory policy, and verification/recovery policy. Tools and permissions stay fixed.

The evaluator should report separate axes: task success, attempted violation, completed violation, scope violation, passivity, benign capability, cost, and wall time. The passivity threshold and primary safety/capability tradeoff should be set before search begins.

The baselines are the default runtime, a hand-designed safety scaffold as a positive control, and a simple control-wrapper baseline to separate behavioral steering from blocking. Measure the noise floor by repeating the same harness across multiple seeds before interpreting improvements.

The OOD suite should be frozen before search and evaluated once after candidate selection. The benign capability suite should be held out from search as well.

The second-model spot check should run the final selected harness and the main baselines on another base model before Phase 1 begins.

### Small Search

The Phase 0 search method should be component-file, trace-reading proposal.

This is the smallest defensible version of the recent open-ended harness-search direction. [ADAS](https://arxiv.org/abs/2408.08435) frames meta agents that program new agent designs; [Meta-Harness](https://arxiv.org/abs/2603.28052) exposes source, scores, and execution traces through a filesystem; [Agentic Harness Engineering](https://arxiv.org/abs/2604.25850) emphasizes editable component files, layered experience, and prediction-backed edits; graph and DSL work such as [GPTSwarm](https://arxiv.org/abs/2402.16823), [AgentSquare](https://arxiv.org/abs/2410.06153), and [AgentFlow](https://arxiv.org/abs/2604.20801) shows richer search spaces available later.

In each iteration, the proposer reads prior scores and sampled traces, edits one or two component files, declares the expected movement on evaluator axes, passes an eligibility gate, runs on the ID suite, and logs the result.

The eligibility gate rejects tool removal, permission changes, blanket blocking, task-specific strings, held-out task references, and candidate changes that make replay or scoring impossible.

The result should fit into one of four outcomes:

| ID result | OOD result | Meaning |
| --- | --- | --- |
| improves | improves | Harness search found transferable safety structure. |
| improves | flat or regresses | Harnesses can improve safety locally; transfer remains an empirical question. |
| flat | flat | The current task signal, search space, evaluator, or budget is too weak. |
| safety improves, success collapses | any | The system found passivity. |

The goal of Phase 0 is a trustworthy trace-and-score loop: generate harnesses, run agents, score traces, improve the harness, and test the result out of distribution.

## Phase 1: Mechanism

If Phase 0 finds a transferable improvement, the next question is what caused it.

Take the winning harness apart. Ablate pieces, simplify it, compare traces, and identify which part of the agent architecture carried the gain: state representation, action structure, uncertainty handling, memory, recovery behavior, observability, or another mechanism.

The return is explanatory power. The project can move from "this harness worked" to "this part of agent architecture appears to steer behavior."

## Phase 2: Boundary

After identifying a plausible mechanism, test where it holds.

Add one carefully chosen task world that creates a different kind of safety pressure. The purpose is to test whether the same harness idea survives beyond the original setup.

The return is a sharper transfer claim. The result should show whether the mechanism generalizes beyond the first environment or belongs to a narrower behavioral regime.

## Phase 3: Portability

After the boundary is clearer, test portability more seriously.

Run the same discovered harness family across additional base models before doing any new search. Keep the comparison focused on transfer.

The return is portability evidence. The result should show whether the safety improvement is a model-specific interaction or a more general agent-design principle.

## Deferred Until Forced

Arbitrary code-level harness search, graph or DSL search, larger benchmark matrices, evaluator ensembles, latency optimization, and red-team suites should wait until one of the phases above creates a specific need for them.

The project should add machinery only when it strengthens the next claim.
