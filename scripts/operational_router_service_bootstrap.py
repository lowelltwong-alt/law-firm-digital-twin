from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from law_firm_digital_twin.operational_router_protocol import MAX_REQUEST_BYTES  # noqa: E402
from law_firm_digital_twin.operational_router_worker import handle_request, response_bytes  # noqa: E402


def main() -> int:
    response = handle_request(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
    sys.stdout.buffer.write(response_bytes(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
