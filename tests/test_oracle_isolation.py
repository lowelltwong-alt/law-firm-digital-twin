from __future__ import annotations

import base64
import json
import zlib
import urllib.parse
import gzip
from dataclasses import replace

import pytest

from law_firm_digital_twin.hashio import canonical_json
from law_firm_digital_twin.oracle_isolation import (
    REQUIRED_OPERATING_SURFACES,
    SurfaceObservation,
    build_operating_surface_registry,
    mint_sealed_canary,
    scan_canary_containment,
)
from law_firm_digital_twin.oracle_isolation_validator import (
    independently_validate_canary_report,
    validate_operating_surface_registry,
)


SEALED_TEST_KEY = b"test-only-sealed-key-not-for-production-0001"


def _canary() -> str:
    return mint_sealed_canary(SEALED_TEST_KEY, "oracle-isolation-fixture")


def _safe_observations() -> tuple[SurfaceObservation, ...]:
    return tuple(
        SurfaceObservation(
            surface_id=surface_id,
            relative_name=f"safe/{surface_id}/record.dat",
            content=f"ordinary synthetic fixture for {surface_id}".encode("utf-8"),
            metadata=(("classification", "synthetic_noncanonical"),),
        )
        for surface_id, _ in REQUIRED_OPERATING_SURFACES
    )


def test_surface_registry_is_complete_noncanonical_and_fail_closed() -> None:
    registry = build_operating_surface_registry()
    assert validate_operating_surface_registry(registry) == ()
    assert {item.surface_id for item in registry.surfaces} == {
        surface_id for surface_id, _ in REQUIRED_OPERATING_SURFACES
    }
    assert all(item.state == "not_created" for item in registry.surfaces)
    assert all(not item.sealed_access for item in registry.surfaces)
    assert not registry.sealed_key_included
    assert not registry.canary_value_included


def test_uncreated_surfaces_can_never_produce_a_clean_claim() -> None:
    registry = build_operating_surface_registry()
    report = scan_canary_containment(registry, (), sealed_canary=_canary())
    assert report.state == "incomplete_surfaces"
    assert len(report.uncreated_surface_ids) == len(REQUIRED_OPERATING_SURFACES)
    assert not report.all_registered_surfaces_scanned
    assert not report.canonical_qualification
    assert independently_validate_canary_report(
        registry, (), report, sealed_canary=_canary()
    ) == ()


def test_implemented_surface_without_observation_is_incomplete() -> None:
    registry = build_operating_surface_registry(state="implemented_noncanonical")
    report = scan_canary_containment(registry, (), sealed_canary=_canary())
    assert report.state == "incomplete_surfaces"
    assert set(report.missing_observation_surface_ids) == {
        surface_id for surface_id, _ in REQUIRED_OPERATING_SURFACES
    }


def test_safe_complete_scan_is_only_clean_noncanonical() -> None:
    registry = build_operating_surface_registry(state="implemented_noncanonical")
    observations = _safe_observations()
    report = scan_canary_containment(
        registry, observations, sealed_canary=_canary()
    )
    assert report.state == "clean_noncanonical"
    assert report.all_registered_surfaces_scanned
    assert not report.hits
    assert not report.mutation_adequacy_validated
    assert not report.worker_boundary_validated
    assert not report.canonical_qualification
    assert independently_validate_canary_report(
        registry, observations, report, sealed_canary=_canary()
    ) == ()


@pytest.mark.parametrize("surface_id", [item[0] for item in REQUIRED_OPERATING_SURFACES])
def test_raw_canary_plant_is_detected_on_every_surface(surface_id: str) -> None:
    registry = build_operating_surface_registry(state="implemented_noncanonical")
    observations = list(_safe_observations())
    index = next(
        index for index, item in enumerate(observations) if item.surface_id == surface_id
    )
    observations[index] = replace(
        observations[index], content=f"prefix::{_canary()}::suffix".encode("utf-8")
    )
    report = scan_canary_containment(
        registry, tuple(observations), sealed_canary=_canary()
    )
    assert report.state == "leak_detected"
    assert any(item.surface_id == surface_id for item in report.hits)
    assert independently_validate_canary_report(
        registry, tuple(observations), report, sealed_canary=_canary()
    ) == ()


@pytest.mark.parametrize(
    "variant_id,encoded",
    (
        ("raw_utf8", lambda value: value.encode("utf-8")),
        ("hex_lower", lambda value: value.encode("utf-8").hex().encode("ascii")),
        ("hex_upper", lambda value: value.encode("utf-8").hex().upper().encode("ascii")),
        ("base64_standard", lambda value: base64.b64encode(value.encode("utf-8"))),
        ("base64_urlsafe", lambda value: base64.urlsafe_b64encode(value.encode("utf-8"))),
        (
            "json_escaped",
            lambda value: json.dumps(value, ensure_ascii=True)[1:-1].encode("ascii"),
        ),
    ),
)
def test_common_canary_encoding_is_detected(
    variant_id: str, encoded: object
) -> None:
    registry = build_operating_surface_registry(state="implemented_noncanonical")
    observations = list(_safe_observations())
    observations[0] = replace(observations[0], content=encoded(_canary()))
    report = scan_canary_containment(
        registry, tuple(observations), sealed_canary=_canary()
    )
    assert report.state == "leak_detected"
    assert any(item.variant_id == variant_id for item in report.hits)
    assert independently_validate_canary_report(
        registry, tuple(observations), report, sealed_canary=_canary()
    ) == ()


@pytest.mark.parametrize(
    "variant_id,encoded",
    (
        ("raw_lower_utf8", lambda value: value.lower().encode("utf-8")),
        (
            "percent_utf8",
            lambda value: urllib.parse.quote(value, safe="").encode("ascii"),
        ),
        ("utf16_le", lambda value: value.encode("utf-16-le")),
        ("utf16_be", lambda value: value.encode("utf-16-be")),
        (
            "gzip_mtime0",
            lambda value: gzip.compress(value.encode("utf-8"), mtime=0),
        ),
        ("zlib", lambda value: zlib.compress(value.encode("utf-8"))),
    ),
)
def test_extended_canary_encoding_is_detected(
    variant_id: str, encoded: object
) -> None:
    registry = build_operating_surface_registry(
        state="implemented_noncanonical"
    )
    observations = list(_safe_observations())
    observations[0] = replace(observations[0], content=encoded(_canary()))
    report = scan_canary_containment(
        registry, tuple(observations), sealed_canary=_canary()
    )
    assert report.state == "leak_detected"
    assert any(item.variant_id == variant_id for item in report.hits)
    assert independently_validate_canary_report(
        registry, tuple(observations), report, sealed_canary=_canary()
    ) == ()

def test_canary_is_detected_in_name_and_metadata() -> None:
    registry = build_operating_surface_registry(state="implemented_noncanonical")
    observations = list(_safe_observations())
    observations[0] = replace(
        observations[0], relative_name=f"unsafe/{_canary()}.dat"
    )
    observations[1] = replace(
        observations[1], metadata=(("unsafe", _canary()),)
    )
    report = scan_canary_containment(
        registry, tuple(observations), sealed_canary=_canary()
    )
    assert {item.channel for item in report.hits} >= {"name", "metadata"}
    assert independently_validate_canary_report(
        registry, tuple(observations), report, sealed_canary=_canary()
    ) == ()


def test_unknown_surface_is_a_terminal_leak_state() -> None:
    registry = build_operating_surface_registry(state="implemented_noncanonical")
    observations = _safe_observations() + (
        SurfaceObservation("unregistered_sink", "x", b"ordinary"),
    )
    report = scan_canary_containment(
        registry, observations, sealed_canary=_canary()
    )
    assert report.state == "leak_detected"
    assert report.unknown_observation_surface_ids == ("unregistered_sink",)


def test_report_never_contains_raw_or_common_encoded_canary() -> None:
    registry = build_operating_surface_registry(state="implemented_noncanonical")
    observations = list(_safe_observations())
    observations[0] = replace(observations[0], content=_canary().encode("utf-8"))
    report = scan_canary_containment(
        registry, tuple(observations), sealed_canary=_canary()
    )
    serialized = canonical_json(report)
    raw = _canary().encode("utf-8")
    forbidden = (
        _canary(),
        raw.hex(),
        raw.hex().upper(),
        base64.b64encode(raw).decode("ascii"),
        base64.urlsafe_b64encode(raw).decode("ascii"),
    )
    assert all(value not in serialized for value in forbidden)
    assert not report.canary_value_included


def test_independent_checker_detects_removed_hit_and_false_clean_claim() -> None:
    registry = build_operating_surface_registry(state="implemented_noncanonical")
    observations = list(_safe_observations())
    observations[0] = replace(observations[0], content=_canary().encode("utf-8"))
    report = scan_canary_containment(
        registry, tuple(observations), sealed_canary=_canary()
    )
    attacked = replace(
        report,
        state="clean_noncanonical",
        hits=(),
        all_registered_surfaces_scanned=False,
    )
    errors = independently_validate_canary_report(
        registry, tuple(observations), attacked, sealed_canary=_canary()
    )
    assert "OIC-003:hit_set_mismatch" in errors
    assert "OIC-005:false_clean_claim" in errors


def test_registry_cannot_claim_h10_canonical_state() -> None:
    registry = build_operating_surface_registry(state="canonical_h10_approved")
    errors = validate_operating_surface_registry(registry)
    assert len([value for value in errors if value.endswith("human_gate_self_activation")]) == len(
        REQUIRED_OPERATING_SURFACES
    )


def test_canary_mint_is_domain_separated_and_rejects_weak_inputs() -> None:
    first = mint_sealed_canary(SEALED_TEST_KEY, "run-a")
    assert first == mint_sealed_canary(SEALED_TEST_KEY, "run-a")
    assert first != mint_sealed_canary(SEALED_TEST_KEY, "run-b")
    assert first.startswith("LFDT-CNY-")
    with pytest.raises(ValueError, match="key_too_short"):
        mint_sealed_canary(b"weak", "run-a")
    with pytest.raises(ValueError, match="nonce_invalid"):
        mint_sealed_canary(SEALED_TEST_KEY, "")
