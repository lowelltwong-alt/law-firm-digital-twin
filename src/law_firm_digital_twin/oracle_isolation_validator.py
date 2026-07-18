from __future__ import annotations

import base64
import binascii
import json
import zlib
import urllib.parse
import gzip

from .hashio import canonical_json
from .oracle_isolation import (
    CANARY_SCANNER_REVISION,
    REQUIRED_OPERATING_SURFACES,
    CanaryScanReport,
    OperatingSurfaceRegistry,
    SurfaceObservation,
)


ORACLE_ISOLATION_CHECKER_REVISION = "oracle-isolation-independent-checker-g0c-v2"


def validate_operating_surface_registry(
    registry: OperatingSurfaceRegistry,
) -> tuple[str, ...]:
    errors: list[str] = []
    expected = {surface_id for surface_id, _ in REQUIRED_OPERATING_SURFACES}
    ids = tuple(item.surface_id for item in registry.surfaces)
    if set(ids) != expected or len(ids) != len(set(ids)):
        errors.append("OIR-001:surface_coverage_invalid")
    if registry.canonical_storage_gate != "H-10":
        errors.append("OIR-002:canonical_storage_gate_invalid")
    if registry.sealed_key_included or registry.canary_value_included or registry.external_effects:
        errors.append("OIR-003:registry_information_boundary_invalid")
    for surface in registry.surfaces:
        if (
            not surface.scans_content
            or not surface.scans_names
            or not surface.scans_metadata
            or not surface.required_before_qualification
            or surface.external_effects
            or surface.sealed_access
        ):
            errors.append(f"OIR-004:{surface.surface_id}:surface_contract_invalid")
        if surface.state == "canonical_h10_approved":
            errors.append(f"OIR-005:{surface.surface_id}:human_gate_self_activation")
    return tuple(errors)


def _checker_variants(canary: str) -> tuple[tuple[str, bytes], ...]:
    raw = canary.encode("utf-8")
    return (
        ("raw_utf8", raw),
        ("raw_lower_utf8", canary.lower().encode("utf-8")),
        ("hex_lower", binascii.hexlify(raw)),
        ("hex_upper", binascii.hexlify(raw).upper()),
        ("base64_standard", base64.standard_b64encode(raw)),
        ("base64_urlsafe", base64.urlsafe_b64encode(raw)),
        ("json_escaped", json.dumps(canary, ensure_ascii=True)[1:-1].encode("ascii")),
        (
            "percent_utf8",
            urllib.parse.quote(canary, safe="").encode("ascii"),
        ),
        ("utf16_le", canary.encode("utf-16-le")),
        ("utf16_be", canary.encode("utf-16-be")),
        ("gzip_mtime0", gzip.compress(raw, mtime=0)),
        ("zlib", zlib.compress(raw)),
    )


def _checker_channels(observation: SurfaceObservation) -> tuple[tuple[str, bytes], ...]:
    return (
        ("name", observation.relative_name.encode("utf-8")),
        ("content", observation.content),
        (
            "metadata",
            json.dumps(
                dict(observation.metadata), sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
        ),
    )


def independently_validate_canary_report(
    registry: OperatingSurfaceRegistry,
    observations: tuple[SurfaceObservation, ...],
    report: CanaryScanReport,
    *,
    sealed_canary: str,
) -> tuple[str, ...]:
    errors = list(validate_operating_surface_registry(registry))
    if report.scanner_revision != CANARY_SCANNER_REVISION:
        errors.append("OIC-001:scanner_revision_invalid")
    if report.registry_hash != registry.registry_hash:
        errors.append("OIC-002:registry_binding_invalid")
    expected_hits: set[tuple[str, str, str, str]] = set()
    known = {item.surface_id for item in registry.surfaces}
    for observation in observations:
        if observation.surface_id not in known:
            continue
        for channel, haystack in _checker_channels(observation):
            for variant_id, needle in _checker_variants(sealed_canary):
                if needle and needle in haystack:
                    expected_hits.add(
                        (
                            observation.surface_id,
                            observation.observation_commitment,
                            channel,
                            variant_id,
                        )
                    )
    actual_hits = {
        (
            item.surface_id,
            item.observation_commitment,
            item.channel,
            item.variant_id,
        )
        for item in report.hits
    }
    if expected_hits != actual_hits:
        errors.append("OIC-003:hit_set_mismatch")
    if report.hits and report.state != "leak_detected":
        errors.append("OIC-004:leak_state_invalid")
    if report.state == "clean_noncanonical" and (
        not report.all_registered_surfaces_scanned
        or report.uncreated_surface_ids
        or report.missing_observation_surface_ids
        or report.unknown_observation_surface_ids
    ):
        errors.append("OIC-005:false_clean_claim")
    if (
        report.mutation_adequacy_validated
        or report.worker_boundary_validated
        or report.canonical_qualification
        or report.canary_value_included
        or report.external_effects
    ):
        errors.append("OIC-006:qualification_or_authority_overclaim")
    serialized = canonical_json(report)
    for _, variant in _checker_variants(sealed_canary):
        text = variant.decode("ascii", errors="ignore")
        if text and text in serialized:
            errors.append("OIC-007:canary_value_leaked_in_report")
            break
    return tuple(errors)

