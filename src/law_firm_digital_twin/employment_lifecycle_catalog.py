from __future__ import annotations

from collections.abc import Iterable

from .litigation_lifecycle_contracts import (
    BranchScope,
    EmploymentLifecycleDocumentCatalog,
    LifecycleDocumentType,
    LifecycleStageContract,
)


CATALOG_ID = "catalog.employment_defense.full_lifecycle.g2.v1"


STAGE_DEFINITIONS: tuple[tuple[str, int, str, BranchScope], ...] = (
    ("referral_intake", 10, "Referral, conflicts, and matter intake", "universal"),
    ("carrier_management", 20, "Carrier reporting and authority", "universal"),
    ("early_investigation", 30, "Preservation and early investigation", "universal"),
    ("administrative_agency", 35, "Administrative-agency design branch", "administrative_agency_design_only"),
    ("pleadings_case_management", 40, "Pleadings and case management", "universal"),
    ("discovery_ediscovery", 50, "Discovery and eDiscovery", "universal"),
    ("depositions", 60, "Fact and organization depositions", "universal"),
    ("experts", 70, "Expert retention and bounded opinion workflow", "universal"),
    ("motion_practice", 80, "Motion practice", "motion"),
    ("settlement", 90, "Negotiated settlement", "settlement"),
    ("mediation", 100, "Mediation", "mediation"),
    ("arbitration", 110, "Arbitration design branch", "arbitration_design_only"),
    ("trial", 120, "Trial preparation and modeled trial", "trial"),
    ("appeal", 130, "Appeal design branch", "appeal"),
    ("billing_finance", 140, "Billing, reductions, appeals, payment, and AR", "universal"),
    ("closure_retention", 150, "Resolution transition, closeout, and retention", "universal"),
)


# id, label, record kind, responsible roles, recipients, confidentiality, filing intent, billing category
DocumentRow = tuple[
    str,
    str,
    str,
    tuple[str, ...],
    tuple[str, ...],
    str,
    str,
    str,
]


def _row(
    document_type_id: str,
    label: str,
    record_kind: str,
    responsible: tuple[str, ...],
    recipients: tuple[str, ...] = (),
    confidentiality: str = "internal_work_product",
    filing_intent: str = "not_a_filing",
    billing_category: str = "case_management",
) -> DocumentRow:
    return (
        document_type_id,
        label,
        record_kind,
        responsible,
        recipients,
        confidentiality,
        filing_intent,
        billing_category,
    )


DOCUMENT_GROUPS: tuple[tuple[str, BranchScope, str | None, tuple[DocumentRow, ...]], ...] = (
    (
        "referral_intake", "universal", None,
        (
            _row("referral_packet", "Synthetic referral packet", "structured_record", ("intake",), ("conflicts",)),
            _row("loss_or_claim_notice", "Synthetic loss or claim notice", "correspondence", ("intake",), ("carrier",)),
            _row("pre_suit_demand_index", "Pre-suit demand index", "index", ("intake",), ("lawyer",)),
            _row("conflicts_search_request", "Conflicts search request", "structured_record", ("intake",), ("conflicts",)),
            _row("conflicts_search_report", "Conflicts search report", "report_surrogate", ("conflicts",), ("lawyer",), "attorney_client_simulated"),
            _row("conflicts_resolution_record", "Conflicts resolution record", "structured_record", ("lawyer",), ("intake",), "attorney_client_simulated"),
            _row("engagement_scope_record", "Engagement scope record", "agreement_surrogate", ("lawyer",), ("carrier",), "carrier_confidential_simulated"),
            _row("outside_guidelines_acknowledgment", "Synthetic outside-guidelines acknowledgment", "structured_record", ("lawyer",), ("carrier",), "carrier_confidential_simulated"),
            _row("matter_opening_checklist", "Matter opening checklist", "structured_record", ("intake",), ("lawyer",)),
            _row("initial_case_assessment", "Initial case assessment", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated"),
        ),
    ),
    (
        "carrier_management", "universal", "initial_case_assessment",
        (
            _row("coverage_status_summary", "Synthetic coverage-status summary", "memorandum", ("lawyer",), ("carrier",), "attorney_client_simulated"),
            _row("reporting_calendar", "Carrier reporting calendar", "structured_record", ("paralegal",), ("lawyer", "carrier"), "carrier_confidential_simulated"),
            _row("rate_and_timekeeper_schedule", "Synthetic rate and timekeeper schedule", "tabular_record", ("billing",), ("carrier",), "billing_confidential_simulated", billing_category="billing_admin"),
            _row("initial_litigation_budget", "Initial litigation budget", "tabular_record", ("lawyer", "billing"), ("carrier",), "carrier_confidential_simulated", billing_category="budgeting"),
            _row("budget_authority_record", "Budget authority record", "structured_record", ("carrier",), ("lawyer", "billing"), "carrier_confidential_simulated", billing_category="budgeting"),
            _row("case_strategy_report", "Case strategy report", "report_surrogate", ("lawyer",), ("carrier",), "carrier_confidential_simulated"),
            _row("exposure_update", "Exposure update", "report_surrogate", ("lawyer",), ("carrier",), "carrier_confidential_simulated"),
            _row("status_report", "Periodic status report", "report_surrogate", ("lawyer",), ("carrier",), "carrier_confidential_simulated"),
            _row("authority_request", "Authority request", "correspondence", ("lawyer",), ("carrier",), "carrier_confidential_simulated"),
            _row("authority_decision_record", "Authority decision record", "structured_record", ("carrier",), ("lawyer",), "carrier_confidential_simulated"),
        ),
    ),
    (
        "early_investigation", "universal", "matter_opening_checklist",
        (
            _row("litigation_hold_trigger", "Synthetic litigation-hold trigger", "structured_record", ("lawyer",), ("paralegal",), "attorney_client_simulated", billing_category="ediscovery"),
            _row("preservation_notice", "Synthetic preservation notice", "correspondence", ("paralegal",), ("witness",), "attorney_client_simulated", billing_category="ediscovery"),
            _row("preservation_acknowledgment_log", "Preservation acknowledgment log", "log", ("paralegal",), ("lawyer",), "attorney_client_simulated", billing_category="ediscovery"),
            _row("custodian_map", "Synthetic custodian map", "structured_record", ("paralegal",), ("lawyer",), "attorney_client_simulated", billing_category="ediscovery"),
            _row("system_and_source_inventory", "Synthetic system and source inventory", "index", ("paralegal",), ("lawyer",), "attorney_client_simulated", billing_category="ediscovery"),
            _row("witness_contact_log", "Witness contact log", "log", ("paralegal",), ("lawyer",)),
            _row("witness_interview_outline", "Witness interview outline", "memorandum", ("lawyer",), ("witness",), "attorney_client_simulated"),
            _row("witness_interview_memorandum", "Witness interview memorandum", "memorandum", ("lawyer",), (), "attorney_client_simulated"),
            _row("employment_record_index", "Employment record index", "index", ("paralegal",), ("lawyer",), "discovery_confidential_simulated"),
            _row("personnel_file_record_surrogate", "Synthetic personnel-file record surrogate", "structured_record", ("paralegal",), ("lawyer",), "discovery_confidential_simulated"),
            _row("discipline_performance_record_surrogate", "Synthetic discipline and performance record surrogate", "structured_record", ("paralegal",), ("lawyer",), "discovery_confidential_simulated"),
            _row("leave_accommodation_record_surrogate", "Synthetic leave and accommodation record surrogate", "structured_record", ("paralegal",), ("lawyer",), "discovery_confidential_simulated"),
            _row("complaint_investigation_record_surrogate", "Synthetic complaint and investigation record surrogate", "structured_record", ("paralegal",), ("lawyer",), "discovery_confidential_simulated"),
            _row("policy_acknowledgment_record_surrogate", "Synthetic policy-acknowledgment record surrogate", "structured_record", ("paralegal",), ("lawyer",), "discovery_confidential_simulated"),
            _row("fact_chronology", "Operating fact chronology", "structured_record", ("paralegal", "lawyer"), (), "attorney_client_simulated"),
            _row("damages_source_index", "Synthetic damages-source index", "index", ("paralegal",), ("lawyer",), "discovery_confidential_simulated"),
            _row("early_case_evaluation", "Early case evaluation", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated"),
        ),
    ),
    (
        "administrative_agency", "administrative_agency_design_only", "early_case_evaluation",
        (
            _row("administrative_agency_charge_or_notice_index", "Administrative-agency charge or notice index", "index", ("paralegal",), ("lawyer",), billing_category="agency_response"),
            _row("administrative_agency_response_strategy", "Administrative-agency response strategy", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="agency_response"),
            _row("administrative_agency_position_response_surrogate", "Employer position-response surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="agency_response"),
            _row("administrative_agency_information_request", "Administrative-agency information-request surrogate", "structured_record", ("paralegal",), ("lawyer",), billing_category="agency_response"),
            _row("administrative_agency_response_production_index", "Administrative-agency response production index", "index", ("paralegal",), ("lawyer",), "discovery_confidential_simulated", billing_category="agency_response"),
            _row("administrative_agency_adr_evaluation", "Administrative-agency ADR evaluation", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="agency_adr"),
            _row("administrative_agency_conciliation_record", "Administrative-agency mediation or conciliation record", "structured_record", ("lawyer",), ("carrier",), "mediation_confidential_simulated", billing_category="agency_adr"),
            _row("administrative_agency_result_record", "Administrative-agency result surrogate", "structured_record", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="agency_response"),
            _row("administrative_agency_transition_surrogate", "Administrative-agency litigation-transition surrogate", "structured_record", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="agency_response"),
            _row("administrative_agency_file_transition_checklist", "Administrative-agency file transition checklist", "structured_record", ("paralegal",), ("lawyer",), billing_category="agency_response"),
        ),
    ),
    (
        "pleadings_case_management", "universal", "early_case_evaluation",
        (
            _row("complaint_or_petition_index", "Complaint or petition index", "index", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="pleadings"),
            _row("service_record", "Synthetic service record", "structured_record", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="pleadings"),
            _row("forum_and_venue_analysis", "Forum and venue analysis", "memorandum", ("lawyer",), (), "attorney_client_simulated", billing_category="pleadings"),
            _row("responsive_pleading_outline", "Responsive pleading outline", "memorandum", ("lawyer",), (), "attorney_client_simulated", billing_category="pleadings"),
            _row("answer_surrogate", "Answer surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="pleadings"),
            _row("affirmative_defense_index", "Affirmative-defense issue index", "index", ("lawyer",), (), "attorney_client_simulated", billing_category="pleadings"),
            _row("appearance_surrogate", "Appearance surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="pleadings"),
            _row("case_management_proposal", "Case-management proposal", "structured_record", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only"),
            _row("scheduling_record", "Synthetic scheduling record", "structured_record", ("docketing",), ("lawyer", "paralegal")),
            _row("deadline_calculation_proposal", "Synthetic deadline calculation proposal", "structured_record", ("docketing",), ("lawyer",)),
            _row("independent_deadline_reconciliation", "Independent deadline reconciliation", "structured_record", ("deadline_reviewer",), ("lawyer",)),
            _row("case_management_conference_note", "Case-management conference note", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated"),
        ),
    ),
    (
        "discovery_ediscovery", "universal", "independent_deadline_reconciliation",
        (
            _row("discovery_plan", "Discovery plan", "memorandum", ("lawyer", "paralegal"), (), "attorney_client_simulated", billing_category="discovery"),
            _row("esi_protocol_surrogate", "ESI protocol surrogate", "agreement_surrogate", ("lawyer",), ("paralegal",), "discovery_confidential_simulated", billing_category="ediscovery"),
            _row("protective_order_surrogate", "Protective-order surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), "discovery_confidential_simulated", "simulated_filing_intent_only", "discovery"),
            _row("written_discovery_request_index", "Written discovery request index", "index", ("paralegal",), ("lawyer",), billing_category="discovery"),
            _row("interrogatory_response_workbook", "Interrogatory response workbook", "structured_record", ("lawyer", "paralegal"), ("witness",), "attorney_client_simulated", billing_category="discovery"),
            _row("document_request_response_workbook", "Document request response workbook", "structured_record", ("lawyer", "paralegal"), ("witness",), "attorney_client_simulated", billing_category="discovery"),
            _row("admission_request_response_workbook", "Admission request response workbook", "structured_record", ("lawyer",), ("witness",), "attorney_client_simulated", billing_category="discovery"),
            _row("collection_plan", "Synthetic collection plan", "memorandum", ("paralegal",), ("lawyer",), "attorney_client_simulated", billing_category="ediscovery"),
            _row("collection_log", "Synthetic collection log", "log", ("paralegal",), ("lawyer",), "discovery_confidential_simulated", billing_category="ediscovery"),
            _row("processing_exception_log", "Processing exception log", "log", ("paralegal",), ("lawyer",), "attorney_client_simulated", billing_category="ediscovery"),
            _row("review_protocol", "Document review protocol", "memorandum", ("lawyer",), ("paralegal",), "attorney_client_simulated", billing_category="ediscovery"),
            _row("review_batch_manifest", "Review batch manifest", "structured_record", ("paralegal",), ("lawyer",), "discovery_confidential_simulated", billing_category="ediscovery"),
            _row("responsiveness_privilege_decision_log", "Responsiveness and privilege decision log", "log", ("lawyer",), ("paralegal",), "attorney_client_simulated", billing_category="ediscovery"),
            _row("privilege_log_surrogate", "Privilege-log surrogate", "tabular_record", ("lawyer", "paralegal"), (), "attorney_client_simulated", billing_category="ediscovery"),
            _row("production_manifest", "Synthetic production manifest", "structured_record", ("paralegal",), ("lawyer",), "discovery_confidential_simulated", billing_category="ediscovery"),
            _row("production_transmittal", "Synthetic production transmittal", "correspondence", ("lawyer",), ("paralegal",), "discovery_confidential_simulated", billing_category="discovery"),
            _row("discovery_deficiency_letter", "Discovery deficiency letter surrogate", "correspondence", ("lawyer",), ("paralegal",), billing_category="discovery"),
            _row("meet_and_confer_memorandum", "Meet-and-confer memorandum", "memorandum", ("lawyer",), ("carrier",), "attorney_client_simulated", billing_category="discovery"),
            _row("subpoena_surrogate", "Third-party subpoena surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="discovery"),
            _row("third_party_response_index", "Third-party response index", "index", ("paralegal",), ("lawyer",), "discovery_confidential_simulated", billing_category="discovery"),
        ),
    ),
    (
        "depositions", "universal", "production_transmittal",
        (
            _row("deposition_strategy_memorandum", "Deposition strategy memorandum", "memorandum", ("lawyer",), (), "attorney_client_simulated", billing_category="depositions"),
            _row("deposition_notice_surrogate", "Deposition notice surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="depositions"),
            _row("organization_representative_topic_list", "Organization-representative topic list", "structured_record", ("lawyer",), ("witness",), "attorney_client_simulated", billing_category="depositions"),
            _row("witness_preparation_memorandum", "Witness preparation memorandum", "memorandum", ("lawyer",), ("witness",), "attorney_client_simulated", billing_category="depositions"),
            _row("deposition_outline", "Deposition outline", "memorandum", ("lawyer",), (), "attorney_client_simulated", billing_category="depositions"),
            _row("deposition_exhibit_index", "Deposition exhibit index", "index", ("paralegal",), ("lawyer",), "discovery_confidential_simulated", billing_category="depositions"),
            _row("deposition_transcript_surrogate", "Deposition transcript intake surrogate", "transcript_surrogate", ("paralegal",), ("lawyer",), "discovery_confidential_simulated", billing_category="depositions"),
            _row("deposition_errata_record", "Deposition errata record", "structured_record", ("witness",), ("lawyer",), "discovery_confidential_simulated", billing_category="depositions"),
            _row("deposition_digest", "Deposition digest", "memorandum", ("lawyer", "paralegal"), ("carrier",), "carrier_confidential_simulated", billing_category="depositions"),
            _row("testimony_conflict_update", "Testimony conflict update", "structured_record", ("lawyer",), (), "attorney_client_simulated", billing_category="depositions"),
        ),
    ),
    (
        "experts", "universal", "deposition_digest",
        (
            _row("expert_need_assessment", "Expert need assessment", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="experts"),
            _row("expert_conflict_and_independence_record", "Expert conflict and independence record", "structured_record", ("expert",), ("lawyer",), "expert_work_product_simulated", billing_category="experts"),
            _row("expert_independence_counsel_verification", "Counsel verification of expert conflict and independence record", "structured_record", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="experts"),
            _row("expert_retention_scope", "Expert retention scope", "agreement_surrogate", ("lawyer",), ("expert", "carrier"), "expert_work_product_simulated", billing_category="experts"),
            _row("expert_materials_index", "Expert materials index", "index", ("paralegal",), ("expert", "lawyer"), "expert_work_product_simulated", billing_category="experts"),
            _row("expert_method_and_limitations_record", "Expert method and limitations record", "structured_record", ("expert",), ("lawyer",), "expert_work_product_simulated", billing_category="experts"),
            _row("expert_report_surrogate", "Expert report surrogate", "report_surrogate", ("expert",), ("lawyer",), "expert_work_product_simulated", billing_category="experts"),
            _row("expert_supplement_surrogate", "Expert supplement surrogate", "report_surrogate", ("expert",), ("lawyer",), "expert_work_product_simulated", billing_category="experts"),
            _row("expert_rebuttal_surrogate", "Expert rebuttal surrogate", "report_surrogate", ("expert",), ("lawyer",), "expert_work_product_simulated", billing_category="experts"),
            _row("expert_deposition_preparation", "Expert deposition preparation", "memorandum", ("lawyer", "expert"), (), "expert_work_product_simulated", billing_category="experts"),
            _row("expert_deposition_digest", "Expert deposition digest", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="experts"),
        ),
    ),
    (
        "motion_practice", "motion", "expert_report_surrogate",
        (
            _row("motion_issue_assessment", "Motion issue assessment", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="motions"),
            _row("motion_surrogate", "Motion surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="motions"),
            _row("statement_of_facts_surrogate", "Statement-of-facts surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="motions"),
            _row("motion_exhibit_index", "Motion exhibit index", "index", ("paralegal",), ("lawyer",), billing_category="motions"),
            _row("motion_opposition_surrogate", "Motion opposition surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="motions"),
            _row("motion_reply_surrogate", "Motion reply surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="motions"),
            _row("motion_hearing_note", "Motion hearing note", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="motions"),
            _row("motion_order_surrogate", "Motion order surrogate", "structured_record", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="motions"),
        ),
    ),
    (
        "settlement", "settlement", "early_case_evaluation",
        (
            _row("settlement_evaluation", "Settlement evaluation", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="settlement"),
            _row("settlement_authority_request", "Settlement authority request", "correspondence", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="settlement"),
            _row("settlement_authority_record", "Settlement authority record", "structured_record", ("carrier",), ("lawyer",), "carrier_confidential_simulated", billing_category="settlement"),
            _row("negotiation_event_log", "Confidential negotiation event log", "log", ("lawyer",), ("carrier",), "attorney_client_simulated", billing_category="settlement"),
            _row("settlement_term_sheet", "Synthetic settlement term sheet", "agreement_surrogate", ("lawyer",), ("carrier",), "attorney_client_simulated", billing_category="settlement"),
            _row("settlement_agreement_surrogate", "Settlement agreement surrogate", "agreement_surrogate", ("lawyer",), ("carrier",), "attorney_client_simulated", billing_category="settlement"),
            _row("release_surrogate", "Release surrogate", "agreement_surrogate", ("lawyer",), ("carrier",), "attorney_client_simulated", billing_category="settlement"),
            _row("dismissal_surrogate", "Dismissal surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="settlement"),
        ),
    ),
    (
        "mediation", "mediation", "deposition_digest",
        (
            _row("mediator_selection_record", "Mediator selection record", "structured_record", ("lawyer",), ("carrier",), "mediation_confidential_simulated", billing_category="mediation"),
            _row("mediation_authority_request", "Mediation authority request", "correspondence", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="mediation"),
            _row("mediation_statement_surrogate", "Mediation statement surrogate", "memorandum", ("lawyer",), ("carrier",), "mediation_confidential_simulated", billing_category="mediation"),
            _row("mediation_exhibit_index", "Mediation exhibit index", "index", ("paralegal",), ("lawyer",), "mediation_confidential_simulated", billing_category="mediation"),
            _row("mediation_session_log", "Mediation session log", "log", ("lawyer",), ("carrier",), "mediation_confidential_simulated", billing_category="mediation"),
            _row("mediation_term_sheet", "Mediation term sheet surrogate", "agreement_surrogate", ("lawyer",), ("carrier",), "mediation_confidential_simulated", billing_category="mediation"),
            _row("mediation_impasse_record", "Mediation impasse record", "structured_record", ("lawyer",), ("carrier",), "mediation_confidential_simulated", billing_category="mediation"),
        ),
    ),
    (
        "arbitration", "arbitration_design_only", "early_case_evaluation",
        (
            _row("arbitration_submission_surrogate", "Arbitration submission surrogate", "agreement_surrogate", ("lawyer",), ("carrier",), "attorney_client_simulated", billing_category="arbitration"),
            _row("arbitration_demand_answer_index", "Arbitration demand and answer index", "index", ("paralegal",), ("lawyer",), billing_category="arbitration"),
            _row("arbitration_procedure_record", "Synthetic arbitration procedure record", "structured_record", ("lawyer",), ("paralegal",), billing_category="arbitration"),
            _row("arbitration_discovery_protocol", "Arbitration discovery protocol surrogate", "agreement_surrogate", ("lawyer",), ("paralegal",), billing_category="arbitration"),
            _row("arbitration_prehearing_brief_surrogate", "Arbitration prehearing brief surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="arbitration"),
            _row("arbitration_hearing_index", "Arbitration hearing index", "index", ("paralegal",), ("lawyer",), billing_category="arbitration"),
            _row("arbitration_award_surrogate", "Arbitration award surrogate", "structured_record", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="arbitration"),
        ),
    ),
    (
        "trial", "trial", "expert_report_surrogate",
        (
            _row("pretrial_strategy_memorandum", "Pretrial strategy memorandum", "memorandum", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="trial"),
            _row("pretrial_order_surrogate", "Pretrial order surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="trial"),
            _row("trial_witness_list", "Trial witness list surrogate", "index", ("lawyer", "paralegal"), (), filing_intent="simulated_filing_intent_only", billing_category="trial"),
            _row("trial_exhibit_list", "Trial exhibit list surrogate", "index", ("lawyer", "paralegal"), (), filing_intent="simulated_filing_intent_only", billing_category="trial"),
            _row("motion_in_limine_surrogate", "Motion-in-limine surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="trial"),
            _row("voir_dire_topic_plan", "Voir-dire topic plan", "memorandum", ("lawyer",), (), "attorney_client_simulated", billing_category="trial"),
            _row("instruction_and_verdict_form_surrogate", "Instruction and verdict-form surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="trial"),
            _row("trial_examination_outline", "Trial examination outline", "memorandum", ("lawyer",), (), "attorney_client_simulated", billing_category="trial"),
            _row("trial_demonstrative_index", "Trial demonstrative index", "presentation_surrogate", ("lawyer", "paralegal"), (), billing_category="trial"),
            _row("trial_daily_report", "Modeled trial daily report", "report_surrogate", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="trial"),
            _row("verdict_and_judgment_surrogate", "Verdict and judgment surrogate", "structured_record", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="trial"),
        ),
    ),
    (
        "appeal", "appeal", "verdict_and_judgment_surrogate",
        (
            _row("appeal_authority_record", "Appeal authority record", "structured_record", ("carrier",), ("lawyer",), "carrier_confidential_simulated", billing_category="appeal"),
            _row("notice_of_appeal_surrogate", "Notice-of-appeal surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="appeal"),
            _row("record_designation_index", "Record-designation index", "index", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="appeal"),
            _row("appellate_brief_surrogate", "Appellate brief surrogate", "filing_surrogate", ("lawyer",), ("paralegal",), filing_intent="simulated_filing_intent_only", billing_category="appeal"),
            _row("appellate_appendix_index", "Appellate appendix index", "index", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="appeal"),
            _row("oral_argument_preparation", "Oral argument preparation", "memorandum", ("lawyer",), (), "attorney_client_simulated", billing_category="appeal"),
            _row("appellate_decision_surrogate", "Appellate decision surrogate", "structured_record", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="appeal"),
            _row("mandate_or_remand_record", "Mandate or remand record surrogate", "structured_record", ("paralegal",), ("lawyer",), filing_intent="simulated_filing_intent_only", billing_category="appeal"),
        ),
    ),
    (
        "billing_finance", "universal", "rate_and_timekeeper_schedule",
        (
            _row("work_event_record", "Synthetic work event record", "structured_record", ("lawyer", "paralegal"), ("billing",), "billing_confidential_simulated", billing_category="timekeeping"),
            _row("time_entry", "Synthetic time entry", "structured_record", ("lawyer", "paralegal"), ("billing",), "billing_confidential_simulated", billing_category="timekeeping"),
            _row("expense_entry", "Synthetic expense entry", "structured_record", ("paralegal",), ("billing",), "billing_confidential_simulated", billing_category="expenses"),
            _row("prebill_review_record", "Prebill review record", "structured_record", ("billing", "lawyer"), (), "billing_confidential_simulated", billing_category="prebill"),
            _row("invoice", "Synthetic invoice", "tabular_record", ("billing",), ("carrier",), "billing_confidential_simulated", billing_category="invoice"),
            _row("carrier_audit_notice", "Synthetic carrier audit notice", "structured_record", ("carrier",), ("billing", "lawyer"), "billing_confidential_simulated", billing_category="audit"),
            _row("billing_reduction_record", "Billing reduction or rejection record", "structured_record", ("carrier",), ("billing",), "billing_confidential_simulated", billing_category="audit"),
            _row("billing_appeal_assessment", "Billing appeal assessment", "memorandum", ("billing", "lawyer"), (), "billing_confidential_simulated", billing_category="billing_appeal"),
            _row("billing_appeal", "Synthetic billing appeal", "correspondence", ("billing",), ("carrier",), "billing_confidential_simulated", billing_category="billing_appeal"),
            _row("billing_appeal_decision", "Billing appeal decision", "structured_record", ("carrier",), ("billing",), "billing_confidential_simulated", billing_category="billing_appeal"),
            _row("revised_invoice", "Revised synthetic invoice", "tabular_record", ("billing",), ("carrier",), "billing_confidential_simulated", billing_category="invoice"),
            _row("payment_advice", "Synthetic payment advice", "structured_record", ("carrier",), ("billing",), "billing_confidential_simulated", billing_category="payment"),
            _row("cash_application_record", "Cash application record", "structured_record", ("billing",), (), "billing_confidential_simulated", billing_category="payment"),
            _row("write_off_record", "Write-off record", "structured_record", ("billing", "lawyer"), (), "billing_confidential_simulated", billing_category="writeoff"),
            _row("ar_aging_record", "Accounts-receivable aging record", "tabular_record", ("billing",), ("lawyer",), "billing_confidential_simulated", billing_category="collections"),
            _row("finance_reconciliation", "Finance reconciliation", "structured_record", ("billing",), ("lawyer",), "billing_confidential_simulated", billing_category="reconciliation"),
            _row("final_invoice_record", "Final invoice record", "structured_record", ("billing",), ("carrier",), "billing_confidential_simulated", billing_category="invoice"),
        ),
    ),
    (
        "closure_retention", "universal", "finance_reconciliation",
        (
            _row("resolution_transition_record", "Kernel-event-bound resolution transition record", "structured_record", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="closeout"),
            _row("settlement_or_judgment_payment_confirmation", "Synthetic resolution-payment confirmation", "structured_record", ("billing",), ("lawyer",), "billing_confidential_simulated", billing_category="closeout"),
            _row("final_case_report", "Final case report", "report_surrogate", ("lawyer",), ("carrier",), "carrier_confidential_simulated", billing_category="closeout"),
            _row("closing_correspondence", "Synthetic closing correspondence", "correspondence", ("lawyer",), ("carrier",), "attorney_client_simulated", billing_category="closeout"),
            _row("file_transfer_index", "File transfer index", "index", ("paralegal",), ("lawyer",), "attorney_client_simulated", billing_category="closeout"),
            _row("retention_schedule", "Synthetic retention schedule", "structured_record", ("paralegal",), ("lawyer",), "attorney_client_simulated", billing_category="closeout"),
            _row("conflict_history_update", "Conflict history update", "structured_record", ("conflicts",), ("lawyer",), "attorney_client_simulated", billing_category="closeout"),
            _row("learning_candidate_receipt", "Learning-candidate isolation receipt", "structured_record", ("lawyer",), (), "attorney_client_simulated", billing_category="closeout"),
            _row("matter_closure_checklist", "Matter closure checklist", "structured_record", ("lawyer",), ("billing", "paralegal"), "attorney_client_simulated", billing_category="closeout"),
            _row("archive_integrity_receipt", "Synthetic archive integrity receipt", "structured_record", ("paralegal",), ("lawyer",), "attorney_client_simulated", billing_category="closeout"),
        ),
    ),
)


STAGE_FACT_DOMAINS = {
    "referral_intake": ("employment_action", "damages"),
    "carrier_management": ("employment_action", "damages"),
    "early_investigation": ("employment_action", "policy", "attendance", "protected_activity", "damages"),
    "administrative_agency": ("employment_action", "policy", "protected_activity", "damages"),
    "pleadings_case_management": ("employment_action", "policy", "damages"),
    "discovery_ediscovery": ("employment_action", "policy", "attendance", "protected_activity", "damages"),
    "depositions": ("employment_action", "policy", "attendance", "protected_activity"),
    "experts": ("employment_action", "policy", "attendance", "protected_activity"),
    "motion_practice": ("employment_action", "policy", "damages"),
    "settlement": ("employment_action", "damages"),
    "mediation": ("employment_action", "damages"),
    "arbitration": ("employment_action", "damages"),
    "trial": ("employment_action", "policy", "attendance", "protected_activity", "damages"),
    "appeal": ("employment_action", "damages"),
    "billing_finance": ("employment_action",),
    "closure_retention": ("employment_action", "damages"),
}


def _activation_events(scope: BranchScope, stage_id: str) -> tuple[str, ...]:
    if scope == "universal":
        return (f"deferred.kernel_adapter_unimplemented.stage.{stage_id}",)
    return (f"deferred.kernel_adapter_unimplemented.branch.{scope}",)


def _build_documents() -> tuple[LifecycleDocumentType, ...]:
    documents: list[LifecycleDocumentType] = []
    for stage_id, scope, base_dependency, rows in DOCUMENT_GROUPS:
        previous = base_dependency
        for row in rows:
            (
                document_type_id,
                label,
                record_kind,
                responsible,
                recipients,
                confidentiality,
                filing_intent,
                billing_category,
            ) = row
            prerequisites = (previous,) if previous else ()
            documents.append(
                LifecycleDocumentType(
                    document_type_id=document_type_id,
                    stage_id=stage_id,
                    label=label,
                    record_kind=record_kind,
                    responsible_role_ids=responsible,
                    recipient_role_ids=recipients,
                    prerequisite_type_ids=prerequisites,
                    activation_event_ids=_activation_events(scope, stage_id),
                    branch_scope=scope,
                    confidentiality_class=confidentiality,
                    target_shape=record_kind,
                    required_metadata_keys=(
                        "document_type_id",
                        "created_day",
                        "synthetic",
                        "version_id",
                        "custody_hash",
                    ),
                    fact_domain_dependencies=STAGE_FACT_DOMAINS[stage_id],
                    custody_policy_id="custody.synthetic_hash_stable.v1",
                    versioning_policy_id="version.optional_supersession.v1",
                    source_class="synthetic_design_specification",
                    rule_admission_state="no_rules_admitted",
                    filing_intent=filing_intent,  # type: ignore[arg-type]
                    billing_task_category=billing_category,
                )
            )
            previous = document_type_id
    return tuple(documents)


def build_employment_lifecycle_document_catalog() -> EmploymentLifecycleDocumentCatalog:
    stages = tuple(
        LifecycleStageContract(
            stage_id=stage_id,
            ordinal=ordinal,
            label=label,
            branch_scope=scope,
            entry_event_ids=_activation_events(scope, stage_id),
            exit_event_ids=(f"kernel.stage_complete.{stage_id}",),
        )
        for stage_id, ordinal, label, scope in STAGE_DEFINITIONS
    )
    return EmploymentLifecycleDocumentCatalog(
        catalog_id=CATALOG_ID,
        case_family_id="employment_defense_g2",
        stages=stages,
        document_types=_build_documents(),
        source_admission_state="no_sources_admitted",
        external_access=False,
        runtime_execution=False,
        learning_eligible=False,
        canonical_truth_write=False,
        activation_gate="human_document_family_activation_and_fixture_qualification",
    )


def iter_document_type_ids() -> Iterable[str]:
    return (item.document_type_id for item in _build_documents())

