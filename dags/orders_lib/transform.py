"""Turns an orders export into revenue per region.

Plain Python with no Airflow imports, so it can be tested in isolation and
the DAG file stays thin.
"""

import csv
import io
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = {"order_id", "region", "amount", "status"}


@dataclass(frozen=True)
class RegionRevenue:
    region: str
    orders: int
    revenue: Decimal


def parse_orders(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"orders export is missing columns: {sorted(missing)}")
    return list(reader)


def summarise(rows: Iterable[dict[str, str]]) -> tuple[list[RegionRevenue], int]:
    """Revenue per region from completed orders.

    Duplicate order IDs, unparseable amounts and negative amounts are
    rejected rather than silently counted. Returns (summary, rejected count).
    """
    totals: dict[str, list] = defaultdict(lambda: [0, Decimal("0")])
    seen: set[str] = set()
    rejected = 0
    for row in rows:
        if row["status"].strip().lower() != "completed":
            continue
        try:
            amount = Decimal(row["amount"])
        except InvalidOperation:
            rejected += 1
            continue
        if amount < 0 or row["order_id"] in seen:
            rejected += 1
            continue
        seen.add(row["order_id"])
        region = row["region"].strip().lower() or "unknown"
        totals[region][0] += 1
        totals[region][1] += amount

    summary = [
        RegionRevenue(region, count, total) for region, (count, total) in sorted(totals.items())
    ]
    return summary, rejected
