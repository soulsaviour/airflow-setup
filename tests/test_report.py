from decimal import Decimal

from orders_lib.report import render_report


def test_report_lists_regions_and_totals():
    report = render_report(
        [("north", 120, Decimal("15400.50")), ("south", 80, "9100")], generated_on="2026-10-30"
    )

    assert report.splitlines() == [
        "# Revenue by region, last 7 days (2026-10-30)",
        "",
        "| Region | Orders | Revenue |",
        "|--------|-------:|--------:|",
        "| north | 120 | 15,400.50 |",
        "| south | 80 | 9,100.00 |",
        "| **Total** | **200** | **24,500.50** |",
    ]


def test_empty_report_still_has_a_total():
    assert "| **Total** | **0** | **0.00** |" in render_report([], generated_on="2026-10-30")
