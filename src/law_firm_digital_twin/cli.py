from __future__ import annotations

import argparse
import json

from .hashio import canonicalize
from .simulation import run_all_routes


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Law Firm Digital Twin walking skeleton.")
    parser.add_argument("--seed", default="alpha", help="deterministic synthetic-world seed")
    args = parser.parse_args()
    result = run_all_routes(args.seed)
    print(json.dumps(canonicalize(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

