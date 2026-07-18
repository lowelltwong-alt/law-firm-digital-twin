from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_receipt_registries_begin_empty_and_fail_closed() -> None:
    source = _load("registry/source-admission-receipts.json")
    reuse = _load("registry/reuse-release-receipts.json")
    assert source["receipts"] == []
    assert reuse["receipts"] == []
    assert "no external source is admitted" in str(source["authority_boundary"])
    assert "no cross-repository asset is released" in str(reuse["authority_boundary"])


def test_receipt_schemas_require_human_and_provenance_fields() -> None:
    source_schema = _load("schemas/source-admission-receipt.schema.json")
    reuse_schema = _load("schemas/reuse-release-receipt.schema.json")
    assert {"source_hash", "license_posture", "review_status"} <= set(
        source_schema["required"]  # type: ignore[arg-type]
    )
    assert {"source_commit", "source_paths", "approved_by"} <= set(
        reuse_schema["required"]  # type: ignore[arg-type]
    )
    assert (
        reuse_schema["properties"]["approved_by"]["const"] == "Lowell"  # type: ignore[index]
    )
