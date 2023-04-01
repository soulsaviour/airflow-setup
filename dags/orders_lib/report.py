"""Formats revenue rows as a Markdown report."""

from collections.abc import Iterable
from decimal import Decimal


def render_report(rows: Iterable[tuple[str, int, Decimal | str]], generated_on: str) -> str:
    """rows: (region, orders, revenue), already sorted the way they should appear."""
    lines = [
        f"# Revenue by region, last 7 days ({generated_on})",
        "",
        "| Region | Orders | Revenue |",
        "|--------|-------:|--------:|",
    ]
    total_orders, total_revenue = 0, Decimal("0")
    for region, orders, revenue in rows:
        revenue = Decimal(revenue)
        total_orders += orders
        total_revenue += revenue
        lines.append(f"| {region} | {orders} | {revenue:,.2f} |")
    lines.append(f"| **Total** | **{total_orders}** | **{total_revenue:,.2f}** |")
    return "\n".join(lines) + "\n"
