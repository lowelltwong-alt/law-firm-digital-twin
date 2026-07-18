from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath, PureWindowsPath

from .design_c_contracts import (
    DESIGN_C_BASELINE_ID,
    DESIGN_C_CONTRACT_REVISION,
    DESIGN_C_REGISTRY_REVISION,
    DesignCJobManifest,
    DesignCJobResult,
    DesignCUnifiedRegistry,
)
from .hashio import canonical_json


REQUIRED_STOPS = frozenset(
    {
        "canary_leak",
        "replay_mismatch",
        "stale_dependency",
        "authority_boundary",
        "budget_exhausted",
        "unresolved_human_gate",
    }
)


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    counts = Counter(values)
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def validate_design_c_registry(registry: DesignCUnifiedRegistry) -> tuple[str, ...]:
    errors: list[str] = []
    if registry.revision != DESIGN_C_REGISTRY_REVISION or registry.baseline_id != DESIGN_C_BASELINE_ID:
        errors.append("DCR-001:registry_revision_or_baseline_invalid")
    if (
        registry.contains_source_rows
        or registry.contains_secrets
        or registry.external_effects
        or registry.unattended_execution_authorized
        or registry.canonical_activation_authorized
    ):
        errors.append("DCR-002:registry_authority_boundary_invalid")

    decision_ids = tuple(item.decision_id for item in registry.decisions)
    asset_ids = tuple(item.asset_id for item in registry.assets)
    obligation_ids = tuple(item.obligation_id for item in registry.obligations)
    loop_ids = tuple(item.loop_id for item in registry.loops)
    qualification_ids = tuple(item.qualification_id for item in registry.runtime_qualifications)
    for code, values in (
        ("DCR-003", decision_ids),
        ("DCR-004", asset_ids),
        ("DCR-005", obligation_ids),
        ("DCR-006", loop_ids),
        ("DCR-007", qualification_ids),
    ):
        if _duplicates(values):
            errors.append(f"{code}:duplicate_id")
    if set(decision_ids) != {f"H-{index}" for index in range(1, 13)}:
        errors.append("DCR-008:human_decision_coverage_invalid")
    if set(asset_ids) != {f"A{index}" for index in range(1, 15)}:
        errors.append("DCR-009:asset_coverage_invalid")
    if set(loop_ids) != {f"L{index}" for index in range(5)}:
        errors.append("DCR-010:g0c_loop_scope_invalid")

    decisions = {item.decision_id: item for item in registry.decisions}
    expected_statuses = {
        "H-1": "delegated",
        "H-2": "adopted",
        "H-3": "adopted",
        "H-4": "pending",
        "H-5": "adopted",
        "H-6": "adopted",
        "H-7": "adopted",
        "H-8": "pending",
        "H-9": "pending",
        "H-10": "adopted",
        "H-11": "adopted",
        "H-12": "pending",
    }
    for decision_id, expected_status in expected_statuses.items():
        decision = decisions.get(decision_id)
        if (
            decision is None
            or decision.status != expected_status
            or (
                expected_status == "pending"
                and not decision.selected_policy.startswith("UNSET_")
            )
            or (
                expected_status != "pending"
                and decision.selected_policy.startswith("UNSET_")
            )
        ):
            errors.append(f"DCR-011:{decision_id}:decision_state_invalid")
    asset_set = set(asset_ids)
    for asset in registry.assets:
        if not asset.validator_ids or not asset.do_not_apply:
            errors.append(f"DCR-012:{asset.asset_id}:asset_contract_incomplete")
        for dependency in asset.depends_on:
            if dependency not in asset_set or dependency == asset.asset_id:
                errors.append(f"DCR-013:{asset.asset_id}:asset_dependency_invalid")
        for gate in asset.human_gate_ids:
            if gate not in decisions:
                errors.append(f"DCR-014:{asset.asset_id}:unknown_human_gate")
    graph = {asset.asset_id: asset.depends_on for asset in registry.assets}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(asset_id: str) -> bool:
        if asset_id in visiting:
            return True
        if asset_id in visited:
            return False
        visiting.add(asset_id)
        cycle = any(
            dependency in graph and visit(dependency)
            for dependency in graph.get(asset_id, ())
        )
        visiting.remove(asset_id)
        visited.add(asset_id)
        return cycle

    if any(visit(asset_id) for asset_id in graph):
        errors.append("DCR-021:asset_dependency_cycle")
    for obligation in registry.obligations:
        if not obligation.gate_id or not obligation.evidence_ids or obligation.world_truth_authority or obligation.self_activation:
            errors.append(f"DCR-015:{obligation.obligation_id}:obligation_invalid")
        if obligation.status == "proposed":
            errors.append(f"DCR-016:{obligation.obligation_id}:frozen_baseline_has_proposed_obligation")
    for loop in registry.loops:
        if (
            loop.status != "proposed_active_g0c"
            or not loop.human_promotion_required
            or loop.self_promotion
            or "world_truth" not in loop.never_modifies
            or loop.loop_id == loop.checker_id
        ):
            errors.append(f"DCR-017:{loop.loop_id}:loop_authority_invalid")
    for qualification in registry.runtime_qualifications:
        if qualification.canonical_authority or qualification.state != "qualified_optional_nondefault":
            errors.append(f"DCR-018:{qualification.qualification_id}:qualification_authority_invalid")
        if not qualification.evidence_paths:
            errors.append(f"DCR-019:{qualification.qualification_id}:qualification_evidence_missing")

    text = canonical_json(registry).lower()
    for forbidden in ("client_payload", "raw_email_body", "sealed_key_value", "canary_token_value", "pacer_purchase"):
        if forbidden in text:
            errors.append(f"DCR-020:forbidden_registry_content:{forbidden}")
    return tuple(errors)


def validate_design_c_job_manifest(manifest: DesignCJobManifest) -> tuple[str, ...]:
    errors: list[str] = []
    if manifest.contract_revision != DESIGN_C_CONTRACT_REVISION:
        errors.append("DCJ-001:contract_revision_invalid")
    if not manifest.objective or not manifest.non_goals:
        errors.append("DCJ-002:scope_invalid")
    if manifest.write_owner == manifest.checker_id:
        errors.append("DCJ-003:self_checking_job")
    if not manifest.input_commitments or any(len(value) != 64 for _, value in manifest.input_commitments):
        errors.append("DCJ-004:input_commitment_invalid")
    if any(len(value) != 64 for _, value in manifest.dependency_hashes):
        errors.append("DCJ-005:dependency_hash_invalid")
    if not manifest.output_paths or any(
        PurePosixPath(path).is_absolute()
        or PureWindowsPath(path).is_absolute()
        or ".." in PurePosixPath(path).parts
        or ".." in PureWindowsPath(path).parts
        for path in manifest.output_paths
    ):
        errors.append("DCJ-006:output_scope_invalid")
    if not manifest.idempotency_key or not manifest.checkpoint_path:
        errors.append("DCJ-007:recovery_identity_missing")
    budget = manifest.budget
    if (
        budget.max_attempts <= 0
        or budget.max_repairs != 1
        or budget.max_wall_seconds <= 0
        or budget.max_cost_units < 0
        or budget.max_output_bytes <= 0
    ):
        errors.append("DCJ-008:budget_invalid")
    if not REQUIRED_STOPS.issubset(set(manifest.stop_conditions)):
        errors.append("DCJ-009:mandatory_stop_missing")
    if (
        manifest.external_effects
        or manifest.canonical_truth_write
        or manifest.human_gate_auto_advance
        or manifest.unattended_execution_authorized
    ):
        errors.append("DCJ-010:authority_boundary_invalid")
    return tuple(errors)


def validate_design_c_job_result(
    manifest: DesignCJobManifest,
    result: DesignCJobResult,
) -> tuple[str, ...]:
    errors: list[str] = []
    if result.job_id != manifest.job_id or result.manifest_hash != manifest.manifest_hash:
        errors.append("DCJR-001:manifest_binding_invalid")
    if result.attempt_count <= 0 or result.attempt_count > manifest.budget.max_attempts:
        errors.append("DCJR-002:attempt_budget_invalid")
    if result.repair_count < 0 or result.repair_count > manifest.budget.max_repairs:
        errors.append("DCJR-003:repair_budget_invalid")
    if result.cost_units_used < 0 or result.cost_units_used > manifest.budget.max_cost_units:
        errors.append("DCJR-004:cost_budget_invalid")
    if result.wall_seconds_used < 0 or result.wall_seconds_used > manifest.budget.max_wall_seconds:
        errors.append("DCJR-005:wall_budget_invalid")
    if result.checker_id != manifest.checker_id or result.checker_id == manifest.write_owner:
        errors.append("DCJR-006:checker_identity_invalid")
    if result.state == "passed" and (not result.checker_passed or result.failure_codes):
        errors.append("DCJR-007:pass_claim_invalid")
    if result.state != "passed" and result.checker_passed:
        errors.append("DCJR-008:failure_checker_state_invalid")
    if not set(manifest.required_gate_ids).issubset(set(result.human_gate_ids_satisfied)) and result.state == "passed":
        errors.append("DCJR-009:human_gate_missing")
    if result.canonical_admission or result.self_approved:
        errors.append("DCJR-010:result_authority_invalid")
    return tuple(errors)

