# G2 SimPy Scheduling Adapter Decision

Date: 2026-07-18  
Status: bounded local adapter qualified; not canonical world time

## Decision

Admit SimPy 4.1.2 under its MIT license for one narrow G2 function: planning
integer-tick start and finish times for opaque work proposals competing for
limited firm resources. The adapter is behind provider-neutral contracts and is
checked against a pure-Python integer scheduler.

The adapter does not receive source bodies, command payloads, identities,
merits, amounts, route labels, verdicts, settlement outcomes, evaluator truth,
or world namespaces. It receives commitments, route-blind scheduling classes,
integer ready/service ticks, priorities, resource classes, and liveness
ceilings. All four resolution routes map to the same `resolution_work` class.

## Authority boundary

`env.now` is proposed schedule time only. It is not the kernel's event clock and
does not create an accepted event. The adapter cannot call `kernel.submit`,
write a projection, choose a branch, decide an outcome, validate a world fact,
or admit a result into canonical data. Only the world kernel owns those
consequences.

## Qualification evidence

The qualification gate requires all of the following on one immutable
cassette:

1. exact decision equality with the provider-neutral reference scheduler;
2. identical repeated SimPy traces;
3. resource-capacity, ready-time, service-time, wait-ceiling, and finish-ceiling
   validation by a separate checker;
4. identical kernel event, projection, denial, attempted-command, and Berean
   audit hashes when the cassette is executed directly and again after schedule
   planning;
5. hostile rejection of cross-matter proposals, payload/authority claims,
   malformed ticks and priorities, runtime drift, trace tampering, and route
   leakage; and
6. an aggregate-only public fixture with no matter, command, cassette,
   proposal, trace, or receipt commitments.

## Dependency receipt

- Package: `simpy`
- Qualified version: `4.1.2`
- License: MIT
- Wheel SHA-256:
  `43071f84b6512c9b4fcb33ef057f240ccb1d1f3b263f9b4f9229d072e310b372`
- Lock: `requirements/simulation.lock`
- Official documentation: <https://simpy.readthedocs.io/en/stable/index.html>
- Distribution record: <https://pypi.org/project/simpy/4.1.2/>

The qualification expires on any runtime, dependency, scheduler-core,
normalization, queue-policy, schema, authority, privacy, resource-model, or G2
cassette-contract change. Requalification is mandatory; self-qualification by
the runtime adapter is prohibited.

## Deferred scope

This decision does not activate stochastic simulation, wall-clock scheduling,
Temporal, external services, unattended campaigns, live legal data, G3
rendering, or another litigation domain. Witness and expert availability also
remain outside this first resource model.
