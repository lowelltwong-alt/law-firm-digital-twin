from __future__ import annotations

from .design_c_contracts import (
    DESIGN_C_BASELINE_ID,
    DESIGN_C_REGISTRY_REVISION,
    DesignCAssetRecord,
    DesignCUnifiedRegistry,
    GateAttachedObligation,
    HumanDecisionRecord,
    LearningLoopRegistryRow,
    RuntimeQualificationPointer,
)


def build_design_c_unified_registry() -> DesignCUnifiedRegistry:
    decisions = (
        HumanDecisionRecord("H-1", "First jurisdiction through data-first rubric", "delegated", "Lowell", "data_first_rubric_with_state_court_skew_explicit", ("jurisdiction_lock",)),
        HumanDecisionRecord("H-2", "Reuse review and release receipts", "adopted", "Lowell", "review_allowed_copying_requires_asset_release_receipt", ("reuse_copy",)),
        HumanDecisionRecord("H-3", "First build scope", "adopted", "Lowell", "G0_G2_employment_walking_skeleton", ("G3_plus", "other_domain_activation")),
        HumanDecisionRecord("H-4", "Corpus license and copyright posture", "pending", "Lowell", "UNSET_FAIL_CLOSED", ("public_release", "release_license")),
        HumanDecisionRecord("H-5", "Three-layer synthetic marking", "adopted", "Lowell", "provenance_manifest_plus_embedded_SYNTHETIC_LFDT_metadata_plus_export_boundary_visible_watermark", ("native_export_until_marking_qualified", "release_assets_until_marking_qualified")),
        HumanDecisionRecord("H-6", "Human capacity budget", "adopted", "Lowell", "zero_scale_capacity_until_weekly_review_capacity_and_sampling_allocations_are_measured", ("multi_case_scale", "unattended_campaign")),
        HumanDecisionRecord("H-7", "Design C baseline freeze and obligation budget", "adopted", "Lowell", "design_c_baseline_v1_frozen_depth_first_obligation_budget", ("unbudgeted_architecture_obligation", "cursor_campaign_until_gates_pass")),
        HumanDecisionRecord("H-8", "Berean standalone posture and naming", "pending", "Lowell", "UNSET_SIMULATION_INTERNAL_ONLY", ("standalone_berean", "public_berean_name")),
        HumanDecisionRecord("H-9", "Medical pack and qualified reviewer", "pending", "Lowell", "UNSET_MEDICAL_INACTIVE", ("medical_pack",)),
        HumanDecisionRecord("H-10", "Non-synced canonical storage and backup", "adopted", "Lowell", "runtime_root_local_setting_LFDT_RUNTIME_ROOT_backup_root_separately_pending_no_canonical_activation_until_boundary_and_backup_qualification", ("canonical_activation_until_physical_isolation_and_backup_qualification",)),
        HumanDecisionRecord("H-11", "Cost ceiling and program budget", "adopted", "Lowell", "zero_multi_case_and_unattended_spend_until_measured_cost_ceiling_is_approved", ("multi_case_scale", "unattended_campaign")),
        HumanDecisionRecord("H-12", "Sealed-key continuity and escrow", "pending", "Lowell", "UNSET_EPHEMERAL_KEYS_ONLY", ("durable_sealed_key", "G3_scale")),
    )

    asset_rows = (
        ("A1", "Governance and receipts", "portable_core", "G0C", "existing_partial", (), ("governance_validator",), ()),
        ("A2", "Contract and schema library", "portable_core", "G0C", "existing_partial", ("A1",), ("design_c_contract_validator",), ()),
        ("A3", "Sealed world assets", "sealed_portable_core", "G0C", "proposed", ("A2", "A4"), ("oracle_isolation_validator",), ("H-10",)),
        ("A4", "Kernel and compiler", "portable_core", "G0C", "existing_partial", ("A1", "A2"), ("kernel_replay_validator",), ()),
        ("A5", "Renderers templates and voice", "portable_core", "G0C_G1", "existing_partial", ("A3", "A4"), ("fidelity_validator",), ("H-5",)),
        ("A6", "Validator and gate suite", "portable_core", "G0C", "existing_partial", ("A2", "A4"), ("negative_control_validator",), ()),
        ("A7", "Operating corpus", "portable_core", "G0C_plus", "proposed", ("A3", "A4", "A6"), ("operating_store_validator",), ("H-10",)),
        ("A8", "Finance ledger", "portable_core", "G0C", "existing_partial", ("A4", "A7"), ("finance_reconciliation_validator",), ("H-10",)),
        ("A9", "Berean core", "portable_core", "G0C_plus", "existing_partial", ("A6", "A7"), ("berean_primitive_validator",), ()),
        ("A10", "Protected evaluation assets", "protected_portable_core", "G0C_plus", "proposed", ("A6", "A7", "A9"), ("split_contamination_validator",), ()),
        ("A11", "Orchestration assets", "runtime_adapter", "G0C_minimal", "existing_partial", ("A2", "A4", "A6"), ("campaign_static_validator",), ("H-6", "H-11")),
        ("A12", "Unified machine-readable registry", "portable_core", "G0C", "proposed", ("A1", "A2"), ("design_c_registry_validator",), ()),
        ("A13", "Learning-loop records", "portable_core", "G0C_plus", "existing_partial", ("A6", "A10", "A12"), ("learning_loop_validator",), ("H-6",)),
        ("A14", "Release and disclosure assets", "portable_core", "pre_G2", "deferred", ("A10", "A12"), ("release_boundary_validator",), ("H-4", "H-5")),
    )
    assets = tuple(
        DesignCAssetRecord(
            asset_id=asset_id,
            title=title,
            portable_class=portable_class,  # type: ignore[arg-type]
            phase=phase,
            status=status,  # type: ignore[arg-type]
            depends_on=depends_on,
            validator_ids=validators,
            human_gate_ids=human_gates,
            do_not_apply=("private_source_rows", "self_activation", "canonical_truth_claim"),
        )
        for asset_id, title, portable_class, phase, status, depends_on, validators, human_gates in asset_rows
    )

    obligations = (
        GateAttachedObligation("DC-O01", "Preserve kernel-only truth and proposal-only workers.", "G0_EXISTING", "binding_existing", "docs/constitution.md", ("kernel_authority_tests",)),
        GateAttachedObligation("DC-O02", "Demonstrate worker-identity denial of sealed paths, keys, and crosswalks plus mutation-proven sealed-to-operating canary containment.", "G0C", "binding_existing", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("E-1",)),
        GateAttachedObligation("DC-O03", "Replay identical inputs in 100 fresh processes with environment drift rejection.", "G0C", "binding_existing", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("E-2",)),
        GateAttachedObligation("DC-O04", "Qualify commit recovery with crash and duplicate-delivery kill drills.", "G0C", "binding_existing", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("E-6",)),
        GateAttachedObligation("DC-O05", "Generate a symmetric two-sided sealed substrate before discovery projections.", "G0C", "binding_existing", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("E-3",)),
        GateAttachedObligation("DC-O06", "Require exact DesignedImperfectionLedger reconciliation.", "G0C", "binding_existing", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("imperfection_reconciliation",)),
        GateAttachedObligation("DC-O07", "Mark every native/exported artifact under the approved synthetic-marking policy.", "NATIVE_EXPORT", "deferred", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("H-5",)),
        GateAttachedObligation("DC-O08", "Activate medical foundations only after H-9 and qualified medical review.", "MEDICAL_PACK", "deferred", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("H-9",)),
        GateAttachedObligation("DC-O09", "Evaluate Temporal only after local queue recovery evidence at the 250-case gate.", "G2_250", "deferred", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("temporal_comparison",)),
        GateAttachedObligation("DC-O10", "Represent merits on liability, causation, damages, procedure, and credibility axes with deterministic single-axis counterfactuals.", "G0C", "binding_existing", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("merits_vector_validator", "counterfactual_sibling_validator")),
        GateAttachedObligation("DC-O11", "Use valid-time and recorded-time assertions plus KnowledgeEvents and RecollectionStates as conflict causes.", "G0C", "binding_existing", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("bitemporal_assertion_validator", "knowledge_recollection_validator")),
        GateAttachedObligation("DC-O12", "Emit assertion manifests that bind every rendered factual span to authorized operating assertions.", "G0C", "binding_existing", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("assertion_manifest_validator",)),
        GateAttachedObligation("DC-O13", "Restrict Berean to OperatingStore-only primitives and deterministic declared conflict classes.", "G0C", "binding_existing", "docs/decisions/fable_design_c_reconciliation_proposal.md", ("berean_primitive_validator", "sealed_access_negative_control")),
    )

    loops = tuple(
        LearningLoopRegistryRow(
            loop_id=f"L{index}",
            title=title,
            status="proposed_active_g0c",
            gate_id="G0C",
            evidence_class=evidence,
            checker_id=checker,
            never_modifies=("world_truth", "validator_thresholds_without_adjudication", "protected_holdout", "authority"),
        )
        for index, (title, evidence, checker) in enumerate(
            (
                ("Security and contamination", "canary_and_surface_scan", "security_checker"),
                ("Generator defect repair", "rejection_cluster", "generator_defect_checker"),
                ("Whole-case coherence", "operating_store_assertions", "coherence_checker"),
                ("Fidelity gate tuning", "adjudicated_gate_disagreement", "fidelity_checker"),
                ("Human adjudication intake", "reviewer_adjudication", "adjudication_checker"),
            )
        )
    )

    simpy = RuntimeQualificationPointer(
        qualification_id="QUAL-SIMPY-4.1.2-G2-V1",
        capability_id="scheduler.simpy_integer_ticks",
        portable_class="runtime_adapter",
        state="qualified_optional_nondefault",
        contract_revision="simulation-scheduler-core-g2-v1",
        adapter_revision="simpy-scheduler-adapter-g2-v1",
        runtime_version="4.1.2",
        evidence_paths=(
            "tests/test_simpy_schedule_adapter.py",
            "generated/g2-simpy-scheduler-v1/summary.json",
        ),
    )
    return DesignCUnifiedRegistry(
        registry_id="registry.design_c.unified.v1",
        baseline_id=DESIGN_C_BASELINE_ID,
        revision=DESIGN_C_REGISTRY_REVISION,
        decisions=decisions,
        assets=assets,
        obligations=obligations,
        loops=loops,
        runtime_qualifications=(simpy,),
        source_receipt_ids=(),
        contains_source_rows=False,
        contains_secrets=False,
        external_effects=False,
        unattended_execution_authorized=False,
        canonical_activation_authorized=False,
    )
