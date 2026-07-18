# Gate Evidence Contract

Gate results are exactly `pass`, `fail_repairable`, `fail_terminal`, `blocked_human`, or `inconclusive`. Only `pass` satisfies auto-advance.

Deterministic gates record the command, exit status, expected test count or schema assertions, input/output digests, validator revision, and non-sensitive evidence path. Independent gates add checker identity and the bounded rubric. Human gates require an affirmative revision-bound receipt.

Gate evidence belongs under `checks/g2-scale-v1/` or controller-owned `.campaign-state/g2-scale-v1/`. Workers may propose evidence but cannot edit controller state or their own acceptance definitions.

Revalidate when an input digest, core or adapter revision, validator, privacy/authority boundary, or scope changes. Preserve failed evidence through the one allowed repair.

