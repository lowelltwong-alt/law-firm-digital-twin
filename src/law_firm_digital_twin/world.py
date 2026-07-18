from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .hashio import digest
from .models import RulePack


@dataclass(frozen=True)
class VoiceProfile:
    register: str
    sentence_style: str
    directness: str
    organization: str
    revision_habit: str
    signature: str


@dataclass(frozen=True)
class MemoryProfile:
    encoding: str
    retrieval: str
    confidence_calibration: str
    stress_effect: str


@dataclass(frozen=True)
class PersonaProfile:
    actor_id: str
    role_id: str
    synthetic_background: str
    training: str
    organization: str
    goals: tuple[str, ...]
    working_style: str
    voice: VoiceProfile
    memory: MemoryProfile
    initial_knowledge: tuple[str, ...]
    initial_authority: tuple[str, ...]


@dataclass(frozen=True)
class FactClaim:
    fact_id: str
    value: str


@dataclass(frozen=True)
class CustodyStep:
    action: str
    actor_id: str
    simulated_day: int
    object_hash: str


@dataclass(frozen=True)
class EvidenceArtifact:
    artifact_id: str
    family: str
    title: str
    author_id: str
    recipients: tuple[str, ...]
    created_day: int
    content: str
    claims: tuple[FactClaim, ...]
    voice_signature: str
    responsive: bool
    privileged: bool
    initially_visible: bool
    native_format: str
    metadata: tuple[tuple[str, str], ...]
    custody: tuple[CustodyStep, ...]

    @property
    def content_hash(self) -> str:
        return digest(
            {
                "artifact_id": self.artifact_id,
                "family": self.family,
                "author_id": self.author_id,
                "created_day": self.created_day,
                "content": self.content,
                "claims": self.claims,
                "metadata": self.metadata,
            }
        )


@dataclass(frozen=True)
class DeclaredConflict:
    conflict_id: str
    fact_id: str
    artifact_ids: tuple[str, ...]
    design_purpose: str


@dataclass(frozen=True)
class SealedWorld:
    truth: tuple[FactClaim, ...]
    declared_conflicts: tuple[DeclaredConflict, ...]
    witness_fact_frontier: tuple[str, ...]
    expert_authorized_artifacts: tuple[str, ...]
    target_posture: str
    target_strength: int

    @property
    def commitment_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class SyntheticMatter:
    matter_id: str
    world_id: str
    referral_id: str
    case_type: str
    rule_pack: RulePack
    hidden_truth_hash: str
    operating_record_hash: str
    oracle_commitment_hash: str
    actors: dict[str, PersonaProfile]
    evidence_inventory: tuple[EvidenceArtifact, ...]
    initial_record_ids: tuple[str, ...]
    facts: dict[str, Any]

    def operating_view(self) -> dict[str, Any]:
        initial = [
            {
                "artifact_id": item.artifact_id,
                "family": item.family,
                "title": item.title,
                "author_id": item.author_id,
                "created_day": item.created_day,
                "content": item.content,
                "content_hash": item.content_hash,
                "native_format": item.native_format,
            }
            for item in self.evidence_inventory
            if item.initially_visible
        ]
        return {
            "matter_id": self.matter_id,
            "world_id": self.world_id,
            "referral_id": self.referral_id,
            "case_type": self.case_type,
            "rule_pack": asdict(self.rule_pack),
            "hidden_truth_hash": self.hidden_truth_hash,
            "operating_record_hash": self.operating_record_hash,
            "oracle_commitment_hash": self.oracle_commitment_hash,
            "actors": {
                actor_id: {
                    "role_id": profile.role_id,
                    "synthetic_background": profile.synthetic_background,
                    "training": profile.training,
                    "organization": profile.organization,
                    "working_style": profile.working_style,
                    "voice": asdict(profile.voice),
                    "memory": asdict(profile.memory),
                }
                for actor_id, profile in sorted(self.actors.items())
            },
            "initial_record": initial,
            "initial_record_ids": list(self.initial_record_ids),
            "facts": self.facts,
        }


@dataclass(frozen=True)
class WorldBundle:
    matter: SyntheticMatter
    sealed: SealedWorld


def _voice(
    register: str,
    sentence_style: str,
    directness: str,
    organization: str,
    revision_habit: str,
) -> VoiceProfile:
    signature = digest(
        {
            "register": register,
            "sentence_style": sentence_style,
            "directness": directness,
            "organization": organization,
            "revision_habit": revision_habit,
        }
    )[:16]
    return VoiceProfile(
        register=register,
        sentence_style=sentence_style,
        directness=directness,
        organization=organization,
        revision_habit=revision_habit,
        signature=signature,
    )


def build_personas() -> dict[str, PersonaProfile]:
    return {
        "intake_coordinator": PersonaProfile(
            actor_id="intake_coordinator",
            role_id="intake",
            synthetic_background="claims-service and community-college administration experience",
            training="intake, confidentiality, and matter-opening workflow",
            organization="defense_firm",
            goals=("capture the referral accurately", "avoid premature commitments"),
            working_style="checklist-first and calmly responsive",
            voice=_voice("professional-warm", "short complete sentences", "moderate", "chronological", "re-reads names and dates"),
            memory=MemoryProfile("source-anchored", "recognition-led", "well calibrated", "narrows attention to required fields"),
            initial_knowledge=("referral_summary",),
            initial_authority=("receive_referral",),
        ),
        "conflicts_analyst": PersonaProfile(
            actor_id="conflicts_analyst",
            role_id="conflicts",
            synthetic_background="litigation-support and records-indexing experience",
            training="conflicts systems, entity normalization, and escalation",
            organization="defense_firm",
            goals=("find entity relationships", "preserve uncertainty"),
            working_style="structured, exact, and exception oriented",
            voice=_voice("formal-operational", "fragments plus tables", "high", "entity-by-entity", "adds qualifiers instead of deleting"),
            memory=MemoryProfile("categorical", "index-cued", "conservative", "double-checks ambiguous affiliates"),
            initial_knowledge=(),
            initial_authority=(),
        ),
        "responsible_lawyer": PersonaProfile(
            actor_id="responsible_lawyer",
            role_id="lawyer",
            synthetic_background="employment-defense practice with earlier public-sector service",
            training="civil procedure, employment law, negotiation, and trial",
            organization="defense_firm",
            goals=("protect the insured", "honor carrier authority", "test adverse facts"),
            working_style="theory-driven but evidence constrained",
            voice=_voice("legal-analytic", "mixed short conclusions and longer reasoning", "high", "issue-rule-evidence-action", "revises categorical language"),
            memory=MemoryProfile("conceptual", "issue-cued", "moderately calibrated", "under pressure remembers themes before dates"),
            initial_knowledge=("referral_summary",),
            initial_authority=(),
        ),
        "litigation_paralegal": PersonaProfile(
            actor_id="litigation_paralegal",
            role_id="paralegal",
            synthetic_background="ten years of civil-litigation operations",
            training="preservation, collection, production, calendaring, and billing support",
            organization="defense_firm",
            goals=("maintain custody", "keep the team ahead of deadlines"),
            working_style="sequence and exception focused",
            voice=_voice("operational-precise", "compact bullets", "high", "date then task then owner", "keeps visible correction history"),
            memory=MemoryProfile("sequence-rich", "timeline-cued", "highly calibrated", "uses external checklists"),
            initial_knowledge=(),
            initial_authority=(),
        ),
        "docketing_specialist": PersonaProfile(
            actor_id="docketing_specialist",
            role_id="docketing",
            synthetic_background="court-operations and deadline-control experience",
            training="rule-pack use, dual calculation, and verification",
            organization="defense_firm",
            goals=("calculate from admitted rules", "surface every assumption"),
            working_style="dual-control and source-first",
            voice=_voice("technical-formal", "numbered calculations", "high", "source-input-calculation-review", "never overwrites prior calculation"),
            memory=MemoryProfile("rule-linked", "citation-cued", "highly calibrated", "stops when source status is uncertain"),
            initial_knowledge=(),
            initial_authority=(),
        ),
        "deadline_reviewer": PersonaProfile(
            actor_id="deadline_reviewer",
            role_id="deadline_reviewer",
            synthetic_background="risk-control review and calendaring quality assurance",
            training="independent deadline verification and exception escalation",
            organization="defense_firm",
            goals=("recalculate without anchoring", "reject unexplained differences"),
            working_style="independent-input and comparison-last",
            voice=_voice("audit-formal", "input and result pairs", "high", "source-recalculation-variance", "records a new version for corrections"),
            memory=MemoryProfile("rule-linked", "independent worksheet-cued", "highly calibrated", "does not inspect the first result until complete"),
            initial_knowledge=(),
            initial_authority=(),
        ),
        "hr_witness": PersonaProfile(
            actor_id="hr_witness",
            role_id="witness",
            synthetic_background="generalist HR work in a fast-growing regional services company",
            training="employee relations and benefits administration",
            organization="synthetic_insured",
            goals=("explain the process honestly", "avoid guessing"),
            working_style="people-centered and interruption prone",
            voice=_voice("business-conversational", "contextual sentences", "moderate", "people then events", "softens conclusions after review"),
            memory=MemoryProfile("gist-strong", "person-cued", "variable", "loses peripheral date precision"),
            initial_knowledge=("hr_note", "policy", "employee_report", "hr_email"),
            initial_authority=(),
        ),
        "manager_witness": PersonaProfile(
            actor_id="manager_witness",
            role_id="manager",
            synthetic_background="field operations supervisor promoted from a technical trade",
            training="safety, scheduling, and performance coaching",
            organization="synthetic_insured",
            goals=("keep operations staffed", "defend the decision"),
            working_style="fast, practical, and mobile-first",
            voice=_voice("plain-direct", "short mobile fragments", "very high", "bottom line first", "rarely edits sent messages"),
            memory=MemoryProfile("action-centered", "place-cued", "overconfident on sequence", "compresses nearby events"),
            initial_knowledge=("manager_email", "attendance", "manager_calendar"),
            initial_authority=(),
        ),
        "claim_handler": PersonaProfile(
            actor_id="claim_handler",
            role_id="carrier",
            synthetic_background="multi-line commercial claims management",
            training="coverage posture, reserves, guidelines, and litigation management",
            organization="synthetic_carrier",
            goals=("control covered spend", "receive candid exposure reporting"),
            working_style="reserve and exception oriented",
            voice=_voice("claims-formal", "compressed paragraphs", "high", "coverage-exposure-budget-next step", "tracks changes by dated addendum"),
            memory=MemoryProfile("file-anchored", "claim-note-cued", "well calibrated", "prioritizes reserve-changing facts"),
            initial_knowledge=("coverage_posture", "guidelines"),
            initial_authority=("carrier_audit",),
        ),
        "billing_specialist": PersonaProfile(
            actor_id="billing_specialist",
            role_id="billing",
            synthetic_background="legal billing and accounts-receivable operations",
            training="time-entry review, invoice submission, appeals, and cash application",
            organization="defense_firm",
            goals=("submit supportable work", "reconcile every balance"),
            working_style="ledger-first and variance focused",
            voice=_voice("financial-operational", "terse labeled lines", "high", "amount then reason then action", "posts corrections as separate entries"),
            memory=MemoryProfile("transactional", "amount-cued", "highly calibrated", "reconciles before relying on recall"),
            initial_knowledge=(),
            initial_authority=(),
        ),
        "independent_expert": PersonaProfile(
            actor_id="independent_expert",
            role_id="expert",
            synthetic_background="organizational-practices research and workplace investigations",
            training="methods, source limitation, and opinion writing",
            organization="independent_practice",
            goals=("remain independent", "state limitations"),
            working_style="method and source constrained",
            voice=_voice("expert-formal", "qualified analytic prose", "moderate", "materials-method-observation-limitation-opinion", "retains versioned drafts"),
            memory=MemoryProfile("source-bounded", "document-cued", "highly calibrated", "declines unsupported extrapolation"),
            initial_knowledge=(),
            initial_authority=(),
        ),
    }


def _artifact(
    artifact_id: str,
    family: str,
    title: str,
    author_id: str,
    recipients: tuple[str, ...],
    created_day: int,
    content: str,
    claims: tuple[FactClaim, ...],
    personas: dict[str, PersonaProfile],
    *,
    responsive: bool = True,
    privileged: bool = False,
    initially_visible: bool = False,
    native_format: str = "text/plain",
) -> EvidenceArtifact:
    metadata = (("synthetic", "true"), ("generator", "g2_deterministic_evidence_v1"))
    provisional_hash = digest(
        {
            "artifact_id": artifact_id,
            "family": family,
            "author_id": author_id,
            "created_day": created_day,
            "content": content,
            "claims": claims,
            "metadata": metadata,
        }
    )
    custody = (
        CustodyStep("created", author_id, created_day, provisional_hash),
        CustodyStep("collected", "litigation_paralegal", 50, provisional_hash),
        CustodyStep("hashed", "litigation_paralegal", 50, provisional_hash),
    )
    return EvidenceArtifact(
        artifact_id=artifact_id,
        family=family,
        title=title,
        author_id=author_id,
        recipients=recipients,
        created_day=created_day,
        content=content,
        claims=claims,
        voice_signature=personas[author_id].voice.signature,
        responsive=responsive,
        privileged=privileged,
        initially_visible=initially_visible,
        native_format=native_format,
        metadata=metadata,
        custody=custody,
    )


def build_employment_world(seed: str, rule_pack: RulePack) -> WorldBundle:
    personas = build_personas()
    world_id = f"WORLD-{digest({'seed': seed, 'kind': 'world'})[:12]}"
    matter_id = f"MATTER-{digest({'seed': seed, 'kind': 'matter'})[:12]}"
    referral_id = f"REF-{digest({'seed': seed, 'kind': 'referral'})[:10]}"
    truth = (
        FactClaim("protected_activity", "employee_reported_wage_and_safety_concerns"),
        FactClaim("termination_day", "44"),
        FactClaim("decision_status_day_38", "manager_treated_decision_as_final"),
        FactClaim("decision_status_day_40", "hr_had_not_received_final_recommendation"),
        FactClaim("attendance_issue", "documented_but_incompletely_investigated"),
        FactClaim("coverage_posture", "reservation_of_rights"),
    )
    posture_bucket = int(digest({"seed": seed, "kind": "posture"})[:8], 16) % 100
    if posture_bucket < 35:
        target_posture = "defense_favorable"
        target_strength = 72
    elif posture_bucket < 70:
        target_posture = "claimant_favorable"
        target_strength = 28
    else:
        target_posture = "balanced"
        target_strength = 50

    evidence = (
        _artifact(
            "E-TERM-001",
            "hr_record",
            "Termination notice",
            "manager_witness",
            ("hr_witness",),
            44,
            "Effective today, employment ends for continuing attendance and performance problems. Operations cannot absorb another missed shift.",
            (FactClaim("termination_day", "44"), FactClaim("stated_reason", "attendance_and_performance")),
            personas,
            initially_visible=True,
            native_format="application/pdf",
        ),
        _artifact(
            "E-HRNOTE-002",
            "hr_note",
            "HR note excerpt",
            "hr_witness",
            (),
            39,
            "Spoke with the manager. I understood we would review the attendance entries together before any final recommendation.",
            (FactClaim("decision_status_day_39", "review_pending"),),
            personas,
            initially_visible=True,
            native_format="text/rtf",
        ),
        _artifact(
            "E-POLICY-003",
            "policy",
            "Progressive-discipline policy excerpt",
            "hr_witness",
            ("manager_witness",),
            1,
            "Managers should document coaching and consult Human Resources before discharge. The policy permits exceptions with a recorded operational reason.",
            (FactClaim("policy_process", "consult_hr_before_discharge"),),
            personas,
            initially_visible=True,
            native_format="application/pdf",
        ),
        _artifact(
            "E-MGREMAIL-004",
            "email",
            "Manager email to operations director",
            "manager_witness",
            ("hr_witness",),
            38,
            "Made the call this morning. We need the role covered Monday. HR can finish the paperwork.",
            (FactClaim("decision_status", "final_on_day_38"),),
            personas,
            native_format="message/rfc822",
        ),
        _artifact(
            "E-HREMAIL-005",
            "email",
            "HR follow-up email",
            "hr_witness",
            ("manager_witness",),
            40,
            "I still do not have a final recommendation or the calendar entries. Please send both before a termination decision is communicated.",
            (FactClaim("decision_status", "not_final_by_day_40"),),
            personas,
            native_format="message/rfc822",
        ),
        _artifact(
            "E-PAYROLL-006",
            "payroll_record",
            "Payroll attendance summary",
            "billing_specialist",
            ("hr_witness",),
            35,
            "Attendance exceptions: two excused, one disputed, one unverified. Manager review field remains blank.",
            (FactClaim("attendance_issue", "mixed_and_partly_unverified"),),
            personas,
            native_format="text/csv",
        ),
        _artifact(
            "E-CALENDAR-007",
            "calendar",
            "Manager calendar export",
            "manager_witness",
            (),
            37,
            "Thu 8:00 staffing; Thu 9:30 employee follow-up; Fri 15:00 HR review (tentative).",
            (FactClaim("hr_review_scheduled", "day_39_tentative"),),
            personas,
            native_format="text/calendar",
        ),
        _artifact(
            "E-NOISE-008",
            "email",
            "Benefits enrollment reminder",
            "hr_witness",
            ("manager_witness",),
            36,
            "Reminder: benefits enrollment closes Friday. The guide and office-hours link are attached.",
            (),
            personas,
            responsive=False,
            native_format="message/rfc822",
        ),
    )
    initial_record_ids = tuple(item.artifact_id for item in evidence if item.initially_visible)
    operating_record = {
        "referral": referral_id,
        "known_documents": list(initial_record_ids),
        "missing": ["complete_emails", "payroll_detail", "manager_calendar"],
        "synthetic_guidelines": "synthetic_ocg_v0",
    }
    sealed = SealedWorld(
        truth=truth,
        declared_conflicts=(
            DeclaredConflict(
                "C-DECISION-TIMING",
                "decision_status",
                ("E-MGREMAIL-004", "E-HREMAIL-005"),
                "test whether review finds incompatible contemporaneous accounts",
            ),
        ),
        witness_fact_frontier=("hr_note", "policy", "employee_report", "hr_email"),
        expert_authorized_artifacts=(
            "E-TERM-001",
            "E-HRNOTE-002",
            "E-POLICY-003",
            "E-MGREMAIL-004",
            "E-HREMAIL-005",
            "E-PAYROLL-006",
            "E-CALENDAR-007",
        ),
        target_posture=target_posture,
        target_strength=target_strength,
    )
    matter = SyntheticMatter(
        matter_id=matter_id,
        world_id=world_id,
        referral_id=referral_id,
        case_type="labor_and_employment_defense",
        rule_pack=rule_pack,
        hidden_truth_hash=digest(truth),
        operating_record_hash=digest(operating_record),
        oracle_commitment_hash=sealed.commitment_hash,
        actors=personas,
        evidence_inventory=evidence,
        initial_record_ids=initial_record_ids,
        facts=operating_record,
    )
    return WorldBundle(matter=matter, sealed=sealed)
