# Technology Adoption Map Decision

Date: 2026-07-18  
Status: approved architecture; only bounded SimPy 4.1.2 adapter installed and active

## Decision

Law Firm Digital Twin will use the following standards and open-source systems
through provider-neutral, versioned adapters. Lowell approved this technology
family for the architecture. This decision does not silently install a package,
start a service, ingest a source row, activate a later case family, or give a
third-party system authority over world truth.

| Technology | Intended role | Adoption state |
|---|---|---|
| [SimPy](https://simpy.readthedocs.io/en/stable/index.html) | Deterministic process/event scheduling and constrained-resource queues inside the simulation | Bounded G2 schedule-only adapter qualified at 4.1.2 |
| [Temporal Python SDK](https://github.com/temporalio/sdk-python) | Crash-resistant, multi-day campaign orchestration, retries, heartbeats, and checkpoints | Approved later; not the world kernel |
| [EDRM model](https://edrm.net/wiki/edrm-model/) | Conceptual and iterative eDiscovery coverage map | Approved reference mapping, never a mandatory waterfall or compliance claim |
| [Apache Tika](https://tika.apache.org/index.html) | Local type detection, metadata extraction, and text extraction for admitted synthetic files | Approved later local adapter |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | OCR of admitted synthetic scans with confidence and layout sidecars | Approved later local adapter |
| [SALI LMSS](https://sali.org/explore-the-standard/) | Matter/service classification and semantic mapping | Approved versioned mapping |
| [LEDES 1998B](https://ledes.org/ledes-98b-format/) | Synthetic legal-invoice exchange and round-trip validation | Approved versioned mapping |
| [UTBMS](https://www.americanbar.org/groups/litigation/resources/uniform-task-based-management-system/) | Litigation task/activity coding, budgets, billing analysis | Approved versioned mapping |
| [Synthea](https://github.com/synthetichealth/synthea) | Later synthetic patient-lifecycle and health-record fixture foundation | Approved later medical-domain foundation |
| [FHIR R4](https://hl7.org/fhir/R4/diagnosticreport.html) | Later synthetic medical resource graph, including DiagnosticReport, Observation, DocumentReference, version, and provenance relationships | Approved later medical-domain foundation |

The architecture also requires provider-neutral graph reasoning, temporal
reasoning, deterministic testing/validation, and separately qualified
construction, traffic-reconstruction, and biomechanics components. No specific
library for those six requirements has been admitted yet.

## Why these boundaries

SimPy is process-based discrete-event simulation. Its processes, events, and
limited-capacity resources fit the internal firm/world clock, queues, staffing,
and congestion model. A SimPy adapter may schedule proposed kernel commands; it
may not own facts, authority, outcomes, or canonical time without a kernel
event receipt.

Temporal is designed for durable long-running orchestration, and its workflows
must remain deterministic while external I/O belongs in activities. That makes
it appropriate for the later Cursor/Codex campaign controller, not for deciding
case facts or litigation outcomes. Workflow revisions, activity idempotency,
heartbeats, retry ceilings, human stop conditions, and payload privacy require a
separate qualification wave.

EDRM explicitly describes its model as conceptual, iterative, and not a literal
linear waterfall. The eDiscovery adapter will therefore map information
governance, identification, preservation, collection, processing, review,
analysis, production, and presentation as revisitable states with provenance,
not as a single compulsory sequence.

Tika and Tesseract are extraction tools, not truth engines. Every extracted
value must retain source-byte hash, parser/OCR version, configuration,
confidence or exception status, and a reversible link to the synthetic source.
Low-confidence OCR cannot silently become a fact. Private or live material
cannot enter either adapter without a future source-admission boundary.

SALI, LEDES, and UTBMS enter as effective-dated mappings with round-trip and
unknown-code behavior. LEDES 1998B is a pipe-delimited 24-field exchange format;
the adapter must preserve original synthetic amounts and classifications and
must never claim carrier acceptance. UTBMS codes classify work; they do not
approve an invoice or predict legal success.

Synthea generates synthetic patient lifecycles and can export FHIR. It will be
used only after a medical-family activation decision. FHIR resources preserve
the distinctions among atomic Observation results, DiagnosticReport context and
interpretation, DocumentReference metadata, underlying bytes, and version/
provenance. Neither Synthea nor FHIR proves clinical plausibility, diagnosis,
causation, standard of care, damages, or medico-legal truth.

## Mandatory gate before each adapter

Every selected dependency must have:

1. a license and terms receipt;
2. an exact version pin and software bill of materials;
3. a provider-neutral contract and an in-memory or cassette fallback;
4. deterministic fixture and replay evidence;
5. privacy, authority, injection, malformed-input, and resource-ceiling tests;
6. an independent validator that does not share the adapter implementation; and
7. rollback plus expiry triggers for version, configuration, provider, schema,
   privacy, authority, scope, or runtime changes.

The gate has passed only for the bounded SimPy 4.1.2 schedule adapter.
`technology_adoption.py` records its installed code and local runtime execution,
while keeping source-row admission, external access, canonical truth, and legal
authority false. Every other entry remains dependency- and runtime-inactive.
The detailed receipt and expiry conditions are in
`g2_simpy_scheduler_adapter_decision.md`.

## Order

1. Build and qualify the SimPy clock/resource adapter against the existing
   deterministic kernel and cassettes.
2. Map the employment eDiscovery dossier to the iterative EDRM states.
3. Add SALI/UTBMS mappings and a LEDES 1998B synthetic round-trip fixture.
4. Add Tika/Tesseract only to a local, synthetic-file extraction sandbox.
5. Add Temporal after the campaign job/lease/checkpoint contracts are stable.
6. Add Synthea/FHIR only with a separately activated medical-malpractice domain
   and qualified clinical-plausibility validators.
7. Select graph, temporal, construction, traffic, and biomechanics libraries
   through their provider-neutral requirement contracts and protected fixtures.

## Non-authorization

Except for the qualified SimPy 4.1.2 local adapter, this decision does not authorize another dependency installation, network service,
live data ingestion, real-client processing, PACER access, legal or clinical
compliance claim, G3 rendering, medical-family activation, unattended campaign
execution, publication, or production use.

