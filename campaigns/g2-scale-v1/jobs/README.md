# Atomic Job Contract

`campaign.json` is authoritative. This directory documents how a controller materializes its inline atomic jobs; workers do not edit this directory during execution.

Each job binds objective, non-goals, immutable inputs and dependency digests, exact outputs, one write owner, a distinct checker, capability qualification, lease and heartbeat, idempotency key, checkpoint and receipt paths, hard ceilings, retry classes, repair limit, escalation, handoff states, and acceptance gates.

| Job | Bounded outcome | Depends on | Write owner |
| --- | --- | --- | --- |
| J000 | Baseline, scope, budget, and human authority receipt | none | controller evidence path only |
| J100 | Projection-separated case compiler | J000 | `case_compiler.py`, projection tests |
| J110 | Evidence-family contracts | J000 | `evidence_contracts.py`, evidence tests |
| J120 | Persona/relationship state projections | J000 | `persona_state.py`, representation tests |
| J130 | Projection/evidence/persona contract-lock integration | J100/J110/J120 | integration test only |
| J200 | Ten sealed blueprint fixtures and corpus manifest | J130 | `generated/g2-scale-v1/`, population test |
| J210 | Corpus-scale Berean audit | J200 | `corpus_auditor.py`, audit test |
| J300 | Cursor adapter specification and static validator | J200/J210 | adapter/checker files only |
| J400 | Clean replay and adversarial forward-test receipt | J200/J210/J300 | one check receipt |
| J410 | Human launch-decision packet | J400 | one final-verification receipt |

Parallel jobs have non-overlapping outputs. Controller state is never a worker output. A worker encountering a pre-existing or user-modified target must return `write_conflict`; it must not overwrite it.

