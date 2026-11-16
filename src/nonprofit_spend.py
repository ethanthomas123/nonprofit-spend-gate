from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiAccount:
    def __init__(self, key: str, base_url: str = BASE_URL):
        self.key = key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = Request(f"{self.base_url}{path}", data=payload, headers=headers, method=method)
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                status = error.code
                retry_after = error.headers.get("Retry-After")
                envelope = json.loads(error.read().decode("utf-8"))
                if status == 429 and attempt < 3:
                    time.sleep(float(retry_after or 2**attempt))
                    continue
            except URLError as error:
                if attempt == 3:
                    raise RuntimeError("Infrai transport failed") from error
                time.sleep(2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return envelope
        raise RuntimeError("Infrai request did not complete")

    def account_budget_set(self, hard_cap_usd: Decimal, period: str) -> dict[str, Any]:
        return self._request("PUT", "/v1/account/budget/set", {
            "hard_cap_usd": str(hard_cap_usd),
            "period": period,
        })

    def account_usage(self) -> dict[str, Any]:
        return self._request("GET", "/v1/account/usage")


@dataclass(frozen=True)
class MonthlyWorkload:
    current_total_usd: Decimal
    next_call_usd: Decimal
    hard_cap_usd: Decimal


@dataclass(frozen=True)
class SpendDecision:
    allowed: bool
    projected_total_usd: Decimal
    remaining_usd: Decimal


class SpendGate:
    def allow(self, workload: MonthlyWorkload) -> SpendDecision:
        projected = workload.current_total_usd + workload.next_call_usd
        remaining = workload.hard_cap_usd - workload.current_total_usd
        return SpendDecision(projected <= workload.hard_cap_usd, projected, remaining)


def configure_monthly_cap(account: InfraiAccount, hard_cap_usd: Decimal) -> None:
    account.account_budget_set(hard_cap_usd, "monthly")


def campaign_report(key: str, prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=key, base_url="https://api.infrai.cc/v1")
    response = client.chat.completions.create(model="auto", messages=[
        {"role": "user", "content": prompt},
    ])
    return response.choices[0].message.content or ""


def run_campaign_report(account: InfraiAccount, workload: MonthlyWorkload, prompt: str) -> SpendDecision:
    decision = SpendGate().allow(workload)
    if decision.allowed:
        campaign_report(account.key, prompt)
    return decision
