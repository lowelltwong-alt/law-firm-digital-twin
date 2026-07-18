from __future__ import annotations

from dataclasses import replace

from law_firm_digital_twin.technology_adoption import (
    build_technology_adoption_catalog,
    validate_technology_adoption_catalog,
)


def test_requested_technology_family_is_complete_with_only_bounded_simpy_active() -> None:
    catalog = build_technology_adoption_catalog()
    assert validate_technology_adoption_catalog(catalog) == ()
    assert len(catalog.entries) == 16
    assert {item.technology_id for item in catalog.entries} == {
        "simpy",
        "temporal_python_sdk",
        "edrm_model",
        "apache_tika",
        "tesseract_ocr",
        "sali_lmss",
        "ledes_1998b",
        "utbms_litigation_codes",
        "synthea",
        "hl7_fhir_r4",
        "graph_reasoning_stack",
        "temporal_reasoning_stack",
        "testing_validation_stack",
        "construction_domain_stack",
        "traffic_reconstruction_stack",
        "biomechanics_stack",
    }
    simpy = next(item for item in catalog.entries if item.technology_id == "simpy")
    inactive = tuple(item for item in catalog.entries if item.technology_id != "simpy")
    assert simpy.dependency_installed
    assert simpy.source_code_admitted
    assert simpy.runtime_execution
    assert simpy.qualified_version == "4.1.2"
    assert simpy.license_id == "MIT"
    assert all(not item.dependency_installed for item in inactive)
    assert all(not item.runtime_execution for item in inactive)
    assert all(not item.external_access for item in catalog.entries)
    assert all(not item.canonical_truth_write for item in catalog.entries)
    assert all(len(item.qualification_gate_ids) == 7 for item in catalog.entries)


def test_simpy_and_temporal_have_separate_authority_scopes() -> None:
    entries = {
        item.technology_id: item for item in build_technology_adoption_catalog().entries
    }
    assert entries["simpy"].integration_contract_id == "adapter.simulation_clock.simpy.v1"
    assert entries["simpy"].adoption_state == "bounded_adapter_active_g2"
    assert entries["temporal_python_sdk"].integration_contract_id == "adapter.orchestration.temporal_python.v1"
    assert entries["temporal_python_sdk"].adoption_state == "approved_later_orchestration_adapter"
    assert "world_kernel_execution" in entries["temporal_python_sdk"].prohibited_uses


def test_ediscovery_billing_and_medical_stacks_are_explicitly_bounded() -> None:
    entries = {
        item.technology_id: item for item in build_technology_adoption_catalog().entries
    }
    assert "mandatory_waterfall_claim" in entries["edrm_model"].prohibited_uses
    assert "live_private_ingestion" in entries["apache_tika"].prohibited_uses
    assert "ground_truth_substitution" in entries["tesseract_ocr"].prohibited_uses
    assert "real_invoice_submission" in entries["ledes_1998b"].prohibited_uses
    assert "automatic_billing_approval" in entries["utbms_litigation_codes"].prohibited_uses
    assert "real_patient_data" in entries["synthea"].prohibited_uses
    assert "clinical_validity_claim" in entries["hl7_fhir_r4"].prohibited_uses


def test_unapproved_runtime_or_authority_self_activation_is_rejected() -> None:
    catalog = build_technology_adoption_catalog()
    simpy = catalog.entries[0]
    temporal = catalog.entries[1]
    attacks = (
        (0, replace(simpy, canonical_truth_write=True)),
        (1, replace(temporal, dependency_installed=True)),
        (1, replace(temporal, runtime_execution=True)),
    )
    for index, attacked in attacks:
        entries = list(catalog.entries)
        entries[index] = attacked
        errors = validate_technology_adoption_catalog(
            replace(catalog, entries=tuple(entries))
        )
        assert "TECH-001:catalog_not_canonical" in errors
        assert any(value.startswith(f"TECH-004:{attacked.technology_id}") for value in errors)

