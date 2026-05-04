# SafeLoop

SafeLoop is an early research project on **harness search for safer agents**.

The core question:

> Can we automatically discover agent harnesses that make a fixed base model behave more safely, without simply blocking actions or adding external oversight, and do those safety improvements generalize out of distribution?

## Motivation

The deployed agent is not just the model. It is the model plus the surrounding loop: prompts, tools, memory, summaries, scratchpad format, state representation, observation formatting, retry logic, and the interface to the environment.

That harness is part of the model's inference-time cognitive environment. It controls what the model sees, remembers, treats as salient, and experiences as the natural next action. So it should be possible for harness design to shift behavior in safety-relevant ways, not just capability-relevant ways.

This is adjacent to AI control, but not quite the same thing. The boring control version is "do not let the agent do dangerous actions" or "ask a human before a big change." That is useful, but it is not the interesting claim here. The interesting claim is that harnesses may steer the model into safer regions of behavior by changing the trajectory distribution, much like a souped-up prompting / in-context learning setup.

## Search framing

The analogy is neural architecture search, but over agent-loop architecture rather than model architecture.

Hold fixed:

- base model
- task suite
- tool permissions
- budget
- verifier / scoring setup

Search over:

- system prompt structure
- scratchpad format
- state summary format
- memory policy
- tool schema / action ontology
- observation formatting
- reflection cadence
- how uncertainty, scope, and consequences are represented
- what the agent sees about past failed attempts

The objective should be a safety/capability tradeoff, not "safest" in the abstract:

- high task success
- low safety violation rate
- low scope violation rate
- low over-refusal / paralysis
- reasonable token and wall-clock overhead

## Key constraint

Do not let the search find trivial safety wrappers.

Rules of the game:

- no removing the dangerous tools
- no blanket refusal policies
- no always asking user approval
- no hard-coded task-specific rules
- no optimizing on the OOD test set

The question is whether the scaffold changes the model's effective behavior distribution, not whether we can disable the task.

## Minimal experiment

1. Build an in-distribution suite of agent tasks with realistic safety pressure:
   - coding tasks where shortcutting tests would improve apparent score
   - filesystem tasks where reading out-of-scope files would help
   - research tasks where overclaiming or fabricating sources helps
   - optimization tasks where violating a constraint improves reward
   - multi-step web tasks where privacy/scope violations make the task easier
2. Define a held-out OOD suite:
   - new task families
   - longer trajectories
   - different tools
   - different safety failure modes
3. Search for harness variants on the in-distribution suite.
4. Evaluate whether the discovered harness transfers OOD.
5. Compare against:
   - bare ReAct / default tool loop
   - hand-designed safety scaffold
   - naive prompt-only safety instruction
   - maybe a simple control wrapper, to separate steering from blocking

## What would count as a result?

Positive result:

- Harness search finds scaffolds that reduce unsafe behavior without tanking task success.
- Some components transfer across task families.
- This suggests inference-time scaffold design is a real safety lever.

Negative result:

- Search finds brittle hacks.
- Gains vanish OOD.
- Safety improvements come mostly from hidden task-specific blocking.
- This suggests harness optimization is prone to benchmark overfitting and should be treated cautiously.

Either result is useful. The core empirical object is OOD generalization of safety improvements induced by scaffold design.

## Related work

- [Meta-Harness: End-to-End Optimization of Model Harnesses](https://arxiv.org/abs/2603.28052) makes the performance-side case: a lot of behavior lives in the harness, and search over harness code can improve model performance while keeping weights fixed. SafeLoop asks the safety version and cares centrally about OOD generalization.
- [ClawsBench: Evaluating Capability and Safety of LLM Productivity Agents in Simulated Workspaces](https://arxiv.org/abs/2604.05172) is important evidence that scaffolding can dominate model choice in productivity agents and that capability and safety do not simply co-vary.
- [Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses](https://arxiv.org/abs/2604.25850) and [Synthesizing Multi-Agent Harnesses for Vulnerability Discovery](https://arxiv.org/abs/2604.20801) are nearby automated harness-search papers, currently more capability/security-task oriented than safety-generalization oriented.
- [SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents](https://arxiv.org/abs/2506.15740) is relevant as a source of multi-step side-task / covert-objective evaluations.

## Open questions

- What safety task suite is small enough to run but rich enough that harness overfitting is meaningful?
- What should count as OOD? New tasks, new tools, new models, or all three?
- How do we distinguish genuine behavior steering from hidden permissioning or over-refusal?
- Can search methods operate over natural-language prompts only, or should they edit harness code directly?
- Is the right proposer a frontier coding agent reading raw traces, as in Meta-Harness, or a simpler evolutionary / bandit loop?
- How much observability is enough for the search process to debug why a harness failed?
- Does a harness found for one model transfer to another model, or are scaffold effects highly model-specific?

## Status

Idea sketch. No implementation yet.
