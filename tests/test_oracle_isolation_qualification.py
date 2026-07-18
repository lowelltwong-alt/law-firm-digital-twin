from __future__ import annotations

import base64

from law_firm_digital_twin.hashio import canonical_json
from law_firm_digital_twin.oracle_isolation import (
    build_operating_surface_registry,
    mint_sealed_canary,
)
from law_firm_digital_twin.oracle_isolation_qualification import (
    qualify_canary_scanner_mutations,
)


def test_mutation_harness_proves_all_surfaces_encodings_and_channels() -> None:
    canary = mint_sealed_canary(
        b"test-only-mutation-key-not-production-0001",
        "mutation-qualification",
    )
    receipt = qualify_canary_scanner_mutations(
        build_operating_surface_registry(), sealed_canary=canary
    )
    assert receipt.surface_count == 10
    assert receipt.encoding_variant_count == 12
    assert receipt.mutation_count == 140
    assert receipt.every_surface_caught
    assert receipt.every_variant_caught
    assert receipt.name_channel_caught
    assert receipt.metadata_channel_caught
    assert receipt.independent_checker_passed
    assert not receipt.worker_boundary_validated
    assert not receipt.system_containment_qualified
    assert not receipt.canonical_admission


def test_mutation_receipt_contains_no_canary_or_common_encoding() -> None:
    canary = mint_sealed_canary(
        b"test-only-mutation-key-not-production-0001",
        "mutation-receipt-redaction",
    )
    receipt = qualify_canary_scanner_mutations(
        build_operating_surface_registry(), sealed_canary=canary
    )
    serialized = canonical_json(receipt)
    raw = canary.encode("utf-8")
    assert canary not in serialized
    assert raw.hex() not in serialized
    assert base64.b64encode(raw).decode("ascii") not in serialized
    assert not receipt.canary_value_included
