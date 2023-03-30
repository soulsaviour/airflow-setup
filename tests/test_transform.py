from decimal import Decimal

import pytest

from orders_lib.transform import RegionRevenue, parse_orders, summarise

EXPORT = """order_id,region,amount,status
A-1,North,100.50,completed
A-2,north ,20.00,completed
A-3,South,75.00,completed
A-4,South,999.00,cancelled
A-3,South,75.00,completed
A-5,East,abc,completed
A-6,East,-10.00,completed
A-7,,12.00,completed
"""


def test_summarise_counts_completed_orders_per_region():
    summary, rejected = summarise(parse_orders(EXPORT))

    assert summary == [
        RegionRevenue("north", 2, Decimal("120.50")),
        RegionRevenue("south", 1, Decimal("75.00")),
        RegionRevenue("unknown", 1, Decimal("12.00")),
    ]
    # duplicate A-3, unparseable A-5, negative A-6
    assert rejected == 3


def test_cancelled_orders_are_ignored_not_rejected():
    rows = parse_orders("order_id,region,amount,status\nB-1,west,10,cancelled\n")
    assert summarise(rows) == ([], 0)


def test_missing_columns_are_reported():
    with pytest.raises(ValueError, match="amount"):
        parse_orders("order_id,region,status\nC-1,west,completed\n")
