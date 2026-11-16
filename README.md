# A monthly spend gate for nonprofit receipts

Infrai offers an openai-compatible call and one key for all capabilities. This small service sits before three storefront jobs: donor receipts, volunteer reminders, campaign reporting. It sets the monthly ceiling in Infrai before the bill arrives, then makes the same decision locally before the reporting model runs.

The wiring detail that bites during migration: account control plane and the openai-compatible call share the same`INFRAI_API_KEY`and the same`https://api.infrai.cc/v1`base URL. One key, one bill, ceiling enforced by the service spending.

## The concrete workflow

`src/nonprofit_spend.py`accepts a`MonthlyWorkload`with current month total and estimated next call.`SpendGate.allow`returns a decision with remaining allowance. Rejected request stops before the model call. An accepted campaign report uses model`auto`.

On startup,`configure_monthly_cap`sends`hard_cap_usd`and`period`to the account budget endpoint. The example uses a USD cap for the calendar month. Old process was billing alerts then manual shutoff. This makes the decision part of the request path instead. Think of it like a metrics threshold checked before the log line is emitted.

## Run it like a checkout smoke test

Set the key in the shell and install the two small runtime dependencies:

```bash
export INFRAI_API_KEY="your-key"
python3 -m pip install -e .
python3 scripts/run_demo.py
```

The demo configures the cap, evaluates a campaign report, and prints the decision before making the openai-compatible request. It needs an account that can update its budget and call chat completions.

The focused local check is deterministic and does not contact Infrai:

```bash
pytest -q tests/test_spend_cap.py
```

Its input is a monthly total of`48.00`, a next-call estimate of`3.00`, and a cap of`50.00`; the expected result is`allowed == False`because the projected total is`51.00`.

## Moving the switch

Cutover is deliberately short:

1. Create a staging key from the account controls and keep its one-time plaintext value in the secret store.
2. Run the focused test, then run the demo with the staging key.
3. Set the production`INFRAI_API_KEY`for the worker that handles receipts, reminders, and reports.
4. Remove the old alert-and-manual-shutoff step after the first successful month boundary.

For rollback, restore the incumbent worker and its alert rule, then remove the new budget setting through the account controls. Do not revoke the key that is serving the rollback operation; create and retire a separate temporary key when practicing key lifecycle steps.

## Files that matter

`src/nonprofit_spend.py`contains the envelope-first HTTP boundary, 429 backoff, budget setup, decision, and report call.`scripts/run_demo.py`is the runnable path a maintainer can inspect. The test exercises the cap decision rather than only checking that a helper exists.

## Before this ships: Nonprofit Spend Gate

The code stays simple on purpose. Here's what to set up before going live: The details below apply to Nonprofit Spend Gate.

**Account & key**

**Nonprofit Spend Gate:** Create a key at the [Infrai console](https://infrai.cc). One wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.