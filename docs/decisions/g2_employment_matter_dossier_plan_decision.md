# G2 Employment-Defense Matter Dossier Plan Decision

Date: 2026-07-18  
Status: candidate after focused deterministic validation; nonexecuting

## Decision

The repository now has a typed, deterministic, non-rendering matter-dossier
planning layer for the active employment-defense G2 family. It maps the file a
synthetic insurance-defense firm may need across the full lifecycle without
creating those documents, filing anything, admitting legal rules or sources,
selecting a resolution route, or writing canonical world truth.

The catalog contains 16 lifecycle stages and 176 document types spanning:

- referral, claim notice, conflicts, engagement, and opening;
- carrier reporting, budgets, rates, exposure, and authority;
- preservation, custodians, systems, witnesses, chronology, and damages sources;
- pleading and case-management surrogates plus independent deadline
  reconciliation;
- written discovery, eDiscovery collection and review, privilege decisions,
  production, deficiency work, and third-party material;
- fact and organization depositions, exhibits, transcripts, errata, digests,
  and testimony-conflict updates;
- expert need, conflicts, independence, scope, materials, methods, limitations,
  reports, supplements, rebuttal, and deposition support;
- motion, settlement, mediation, arbitration-design, trial, and appeal branches;
- work events, time and expenses, prebill, invoices, audits, reductions,
  billing appeals and decisions, revised invoices, payments, cash application,
  write-offs, AR, reconciliation, and final invoicing; and
- future-kernel-adapter-bound resolution transition, final reporting, retention,
  conflict-history update, learning-candidate isolation, closure, and archive
  integrity.

## Boundary

This layer is a control surface, not a generator or legal-rules engine.

- Every document type has `body_included=false`, `runtime_execution=false`,
  `legal_compliance_claimed=false`, and `native_fidelity_claimed=false`.
- Source admission is `no_sources_admitted`; rule admission is
  `no_rules_admitted`.
- Filing-shaped records are labeled `simulated_filing_intent_only` and remain
  generic surrogates. They are not PACER replicas, jurisdiction-correct forms,
  or court-ready documents.
- Universal nodes are planning-only. Motion, settlement, mediation,
  arbitration, trial, and appeal nodes remain
  `inactive_pending_kernel_event`.
- No future branch is currently activatable; a versioned adapter to actual kernel events must be implemented and qualified first. The dossier contains no
  selected route, merits posture, outcome, settlement amount, verdict, or
  evaluator join.
- Arbitration remains a design-only branch and does not activate an arbitration
  runtime.

## Qualification and graph controls

The planner accepts only a fully revalidated `CaseCompilation` and its exact
qualification receipt. It binds the operating projection, receipt, catalog,
and complete document DAG. Node identifiers are derived from the operating
projection and catalog; sealed labels cannot select, remove, reorder, or alter
branch documents.

Independent validation checks the canonical catalog, exact closed
vocabularies, graph uniqueness, dependency resolution, acyclicity,
reachability, one referral root, stage and branch compatibility, kernel-event
activation, case binding, source and rule boundaries, no rendering or runtime
claims, and canonical replay. A stale receipt, cross-case graph transplant,
future-branch activation, unsafe source, stereotype shortcut, unknown role,
cycle, orphan, compliance claim, or regenerated local hash still fails closed.

The public fixture contains only aggregate counts and commitments over five
qualified planning blueprints. It excludes document definitions and bodies,
case facts, actor or organization identities, matter and world namespaces,
source rows, prompts, selected routes, outcomes, and financial amounts. The
minimum public cohort is five.

## Persona and expert constraints

The catalog assigns work by bounded roles and observable workflow needs. It
does not infer competence, memory, credibility, grammar, authority, liability,
or outcome from MBTI, left/right-brain labels, class, education, profession,
language, disability, or protected traits.

Expert entries are workflow requirements only. They separate need assessment,
conflicts and independence, separate counsel verification, retention scope, authorized materials, method and
limitations, report versions, rebuttal, and deposition support. They do not
verify credentials, execute an expert, admit external material, or authorize
medical, legal, credibility, causation, or damages conclusions.

## Finance constraints

Document ordering makes the finance chain explicit: work event, time and
expense entry, prebill, invoice, audit, reduction or rejection, appeal
assessment, appeal, decision, revised invoice, payment advice, cash application,
write-off, AR aging, reconciliation, and final invoice. These are document
intents only. The world kernel remains the authority for amounts, event order,
balances, payment, and closure invariants. Legal outcome cannot directly alter
the billing graph without observable work and finance events.

## Evidence

- `tests/test_employment_lifecycle_dossier.py`: 19 focused tests passed in
  118.82 seconds on 2026-07-18.
- `scripts/build_g2_employment_dossier_catalog.py`: public aggregate fixture
  built and independently validated over five qualified cases.
- `generated/g2-employment-dossier-plan-v1/catalog_summary.json`: 16 stages,
  176 document types, five planning blueprints, zero runtime execution.
- Architecture, integration, and hostile-test reviewers independently reviewed
  the design. Their requirements shaped the plane separation, branch blindness,
  public small-cell gate, expert limits, finance chain, and mutation tests.
- The current repository collects 176 tests. A full-suite attempt timed out after
  364.1 seconds without a result; it was not repeated, and no fresh full-suite
  pass is claimed.

The 118.82-second focused result is retained as immutable evidence. It is not to
be repeated against unchanged inputs; future validation should rerun only when
code, contracts, fixtures, runtime, authority, privacy, or scope changes.

## Non-authorization

This decision does not authorize document rendering, runtime specialists,
source ingestion, legal research, jurisdiction claims, native-file fidelity,
G3 expansion, external services, learning-loop promotion, unattended campaign
execution, publication, or production use. Each remains a separate human gate.

