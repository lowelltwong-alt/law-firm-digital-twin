from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.design_c_registry import (  # noqa: E402
    build_design_c_unified_registry,
)
from law_firm_digital_twin.design_c_validator import (  # noqa: E402
    validate_design_c_registry,
)
from law_firm_digital_twin.oracle_isolation import (  # noqa: E402
    build_operating_surface_registry,
    mint_sealed_canary,
    scan_canary_containment,
)
from law_firm_digital_twin.oracle_isolation_qualification import (  # noqa: E402
    qualify_canary_scanner_mutations,
)
from law_firm_digital_twin.oracle_isolation_validator import (  # noqa: E402
    validate_operating_surface_registry,
)


OUTPUT = ROOT / "generated" / "design-c-g0c-readiness-v1"


def build_summary() -> dict[str, object]:
    registry = build_design_c_unified_registry()
    registry_errors = validate_design_c_registry(registry)
    if registry_errors:
        raise ValueError(f"design_c_registry_invalid:{registry_errors}")
    surfaces = build_operating_surface_registry()
    surface_errors = validate_operating_surface_registry(surfaces)
    if surface_errors:
        raise ValueError(f"operating_surface_registry_invalid:{surface_errors}")
    sealed_canary = mint_sealed_canary(
        b"public-fixture-test-key-never-production-0001",
        "public-mutation-summary",
    )
    incomplete = scan_canary_containment(
        surfaces, (), sealed_canary=sealed_canary
    )
    mutation = qualify_canary_scanner_mutations(
        surfaces, sealed_canary=sealed_canary
    )
    return {
        "schema": "design_c_g0c_public_readiness_v1",
        "baseline_state": "adopted_frozen_design_c_v1",
        "decision_status_counts": dict(
            sorted(Counter(item.status for item in registry.decisions).items())
        ),
        "asset_status_counts": dict(
            sorted(Counter(item.status for item in registry.assets).items())
        ),
        "obligation_status_counts": dict(
            sorted(Counter(item.status for item in registry.obligations).items())
        ),
        "g0c_loop_count": len(registry.loops),
        "optional_runtime_qualification_count": len(
            registry.runtime_qualifications
        ),
        "operating_surface_count": len(surfaces.surfaces),
        "operating_surface_state_counts": dict(
            sorted(Counter(item.state for item in surfaces.surfaces).items())
        ),
        "current_system_containment_state": incomplete.state,
        "scanner_mutation_evidence": {
            "surface_count": mutation.surface_count,
            "encoding_variant_count": mutation.encoding_variant_count,
            "mutation_count": mutation.mutation_count,
            "independent_checker_passed": mutation.independent_checker_passed,
        },
        "qualification_boundaries": {
            "worker_boundary_validated": False,
            "system_containment_qualified": False,
            "canonical_runtime_root_selected": True,
            "backup_location_selected": False,
            "canonical_storage_authorized": False,
            "unattended_execution_authorized": False,
            "external_effects": False,
        },
        "contains_case_identifiers": False,
        "contains_canary_or_key": False,
        "contains_source_rows": False,
        "nonjoinable": True,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = build_summary()
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUTPUT / "README.md").write_text(
        "# Design C G0C Readiness Fixture\n\n"
        "Aggregate, nonjoinable readiness evidence only. The canary scanner's "
        "negative controls pass, but system containment remains incomplete until "
        "all operating surfaces and the worker boundary exist and the separate backup qualification completes.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
