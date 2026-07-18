from __future__ import annotations

from pathlib import Path

from law_firm_digital_twin.hashio import canonical_json
from scripts.build_g2_channel_fixture import build_payloads


def test_checked_in_persona_channel_fixture_matches_builder() -> None:
    manifest, audit_summary, diversity_summary = build_payloads(
        seed="g2-scale-v1-ten",
        count=10,
    )
    root = (
        Path(__file__).resolve().parents[1]
        / "generated"
        / "g2-channel-v1"
    )
    assert (root / "render-manifest.json").read_text(encoding="utf-8") == (
        canonical_json(manifest) + "\n"
    )
    assert (
        root / "corpus-audit-summary.json"
    ).read_text(encoding="utf-8") == canonical_json(audit_summary) + "\n"
    assert (
        root / "corpus-diversity-summary.json"
    ).read_text(encoding="utf-8") == canonical_json(diversity_summary) + "\n"


def test_public_persona_channel_fixture_excludes_private_and_sealed_fields() -> None:
    root = (
        Path(__file__).resolve().parents[1]
        / "generated"
        / "g2-channel-v1"
    )
    text = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in sorted(root.glob("*.json"))
    )
    for forbidden in (
        "merits_posture",
        "target_posture",
        "claimant_favorable",
        "defense_favorable",
        "world_namespace",
        "matter_namespace",
        "author_id",
        "assertion_id",
        "synthetic_context",
        "training_context",
        "active_goals",
        "sealed_axis_labels",
        "oracle",
        '"body":',
    ):
        assert forbidden not in text
    assert '"bodies_included":false' in text
    assert '"canonical_admission":false' in text

