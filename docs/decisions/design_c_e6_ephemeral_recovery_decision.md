# Design C E-6 Ephemeral Recovery Decision

Date: 2026-07-18  
Status: qualified ephemeral reference; canonical activation blocked on H-10

## Decision

Use standard-library SQLite only as a noncanonical, ephemeral reference adapter
for the minimum commit and finance recovery contracts. The portable core owns
the proposal, decision, snapshot, idempotency, compare-and-swap, outbox, and
double-entry shapes. SQLite owns no world facts, legal outcomes, or external
effects.

The commit transaction atomically appends the event, binds its idempotency key,
creates a pending outbox row, and advances the hash-chain head. Changed input
cannot reuse an idempotency key; a stale expected parent cannot commit; identical
redelivery returns the original event without mutation. Outbox acknowledgement
is idempotent and performs no delivery.

The finance journal posts balanced integer-cent double entries for invoice,
reduction, successful appeal, payment, and residual write-off. The reference
cycle ends with zero accounts receivable, $850 cash, $1,000 fee revenue, and
$150 net billing write-off. These are synthetic fixture amounts, not billing
advice or carrier predictions.

## Recovery evidence

Tests inject exceptions and real process death after begin, event/transaction
insert, command insert, finance-entry insert, outbox insert, before commit, and
after commit before return. Before-commit death recovers no partial rows and the
genesis head. After-commit death recovers one complete transaction and retries
as a duplicate. Two concurrent processes delivering one idempotency key yield
one acceptance and one duplicate.

Every restart runs SQLite integrity checks plus independent event-chain,
parent/head, command/event, outbox/event, record-count, per-transaction balance,
global balance, and finance-head validation.

## Boundaries

The adapters reject `ephemeral_test_only=false`. Test databases live in
temporary directories and are deleted after the run. No database, journal, WAL,
key, source row, or case identifier enters the repository. This evidence does
not satisfy H-10, authorize a canonical store, prove backup recovery, implement
worker leases, deliver an outbox effect, or authorize unattended execution.

The adapter and evidence expire on schema, transaction boundary, SQLite/Python,
journal/synchronous mode, filesystem, idempotency, hash, outbox, finance,
concurrency, worker, storage-root, or authority change.
