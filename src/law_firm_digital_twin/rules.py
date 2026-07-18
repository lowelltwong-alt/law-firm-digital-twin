from __future__ import annotations

from .hashio import digest
from .models import RulePack, SourceReceipt


PRIMARY_DEADLINE_CALCULATOR = "primary_deadline_calculator_v1"
SECONDARY_DEADLINE_CALCULATOR = "secondary_deadline_calculator_v1"


def calculate_deadlines_primary(rule_pack: RulePack, filed_day: int) -> dict[str, int]:
    """First calculator: direct rule-field expansion."""
    return {
        "response_due": filed_day + rule_pack.response_days,
        "initial_disclosures_due": filed_day + rule_pack.disclosure_days,
        "discovery_cutoff": filed_day + rule_pack.discovery_cutoff_days,
    }


def calculate_deadlines_secondary(rule_pack: RulePack, filed_day: int) -> dict[str, int]:
    """Second implementation used by a different actor after the proposal is sealed."""
    named_offsets = (
        ("discovery_cutoff", rule_pack.discovery_cutoff_days),
        ("response_due", rule_pack.response_days),
        ("initial_disclosures_due", rule_pack.disclosure_days),
    )
    independently_derived: dict[str, int] = {}
    for label, offset in named_offsets:
        independently_derived[label] = sum((filed_day, offset))
    return independently_derived


def placeholder_data_first_rule_pack() -> RulePack:
    receipt = SourceReceipt(
        source_id="SRC-DATA-FIRST-PENDING",
        stable_source="docs/jurisdiction_data_rubric.md",
        authority="Lowell decision H-1; jurisdiction not locked",
        retrieval_date="2026-07-18",
        effective_date="pending",
        license_posture="local project policy",
        intended_use="placeholder deadlines for deterministic skeleton only",
        prohibited_use="real legal deadline authority or public claim of jurisdiction correctness",
        source_hash=digest({"doc": "jurisdiction_data_rubric", "date": "2026-07-18"}),
        validator="placeholder_rule_pack_validator",
        status="hold_for_real_jurisdiction",
    )
    return RulePack(
        rule_pack_id="RULEPACK-DATA-FIRST-PENDING-v0",
        jurisdiction_label="DATA_FIRST_PENDING",
        source_receipts=(receipt,),
        response_days=21,
        disclosure_days=30,
        discovery_cutoff_days=180,
    )

