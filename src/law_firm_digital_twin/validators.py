from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .case_manifest import (
    CapabilityRegistry,
    CaseDesignBlueprint,
    _allocate_axis,
    build_capability_registry,
)
from .hashio import canonical_json, digest


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    subject_id: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    validator_revision: str
    passed: bool
    issues: tuple[ValidationIssue, ...]
    evidence: tuple[str, ...]
    report_hash: str


VALIDATOR_REVISION = "g2-scale-contract-validator-v1"


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def validate_capability_registry(registry: CapabilityRegistry) -> ValidationReport:
    issues: list[ValidationIssue] = []
    evidence: list[str] = [f"registry_hash:{registry.registry_hash}"]

    id_groups = {
        "case_family": [item.family_id for item in registry.case_families],
        "evidence_capability": [item.capability_id for item in registry.evidence_capabilities],
        "persona_dimension": [item.dimension_id for item in registry.persona_dimensions],
        "specialist_capability": [item.capability_id for item in registry.specialist_capabilities],
        "population_axis": [item.axis_id for item in registry.population_axes],
    }
    for group, ids in id_groups.items():
        for duplicate in sorted(_duplicates(ids)):
            issues.append(ValidationIssue("REG-001", "error", duplicate, f"duplicate {group} id"))

    for axis in registry.population_axes:
        total = sum(bucket.weight for bucket in axis.buckets)
        if total != 100:
            issues.append(ValidationIssue("REG-002", "error", axis.axis_id, f"weights total {total}, expected 100"))
        if not axis.buckets or any(bucket.weight <= 0 for bucket in axis.buckets):
            issues.append(ValidationIssue("REG-003", "error", axis.axis_id, "axis requires positive buckets"))
        if axis.operating_visibility != "commitment_only":
            issues.append(ValidationIssue("REG-004", "error", axis.axis_id, "sealed population labels cannot enter operating view"))

    evidence_families = {item.family_id for item in registry.evidence_capabilities}
    for family in registry.case_families:
        if not family.synthetic_only:
            issues.append(ValidationIssue("REG-005", "error", family.family_id, "case family must remain synthetic-only"))
        if family.fidelity_level not in {"G0", "G1", "G2"}:
            issues.append(ValidationIssue("REG-006", "error", family.family_id, "unsupported fidelity level"))
        if family.readiness == "active_g2":
            missing = sorted(set(family.required_evidence_capabilities) - evidence_families)
            if missing:
                issues.append(ValidationIssue("REG-007", "error", family.family_id, f"active family lacks evidence capabilities: {missing}"))
        elif "human_case_family_activation" not in family.activation_gate:
            issues.append(ValidationIssue("REG-008", "error", family.family_id, "design-only family lacks human activation gate"))
        if min(family.max_roles, family.max_relationship_edges, family.max_artifacts, family.max_versions_per_artifact) < 1:
            issues.append(ValidationIssue("REG-009", "error", family.family_id, "complexity bounds must be positive"))

    required_evidence_validators = {
        "validate_fact_allowlist",
        "validate_knowledge_frontier",
        "validate_timeline_and_version_graph",
        "validate_custody_and_hashes",
        "validate_nonplaceholder",
    }
    for capability in registry.evidence_capabilities:
        missing = required_evidence_validators - set(capability.validator_ids)
        if missing:
            issues.append(ValidationIssue("REG-010", "error", capability.capability_id, f"missing validators: {sorted(missing)}"))
        if not capability.required_fields or capability.max_per_matter < 1:
            issues.append(ValidationIssue("REG-011", "error", capability.capability_id, "family schema or count bound is empty"))
        if "oracle_paraphrase" not in capability.prohibited_shortcuts:
            issues.append(ValidationIssue("REG-012", "error", capability.capability_id, "oracle shortcut is not prohibited"))

    serialized_personas = canonical_json(registry.persona_dimensions).lower()
    required_safeguards = {
        "mbti_as_validated_cause",
        "left_right_brain_claim",
        "protected_attribute_outcome_rule",
        "education_equals_intelligence",
        "class_determines_grammar",
    }
    for dimension in registry.persona_dimensions:
        missing = required_safeguards - set(dimension.prohibited_uses)
        if missing:
            issues.append(ValidationIssue("REG-013", "error", dimension.dimension_id, f"missing persona safeguards: {sorted(missing)}"))
    if "left_right_brain_claim" not in serialized_personas:
        issues.append(ValidationIssue("REG-014", "error", "persona_registry", "popular-psychology boundary is not explicit"))

    forbidden_provider_terms = ("openai", "anthropic", "gpt-", "claude", "cursor", "composer")
    for capability in registry.specialist_capabilities:
        serialized = canonical_json(capability).lower()
        if capability.canonical_truth_write:
            issues.append(ValidationIssue("REG-015", "error", capability.capability_id, "specialist cannot write canonical truth"))
        if any(term in serialized for term in forbidden_provider_terms):
            issues.append(ValidationIssue("REG-016", "error", capability.capability_id, "provider identity leaked into portable registry"))
        if capability.classification not in {"portable_core", "runtime_adapter", "provider_probe"}:
            issues.append(ValidationIssue("REG-017", "error", capability.capability_id, "invalid portability classification"))
        if "oracle_truth" not in capability.prohibited_inputs or "private_source_rows" not in capability.prohibited_inputs:
            issues.append(ValidationIssue("REG-018", "error", capability.capability_id, "privacy or oracle boundary missing"))
        if not capability.validator_ids or not capability.qualification_expiry_triggers:
            issues.append(ValidationIssue("REG-019", "error", capability.capability_id, "qualification contract incomplete"))

    passed = not issues
    payload = {
        "revision": VALIDATOR_REVISION,
        "passed": passed,
        "issues": issues,
        "evidence": evidence,
    }
    return ValidationReport(
        validator_revision=VALIDATOR_REVISION,
        passed=passed,
        issues=tuple(issues),
        evidence=tuple(evidence),
        report_hash=digest(payload),
    )


def validate_population_blueprints(
    blueprints: tuple[CaseDesignBlueprint, ...],
    registry: CapabilityRegistry | None = None,
) -> ValidationReport:
    registry = registry or build_capability_registry()
    issues: list[ValidationIssue] = []
    evidence: list[str] = []
    if not blueprints:
        issues.append(ValidationIssue("POP-001", "error", "population", "population cannot be empty"))
    ids = [item.design_id for item in blueprints]
    for duplicate in sorted(_duplicates(ids)):
        issues.append(ValidationIssue("POP-002", "error", duplicate, "duplicate design id"))
    if blueprints:
        seed = blueprints[0].seed
        family_ids = {item.case_family_id for item in blueprints}
        seeds = {item.seed for item in blueprints}
        if len(seeds) != 1:
            issues.append(ValidationIssue("POP-003", "error", "population", "one population receipt must bind one seed"))
        family_readiness = {item.family_id: item.readiness for item in registry.case_families}
        known_families = set(family_readiness)
        for family_id in sorted(family_ids - known_families):
            issues.append(ValidationIssue("POP-004", "error", family_id, "unknown case family"))
        for family_id in sorted(family_ids & known_families):
            if family_readiness[family_id] != "active_g2":
                issues.append(
                    ValidationIssue(
                        "POP-008",
                        "error",
                        family_id,
                        "design-only case family cannot enter a population",
                    )
                )
        for axis in registry.population_axes:
            expected = sorted(_allocate_axis(axis, seed, len(blueprints)))
            observed = sorted(dict(item.sealed_axis_labels).get(axis.axis_id, "") for item in blueprints)
            if observed != expected:
                issues.append(ValidationIssue("POP-005", "error", axis.axis_id, "population distribution does not match deterministic allocation"))
        evidence.append(f"population_hash:{digest(blueprints)}")

    forbidden_operating_terms = (
        "sealed_axis_labels",
        "design_labels",
        "sealed:merits",
        "authorial target",
        "designed_conflict",
        "procedural_defect",
    )
    for blueprint in blueprints:
        operating = canonical_json(blueprint.operating_view()).lower()
        if any(term in operating for term in forbidden_operating_terms):
            issues.append(ValidationIssue("POP-006", "error", blueprint.design_id, "sealed design label leaked into operating view"))
        if not blueprint.design_labels:
            issues.append(ValidationIssue("POP-007", "error", blueprint.design_id, "every blueprint requires at least one sealed design label"))

    passed = not issues
    payload = {
        "revision": VALIDATOR_REVISION,
        "passed": passed,
        "issues": issues,
        "evidence": evidence,
    }
    return ValidationReport(
        validator_revision=VALIDATOR_REVISION,
        passed=passed,
        issues=tuple(issues),
        evidence=tuple(evidence),
        report_hash=digest(payload),
    )

