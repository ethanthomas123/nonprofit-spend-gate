from decimal import Decimal

from nonprofit_spend import MonthlyWorkload, SpendGate


def test_projected_monthly_total_is_rejected_at_the_ceiling() -> None:
    workload = MonthlyWorkload(Decimal("48.00"), Decimal("3.00"), Decimal("50.00"))

    decision = SpendGate().allow(workload)

    assert decision.allowed is False
    assert decision.projected_total_usd == Decimal("51.00")
    assert decision.remaining_usd == Decimal("2.00")

