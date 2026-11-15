"""Stage 1 financing: when the intake chooses financing, show a Capital One Nessie loan for sale listings above budget.

The user's budget is the down payment and the loan covers the rest. Lender terms are assumptions, labelled as such:
at least 25% down, 9% APR, 20 years. A listing that needs more than 75% financing is marked not financeable at these
terms rather than stretched. Nothing here changes a budget classification; the deterministic gates stay as they are.

When the user selects a listing to investigate, the loan is stored on their Nessie sandbox account
(NESSIE_ACCOUNT_ID) as a pending small-business loan and copied into the Stage 2 handoff. Nessie failures never block
the handoff: the plan is kept and the reason is recorded. Uses playground/nessie_loan.py for the math and Nessie calls.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "playground"))
import nessie_loan  # noqa: E402

MIN_DOWN_PAYMENT = 0.25
APR = 9.0
TERM_MONTHS = 240
TERMS_LABEL = (f"Assumed lender terms: at least {MIN_DOWN_PAYMENT:.0%} down, {APR:g}% APR, {TERM_MONTHS // 12} years. "
               "Simulated Nessie sandbox loan, not a credit offer or a Capital One rate.")


def acquisition_budget(record: dict, intake: dict) -> float:
    if record.get("occupancy_budget_usd") is not None:
        return float(record["occupancy_budget_usd"])
    allocation = intake.get("acquisition_allocation")
    total = float(intake["total_budget_usd"])
    return total if allocation is None else total * float(allocation) / 100


def financing_option(record: dict, intake: dict) -> dict | None:
    """Loan option for one listing, or None when financing doesn't apply (cash intake, lease, unknown price, in budget)."""
    price = record.get("asking_price_usd")
    if intake.get("financing") != "financing" or record.get("transaction_type") != "sale" or not price:
        return None
    budget = acquisition_budget(record, intake)
    if price <= budget:
        return None
    down_needed = price * MIN_DOWN_PAYMENT
    if budget < down_needed:
        return {"status": "not_financeable", "asking_price_usd": price, "down_payment_usd": budget,
                "minimum_down_payment_usd": round(down_needed, 2), "label": TERMS_LABEL,
                "reason": f"Needs at least ${down_needed:,.0f} down ({MIN_DOWN_PAYMENT:.0%}) at the assumed terms; "
                          f"budget is ${budget:,.0f}."}
    amount = round(price - budget, 2)  # a purchase borrows the exact gap
    schedule = nessie_loan.schedule(amount, APR, TERM_MONTHS)
    return {"status": "financeable", "asking_price_usd": price, "down_payment_usd": budget,
            "loan_amount_usd": amount, "loan_to_price_percent": round(amount / price * 100, 1),
            "apr": APR, "term_months": TERM_MONTHS,
            "monthly_payment_usd": round(nessie_loan.payment(amount, APR, TERM_MONTHS), 2),
            "first_year_interest_usd": round(sum(r["interest"] for r in schedule), 2),
            "schedule": schedule, "label": TERMS_LABEL}


def attach_financing(response: dict, intake: dict) -> dict:
    """Add financing_option to every result (None when it doesn't apply) and a count to the trace."""
    results = response.get("results") or []
    for record in results:
        record["financing_option"] = financing_option(record, intake)
    financeable = sum(1 for r in results if (r.get("financing_option") or {}).get("status") == "financeable")
    response.setdefault("trace", {})["financeable_sale_listings"] = financeable
    return response


def handoff_financing(record: dict, intake: dict, account_id: str | None = None, create=nessie_loan.create) -> dict | None:
    """Financing block for the Stage 2 handoff; stores the loan in Nessie when an account is configured."""
    option = record.get("financing_option") or financing_option(record, intake)
    if not option:
        return None
    out = {"option": option, "nessie_loan": None}
    if option["status"] != "financeable":
        out["nessie_status"] = "not created: not financeable at the assumed terms"
        return out
    account_id = account_id or os.environ.get("NESSIE_ACCOUNT_ID")
    if not account_id:
        out["nessie_status"] = "not created: NESSIE_ACCOUNT_ID is not set"
        return out
    try:
        out["nessie_loan"] = create(account_id, option["loan_amount_usd"], APR, TERM_MONTHS)
        out["nessie_status"] = "created (pending)"
    except Exception as error:  # noqa: BLE001 - Nessie must never block the handoff
        out["nessie_status"] = f"not created: {type(error).__name__}"
    return out
