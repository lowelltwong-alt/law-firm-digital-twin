from __future__ import annotations

from dataclasses import dataclass

from .hashio import digest
from .models import RulePack


@dataclass(frozen=True)
class SyntheticMatter:
    matter_id: str
    world_id: str
    referral_id: str
    rule_pack: RulePack
    hidden_truth_hash: str
    operating_record_hash: str
    oracle_commitment_hash: str
    actors: dict[str, str]
    facts: dict[str, str]


def build_employment_matter(seed: str, rule_pack: RulePack) -> SyntheticMatter:
    world_id = f"WORLD-{digest({'seed': seed, 'kind': 'world'})[:12]}"
    matter_id = f"MATTER-{digest({'seed': seed, 'kind': 'matter'})[:12]}"
    referral_id = f"REF-{digest({'seed': seed, 'kind': 'referral'})[:10]}"
    hidden_truth = {
        "protected_activity": "employee reported alleged wage and safety concerns to HR",
        "adverse_action": "termination followed two weeks later",
        "employer_reason": "documented performance decline and attendance issue",
        "weakness": "manager note conflicts with HR chronology",
        "coverage_tension": "reservation of rights for intentional acts and punitive exposure",
    }
    operating_record = {
        "referral": referral_id,
        "known_documents": ["termination_notice", "hr_note_excerpt", "policy_excerpt"],
        "missing": ["complete emails", "payroll detail", "manager calendar"],
    }
    return SyntheticMatter(
        matter_id=matter_id,
        world_id=world_id,
        referral_id=referral_id,
        rule_pack=rule_pack,
        hidden_truth_hash=digest(hidden_truth),
        operating_record_hash=digest(operating_record),
        oracle_commitment_hash=digest({"world": world_id, "truth": hidden_truth}),
        actors={
            "lawyer": "synthetic_responsible_lawyer",
            "carrier": "synthetic_claim_handler",
            "insured": "synthetic_employer_contact",
            "witness": "synthetic_hr_witness",
            "expert": "synthetic_hr_practices_expert",
            "tribunal": "synthetic_tribunal",
        },
        facts=operating_record,
    )

