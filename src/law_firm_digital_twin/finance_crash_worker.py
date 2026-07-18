from __future__ import annotations

import argparse
import os
from pathlib import Path

from .finance_journal import (
    FINANCE_FAULT_POINTS,
    SQLiteFinanceJournal,
    build_finance_lifecycle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--fault-point", required=True, choices=FINANCE_FAULT_POINTS)
    args = parser.parse_args()
    journal = SQLiteFinanceJournal(args.database)

    def fault_hook(point: str) -> None:
        if point == args.fault_point:
            os._exit(78)

    journal.post(build_finance_lifecycle()[0], fault_hook=fault_hook)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
