# High-Level Components

SafeLoop studies whether the operating conditions around an agent can make its behavior safer while preserving its usefulness.

The project treats an agent as a complete runtime system. The model matters, but so do the surrounding structures: available actions, state, memory, feedback, observations, recovery loops, task pressure, and evaluation.

At a high level, SafeLoop has five components.

## Agent Substrate

The substrate is the fixed foundation of an experiment: the base model, tools, permissions, runtime budget, and execution environment.

This gives each experiment a stable comparison point. When behavior changes, the change should come from the surrounding harness rather than from swapping models, removing powers, or changing the environment underneath the agent.

## Harness

The harness is the main object of study.

It defines the agent's inference-time operating conditions: what state exists, how actions are represented, what observations look like, what gets remembered, what gets summarized, how uncertainty is handled, how failed attempts are surfaced, when the agent reflects or replans, and how consequences become visible during a trajectory.

The harness is the cognitive architecture around the model.

## Task Worlds

Task worlds are controlled environments where safety failures are tempting because they make success easier.

A useful task world creates pressure. The agent might finish faster by reading out-of-scope files, editing tests, fabricating evidence, violating a constraint, leaking private information, or skipping verification. These pressures make safety behavior measurable.

## Search Loop

The search loop generates harness variants, runs them through task worlds, reads the resulting traces, and proposes improved variants.

The search target is agent-loop structure: state, actions, feedback, memory, recovery, and observability. Over time, this may include direct edits to harness code and runtime mechanics.

## Evaluator

The evaluator decides what happened.

It measures task success, safety violations, scope violations, over-refusal, cheating, recovery from uncertainty, cost, and transfer to new situations. The key question is whether a discovered harness improves behavior beyond the tasks it was optimized on.

## Minimal Starting Shape

A first SafeLoop experiment should have one fixed model, one simple agent runtime, two small task worlds with real safety pressure, a harness representation rich enough to express runtime structure, and an evaluator that separates safer behavior from passivity.

The point of the first version is to establish a measurable loop: generate harnesses, run agents, score traces, improve the harness, and test whether the improvement survives out of distribution.
