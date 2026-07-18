from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .hashio import digest
from .oracle_isolation import (
    CANARY_SCANNER_REVISION,
    OperatingSurfaceRegistry,
    SurfaceObservation,
    scan_canary_containment,
)
from .oracle_isolation_validator import (
    ORACLE_ISOLATION_CHECKER_REVISION,
    _checker_variants,
    independently_validate_canary_report,
    validate_operating_surface_registry,
)


CANARY_MUTATION_HARNESS_REVISION = "oracle-canary-mutation-harness-g0c-v1"


@dataclass(frozen=True)
class CanaryScannerMutationReceipt:
    receipt_id: str
    scanner_revision: str
    checker_revision: str
    harness_revision: str
    qualification_registry_hash: str
    surface_count: int
    encoding_variant_count: int
    mutation_count: int
    every_surface_caught: Literal[True]
    every_variant_caught: Literal[True]
    name_channel_caught: Literal[True]
    metadata_channel_caught: Literal[True]
    independent_checker_passed: Literal[True]
    worker_boundary_validated: Literal[False]
    system_containment_qualified: Literal[False]
    canonical_admission: Literal[False]
    canary_value_included: Literal[False]
    external_effects: Literal[False]

    @property
    def receipt_hash(self) -> str:
        return digest(self)


def qualify_canary_scanner_mutations(
    registry: OperatingSurfaceRegistry,
    *,
    sealed_canary: str,
) -> CanaryScannerMutationReceipt:
    registry_errors = validate_operating_surface_registry(registry)
    if registry_errors:
        raise ValueError(f"oracle_surface_registry_invalid:{registry_errors}")
    qualification_registry = replace(
        registry,
        surfaces=tuple(
            replace(item, state="ephemeral_fixture") for item in registry.surfaces
        ),
    )
    safe = tuple(
        SurfaceObservation(
            surface_id=item.surface_id,
            relative_name=f"safe/{item.surface_id}/fixture.dat",
            content=b"ordinary mutation-harness control",
            metadata=(("classification", "test_only"),),
        )
        for item in qualification_registry.surfaces
    )
    variants = _checker_variants(sealed_canary)
    caught_surfaces: set[str] = set()
    caught_variants: set[str] = set()
    mutation_count = 0
    for surface_index, surface in enumerate(qualification_registry.surfaces):
        for variant_id, encoded in variants:
            observations = list(safe)
            observations[surface_index] = replace(
                observations[surface_index], content=encoded
            )
            report = scan_canary_containment(
                qualification_registry,
                tuple(observations),
                sealed_canary=sealed_canary,
            )
            checker_errors = independently_validate_canary_report(
                qualification_registry,
                tuple(observations),
                report,
                sealed_canary=sealed_canary,
            )
            if checker_errors:
                raise ValueError(f"oracle_mutation_checker_failed:{checker_errors}")
            if not any(
                hit.surface_id == surface.surface_id
                and hit.variant_id == variant_id
                and hit.channel == "content"
                for hit in report.hits
            ):
                raise ValueError(
                    f"oracle_mutation_not_detected:{surface.surface_id}:{variant_id}"
                )
            caught_surfaces.add(surface.surface_id)
            caught_variants.add(variant_id)
            mutation_count += 1

        for channel in ("name", "metadata"):
            observations = list(safe)
            if channel == "name":
                observations[surface_index] = replace(
                    observations[surface_index],
                    relative_name=f"unsafe/{sealed_canary}.dat",
                )
            else:
                observations[surface_index] = replace(
                    observations[surface_index],
                    metadata=(("unsafe", sealed_canary),),
                )
            report = scan_canary_containment(
                qualification_registry,
                tuple(observations),
                sealed_canary=sealed_canary,
            )
            if not any(
                hit.surface_id == surface.surface_id and hit.channel == channel
                for hit in report.hits
            ):
                raise ValueError(
                    f"oracle_channel_mutation_not_detected:{surface.surface_id}:{channel}"
                )
            mutation_count += 1

    surface_ids = {item.surface_id for item in qualification_registry.surfaces}
    variant_ids = {item[0] for item in variants}
    if caught_surfaces != surface_ids or caught_variants != variant_ids:
        raise ValueError("oracle_mutation_coverage_incomplete")
    payload = {
        "scanner": CANARY_SCANNER_REVISION,
        "checker": ORACLE_ISOLATION_CHECKER_REVISION,
        "harness": CANARY_MUTATION_HARNESS_REVISION,
        "registry": qualification_registry.registry_hash,
        "surfaces": len(surface_ids),
        "variants": len(variant_ids),
        "mutations": mutation_count,
    }
    return CanaryScannerMutationReceipt(
        receipt_id=f"CANARY-MUTATION-{digest(payload)[:18]}",
        scanner_revision=CANARY_SCANNER_REVISION,
        checker_revision=ORACLE_ISOLATION_CHECKER_REVISION,
        harness_revision=CANARY_MUTATION_HARNESS_REVISION,
        qualification_registry_hash=qualification_registry.registry_hash,
        surface_count=len(surface_ids),
        encoding_variant_count=len(variant_ids),
        mutation_count=mutation_count,
        every_surface_caught=True,
        every_variant_caught=True,
        name_channel_caught=True,
        metadata_channel_caught=True,
        independent_checker_passed=True,
        worker_boundary_validated=False,
        system_containment_qualified=False,
        canonical_admission=False,
        canary_value_included=False,
        external_effects=False,
    )

