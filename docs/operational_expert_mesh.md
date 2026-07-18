# Law Firm Digital Twin Operational Expert Mesh

Status: G2 simulation contract; runtime execution and external effects are disabled.

This mesh models the operational work of an insurance-defense firm without pretending that a prompt, model, or simulation has legal, carrier, court, client, accounting, or banking authority. It complements the artifact specialist mesh. The kernel remains the only owner of simulated world consequences.

## Routing shape

The deterministic router selects an exact provider-neutral capability, one worker, and a distinct checker. It never selects a model or vendor. Runtime/model bindings belong in separately qualified adapters and attempt receipts. The only public route enters through WorldKernel.route_operational_work; the lower-level router and its construction token are internal. Requests may name record IDs but cannot supply their meaning or inject a ledger. The kernel derives its authority ledger from its committed matter. A rule-pack source is admitted only when its ID and digest match an approved, license-admitted record in the repository source-admission registry. Human authority-event and reuse-release admission are intentionally not active in this revision; those routes remain gated until kernel-authenticated issuers are implemented and qualified.

The domains are:

- intake and risk: intake triage, conflicts screening, independent conflicts review, and matter-opening packet control;
- matter operations: docketing, independent deadline review, legal-assistant coordination, paralegal support, depositions, witnesses, experts, and filing assembly;
- finance and carrier: guideline admission, time/WIP, prebill, invoice compilation, audit/reduction interpretation, appeals, revenue/AR, cash application, collections, reconciliation, and controls;
- information and evidence: neutral DMS/records, KM, legal hold, collection/custody, processing, review/privilege triage, production support, and retention/disposition;
- legal technology: provider-neutral integration planning plus separately qualified adapters. iManage is an adapter to a neutral document-repository contract, never the core truth system;
- control plane: authority, operations quality, finance controls, custody/provenance, privilege boundary, production lineage, adapter contract, and KM provenance checkers.

## Structural boundaries

- Only synthetic/public inputs are routable. Private, client, purchased, portal, raw-email, and case-bound inputs fail closed.
- Every output is a proposal, checklist, projection, or immutable receipt. No route can send email, book a deposition, access a portal, move money, submit a filing, release a hold, dispose of information, decide privilege, clear or waive a conflict, retain an expert, authorize settlement, or make legal strategy.
- Missing capabilities, receipts, authority artifacts, source admission, checker independence, or adapter qualification block routing. Invented, expired, wrong-matter, wrong-scope, wrong-issuer, self-issued, or digestless records also block. There is no improvising fallback.
- Public carrier/rule material requires source admission. Reused local carrier material also requires a named per-asset reuse-release receipt. Raw proprietary guideline text remains prohibited.
- Intake, conflicts, matter opening, time, prebill, invoice, cash, reconciliation, collection, production, and disposition duties are separated.
- Human-lawyer and other named-human gates must resolve from the kernel-owned ledger to a distinct named-human issuer; no request, worker, or checker may issue its own authority artifact.

## Activation boundary

This version validates role coverage and routing behavior only. It does not execute AI specialists, ingest real data, connect iManage or eDiscovery systems, establish legal/accounting compliance, or authorize G3+ work. Any connector, runtime, provider, schema, privacy, effect, authority, or corpus change requires a new qualification receipt and regression replay.

## Known trusted-process boundary

This is a fail-closed G2 mock inside a trusted Python process, not an in-process security boundary. The public WorldKernel route does not accept a caller ledger, but Python extensions in the same process can import module-internal objects. Operational activation therefore remains blocked until routing and authority resolution run behind a separately qualified process or tool-capability boundary whose caller cannot construct or replace the authority store. Human-authority and reuse-release admission also remain inactive until that boundary exists.
