from __future__ import annotations

import json
from pathlib import Path

from law_firm_digital_twin.operational_router_process import qualification_summary


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    destination = root / "generated" / "operational-router-process-v1" / "summary.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    summary = qualification_summary(launches=10)
    destination.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
