from __future__ import annotations

import base64
import hashlib
import zlib
import urllib.parse
import gzip
import hmac
import json
from dataclasses import dataclass
from typing import Literal

from .hashio import digest


ORACLE_ISOLATION_REVISION = "oracle-isolation-contract-g0c-v1"
CANARY_SCANNER_REVISION = "oracle-canary-primary-scanner-g0c-v2"

SurfaceState = Literal[
    "not_created",
    "ephemeral_fixture",
    "implemented_noncanonical",
    "canonical_h10_approved",
]
ScanState = Literal["leak_detected", "incomplete_surfaces", "clean_noncanonical"]


@dataclass(frozen=True)
class OperatingSurfaceSpec:
    surface_id: str
    surface_kind: str
    state: SurfaceState
    scans_content: Literal[True]
    scans_names: Literal[True]
    scans_metadata: Literal[True]
    required_before_qualification: Literal[True]
    external_effects: Literal[False] = False
    sealed_access: Literal[False] = False


@dataclass(frozen=True)
class OperatingSurfaceRegistry:
    registry_id: str
    revision: str
    surfaces: tuple[OperatingSurfaceSpec, ...]
    canonical_storage_gate: Literal["H-10"]
    sealed_key_included: Literal[False]
    canary_value_included: Literal[False]
    external_effects: Literal[False]

    @property
    def registry_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class SurfaceObservation:
    surface_id: str
    relative_name: str
    content: bytes
    metadata: tuple[tuple[str, str], ...] = ()

    @property
    def observation_commitment(self) -> str:
        return digest(
            {
                "surface_id": self.surface_id,
                "relative_name_hash": hashlib.sha256(
                    self.relative_name.encode("utf-8")
                ).hexdigest(),
                "content_hash": hashlib.sha256(self.content).hexdigest(),
                "metadata_hash": digest(self.metadata),
            }
        )


@dataclass(frozen=True)
class CanaryHit:
    surface_id: str
    observation_commitment: str
    channel: Literal["name", "content", "metadata"]
    variant_id: str


@dataclass(frozen=True)
class CanaryScanReport:
    report_id: str
    scanner_revision: str
    registry_hash: str
    protected_canary_commitment: str
    state: ScanState
    observed_surface_ids: tuple[str, ...]
    uncreated_surface_ids: tuple[str, ...]
    missing_observation_surface_ids: tuple[str, ...]
    unknown_observation_surface_ids: tuple[str, ...]
    hits: tuple[CanaryHit, ...]
    all_registered_surfaces_scanned: bool
    mutation_adequacy_validated: Literal[False]
    worker_boundary_validated: Literal[False]
    canonical_qualification: Literal[False]
    canary_value_included: Literal[False]
    external_effects: Literal[False]

    @property
    def report_hash(self) -> str:
        return digest(self)


REQUIRED_OPERATING_SURFACES = (
    ("operating_db", "database"),
    ("artifact_staging", "filesystem"),
    ("trace_log_sink", "log"),
    ("local_cache", "cache"),
    ("retrieval_index", "index"),
    ("embedding_index", "index"),
    ("provider_prompt_outbox", "outbox"),
    ("public_export", "export"),
    ("temporary_workspace", "filesystem"),
    ("renderer_workspace", "filesystem"),
)


def build_operating_surface_registry(
    *, state: SurfaceState = "not_created"
) -> OperatingSurfaceRegistry:
    return OperatingSurfaceRegistry(
        registry_id="registry.oracle.operating-surfaces.g0c.v1",
        revision=ORACLE_ISOLATION_REVISION,
        surfaces=tuple(
            OperatingSurfaceSpec(
                surface_id=surface_id,
                surface_kind=surface_kind,
                state=state,
                scans_content=True,
                scans_names=True,
                scans_metadata=True,
                required_before_qualification=True,
            )
            for surface_id, surface_kind in REQUIRED_OPERATING_SURFACES
        ),
        canonical_storage_gate="H-10",
        sealed_key_included=False,
        canary_value_included=False,
        external_effects=False,
    )


def mint_sealed_canary(sealed_key: bytes, run_nonce: str) -> str:
    if len(sealed_key) < 32:
        raise ValueError("sealed_canary_key_too_short")
    if not run_nonce or len(run_nonce) > 200:
        raise ValueError("sealed_canary_nonce_invalid")
    token = hmac.new(
        sealed_key,
        f"lfdt:oracle-canary:v1:{run_nonce}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()
    return f"LFDT-CNY-{token}"


def _canary_variants(canary: str) -> tuple[tuple[str, bytes], ...]:
    raw = canary.encode("utf-8")
    json_escaped = json.dumps(canary, ensure_ascii=True)[1:-1].encode("ascii")
    return (
        ("raw_utf8", raw),
        ("raw_lower_utf8", raw.lower()),
        ("hex_lower", raw.hex().encode("ascii")),
        ("hex_upper", raw.hex().upper().encode("ascii")),
        ("base64_standard", base64.b64encode(raw)),
        ("base64_urlsafe", base64.urlsafe_b64encode(raw)),
        ("json_escaped", json_escaped),
        (
            "percent_utf8",
            urllib.parse.quote_from_bytes(raw, safe="").encode("ascii"),
        ),
        ("utf16_le", raw.decode("ascii").encode("utf-16-le")),
        ("utf16_be", raw.decode("ascii").encode("utf-16-be")),
        ("gzip_mtime0", gzip.compress(raw, mtime=0)),
        ("zlib", zlib.compress(raw)),
    )


def _channel_bytes(observation: SurfaceObservation) -> tuple[tuple[str, bytes], ...]:
    metadata_text = json.dumps(
        dict(observation.metadata), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return (
        ("name", observation.relative_name.encode("utf-8")),
        ("content", observation.content),
        ("metadata", metadata_text),
    )


def scan_canary_containment(
    registry: OperatingSurfaceRegistry,
    observations: tuple[SurfaceObservation, ...],
    *,
    sealed_canary: str,
) -> CanaryScanReport:
    known = {item.surface_id: item for item in registry.surfaces}
    observed_ids = tuple(sorted({item.surface_id for item in observations}))
    unknown_ids = tuple(sorted(set(observed_ids) - set(known)))
    uncreated_ids = tuple(
        sorted(item.surface_id for item in registry.surfaces if item.state == "not_created")
    )
    expected_observed = {
        item.surface_id for item in registry.surfaces if item.state != "not_created"
    }
    missing_ids = tuple(sorted(expected_observed - set(observed_ids)))
    variants = _canary_variants(sealed_canary)
    hits: list[CanaryHit] = []
    for observation in observations:
        if observation.surface_id not in known:
            continue
        for channel, haystack in _channel_bytes(observation):
            for variant_id, needle in variants:
                if needle and needle in haystack:
                    hits.append(
                        CanaryHit(
                            surface_id=observation.surface_id,
                            observation_commitment=observation.observation_commitment,
                            channel=channel,  # type: ignore[arg-type]
                            variant_id=variant_id,
                        )
                    )
    hits_tuple = tuple(
        sorted(
            set(hits),
            key=lambda item: (
                item.surface_id,
                item.observation_commitment,
                item.channel,
                item.variant_id,
            ),
        )
    )
    all_scanned = not uncreated_ids and not missing_ids and not unknown_ids
    if hits_tuple or unknown_ids:
        state: ScanState = "leak_detected"
    elif not all_scanned:
        state = "incomplete_surfaces"
    else:
        state = "clean_noncanonical"
    canary_commitment = hmac.new(
        b"lfdt-protected-evaluation-commitment-v1",
        sealed_canary.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    payload = {
        "scanner": CANARY_SCANNER_REVISION,
        "registry": registry.registry_hash,
        "canary": canary_commitment,
        "state": state,
        "observed": observed_ids,
        "uncreated": uncreated_ids,
        "missing": missing_ids,
        "unknown": unknown_ids,
        "hits": hits_tuple,
    }
    return CanaryScanReport(
        report_id=f"CANARY-SCAN-{digest(payload)[:18]}",
        scanner_revision=CANARY_SCANNER_REVISION,
        registry_hash=registry.registry_hash,
        protected_canary_commitment=canary_commitment,
        state=state,
        observed_surface_ids=observed_ids,
        uncreated_surface_ids=uncreated_ids,
        missing_observation_surface_ids=missing_ids,
        unknown_observation_surface_ids=unknown_ids,
        hits=hits_tuple,
        all_registered_surfaces_scanned=all_scanned,
        mutation_adequacy_validated=False,
        worker_boundary_validated=False,
        canonical_qualification=False,
        canary_value_included=False,
        external_effects=False,
    )

