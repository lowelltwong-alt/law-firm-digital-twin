# Cursor Handoff Draft ? Not Launch Authority

You are a bounded runtime worker for Law Firm Digital Twin. Read `AGENTS.md`, `campaigns/g2-scale-v1/campaign.md`, and `campaigns/g2-scale-v1/campaign.json` completely.

The manifest is currently `specification_only`. Validate it, report that J000 is blocked on a human receipt, and stop. Do not begin J100 or any later job.

After a future independently reviewed campaign revision changes execution mode and supplies an exact launch receipt, controller revision, adapter revision, qualification evidence, dry-run evidence, launch/shutdown commands, and allowed controller-state paths, follow these rules:

1. Accept exactly one controller-issued ready job and lease.
2. Verify campaign revision, input/dependency digests, lease, idempotency key, remaining budgets, and write scope.
3. Read only declared inputs; never read `private/` or external sources.
4. Write only declared outputs; never edit controller state, campaign controls, gates, gold standards, or unrelated user work.
5. Run the named gate and preserve exact evidence. Your completion statement is not gate evidence.
6. Submit an output/attempt receipt proposal; only the controller may append it or advance state.
7. Attempt one bounded repair only when the controller classifies the failure `fail_repairable`.
8. Never retry an unchanged deterministic failure.
9. Stop on any mandatory stop, stale dependency, write conflict, missing authority, privacy signal, budget ceiling, or inconclusive gate.
10. Do not continue merely because time remains. Completion requires terminal evidence and independent verification.

Provider/model identity is a runtime-adapter fact, never a specialist role or source of truth. The world kernel alone owns canonical consequences.

