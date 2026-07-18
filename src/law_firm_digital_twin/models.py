from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class Arm(str, Enum):
    TRADITIONAL = "traditional"
    AI_FIRST = "ai_first"


class Route(str, Enum):
    EARLY_SETTLEMENT = "early_settlement"
    MEDIATION_IMPASSE = "mediation_impasse"
    DISPOSITIVE = "dispositive"
    TRIAL_APPEAL = "trial_appeal"


class Plane(str, Enum):
    WORLD = "world"
    OPERATING = "operating"
    EVALUATION = "evaluation"


@dataclass(frozen=True)
class SourceReceipt:
    source_id: str
    stable_source: str
    authority: str
    retrieval_date: str
    effective_date: str
    license_posture: str
    intended_use: str
    prohibited_use: str
    source_hash: str
    validator: str
    status: str


@dataclass(frozen=True)
class RulePack:
    rule_pack_id: str
    jurisdiction_label: str
    source_receipts: tuple[SourceReceipt, ...]
    response_days: int
    disclosure_days: int
    discovery_cutoff_days: int


@dataclass(frozen=True)
class Command:
    command_id: str
    verb: str
    actor_id: str
    role_id: str
    matter_id: str
    payload: dict[str, Any]
    requires_authority: tuple[str, ...] = ()
    requires_knowledge: tuple[str, ...] = ()


@dataclass(frozen=True)
class Event:
    event_id: str
    run_id: str
    matter_id: str
    simulated_at: int
    event_type: str
    command_id: str
    actor_id: str
    role_id: str
    knowledge_scope: str
    authority_basis: str
    payload: dict[str, Any]
    input_hash: str
    output_hash: str
    random_stream_key: str
    treatment_arm: str | None = None


@dataclass
class FinanceBook:
    work: Decimal = Decimal("0.00")
    wip: Decimal = Decimal("0.00")
    submitted: Decimal = Decimal("0.00")
    approved: Decimal = Decimal("0.00")
    reduced: Decimal = Decimal("0.00")
    appealed: Decimal = Decimal("0.00")
    accounts_receivable: Decimal = Decimal("0.00")
    cash: Decimal = Decimal("0.00")
    write_off: Decimal = Decimal("0.00")

    def invariant_errors(self) -> list[str]:
        errors: list[str] = []
        if self.work != self.wip + self.submitted:
            errors.append("work must equal wip plus submitted")
        if self.submitted != self.approved + self.reduced:
            errors.append("submitted must equal approved plus reduced")
        if self.approved + self.appealed != self.accounts_receivable + self.cash + self.write_off:
            errors.append("approved plus appealed must equal AR plus cash plus write-off")
        return errors


@dataclass
class Projection:
    matter_status: str = "new"
    deadlines: dict[str, int] = field(default_factory=dict)
    authority_holds: set[str] = field(default_factory=set)
    knowledge_canary_hits: int = 0
    oracle_access_attempts: int = 0
    human_gate_bypasses: int = 0
    artifact_hashes: list[str] = field(default_factory=list)
    finance: FinanceBook = field(default_factory=FinanceBook)
    closed: bool = False
    route: str = ""

