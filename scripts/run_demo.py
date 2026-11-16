from decimal import Decimal
import os

from nonprofit_spend import MonthlyWorkload, InfraiAccount, configure_monthly_cap, run_campaign_report


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    account = InfraiAccount(key)
    cap = Decimal("50.00")
    configure_monthly_cap(account, cap)
    workload = MonthlyWorkload(Decimal("12.00"), Decimal("3.00"), cap)
    decision = run_campaign_report(account, workload, "Summarize this month's donor campaign results.")
    print(f"campaign report allowed: {decision.allowed}; remaining: {decision.remaining_usd}")


if __name__ == "__main__":
    main()

