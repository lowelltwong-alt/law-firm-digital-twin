# Design C Baseline v1 Adoption

Date: 2026-07-18
Status: adopted and frozen by Lowell

## Decisions

- H-5 is adopted. Native/export-ready artifacts require all three marks: a corpus-external provenance manifest, embedded `SYNTHETIC - LFDT` native metadata with corpus identity, and a visible watermark applied at the export or sharing boundary.
- H-6 is adopted as a zero-capacity rule until weekly human-review capacity and sampling allocations are measured. No multi-case advancement is authorized.
- H-7 is adopted. `design-c-baseline-v1` is the frozen depth-first obligation set. Existing breadth assets are retained as a specification and prototype library, not an automatic build queue.
- H-10 selects a non-synced local runtime root through the untracked `LFDT_RUNTIME_ROOT` setting. The machine-specific value is deliberately excluded from public artifacts. This selection does not activate canonical storage. Physical worker-identity isolation, path/key/crosswalk denial, startup root validation, and a separately selected and qualified backup location remain mandatory before activation.
- H-11 is adopted as a zero-spend rule for multi-case and unattended execution until a measured cost ceiling is separately approved.

## Frozen depth-first sequence

1. One hardened synthetic employment case.
2. Physical sealed/operating boundary with worker-identity denial.
3. Mutation-qualified oracle canaries over every registered operating surface.
4. One hundred fresh-process deterministic replays with environment-drift rejection.
5. Append-only commit ledger, compare-and-swap, idempotency, transactional outbox, finance journal, and recovery kill drills.
6. Exact DesignedImperfectionLedger reconciliation.
7. Symmetric two-sided sealed world, five-axis MeritsVector, bitemporal assertions, KnowledgeEvents, RecollectionStates, assertion manifests, and OperatingStore-only Berean primitives.
8. Independent re-review before any multi-case or unattended campaign.

## Explicit non-authorizations

This decision does not authorize creation of a canonical store, a durable sealed key, a backup destination, external service access, public-data ingestion, G3 native export, another litigation family, publication, deployment, multi-case generation, or unattended Cursor execution. SimPy remains an optional non-default comparator; the pure integer scheduler is normative.
