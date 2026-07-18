# Candidate lesson: cache expensive replay gates by exact immutable state

Status: locally verified candidate; DAD transport unavailable  
Baseline: 100 fresh Windows processes, 152.5 seconds, passing

Fresh-process replay is intentionally expensive because process startup is part
of the isolation proof. Do not weaken the gate by reusing one process. For
routine reruns, perform one fresh-process preflight and reuse a protected receipt
only when the following exact key is unchanged: harness revision, worker
revision, package source-tree hash, dependency-lock hashes, runtime/environment
hash, input commitment, replay-semantics hash, and required process count.

Any code, dependency, environment, input, semantics, or count change is a cache
miss and requires the full qualification. Validate the cached receipt before
reuse; keep it outside public fixtures; publish only a nonjoinable aggregate.
This optimization targets redundant startup I/O and preserves the original
isolation and stale-environment tests. It is not suitable for mutable current
state without exact content invalidation.

On managed Windows sandboxes, Python's process-default temporary directory may
be readable but not writable. Qualification harnesses must therefore accept or
select an explicit writable ephemeral root, while pytest runs must receive an
explicit unique `--basetemp`. A permission failure in the default temp root is
an environment-contract failure, not evidence about the transaction protocol.

OneDrive-synchronized roots can transiently lock SQLite files during cleanup.
SQLite crash/recovery qualifications must run on a separately admitted local
ephemeral root; a repository-local ignored folder is not sufficient merely
because Git ignores it. The harness uses the task-specific
`LFDT_EPHEMERAL_ROOT` adapter variable and publishes no machine path.
