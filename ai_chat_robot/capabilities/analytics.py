"""Analytics capability boundary.

The sandbox implementation remains the execution adapter for now. Keeping the
public functions here gives Agent composition a single capability namespace and
allows the execution backend to move independently later.
"""

from sandbox.analytics_tools import (
    run_order_analysis,
    run_pricing_simulation,
    run_sales_report,
)

__all__ = ["run_order_analysis", "run_pricing_simulation", "run_sales_report"]
