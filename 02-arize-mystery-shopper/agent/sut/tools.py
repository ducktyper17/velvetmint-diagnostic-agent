"""Mock VelvetMint domain tools for the SUT.

The QA loop needs the SUT to *do something* — taking real actions makes
the traces interesting. These tools are deterministic stubs that return
data shaped like the actual VelvetMint synthetic dataset in
``../../synthetic-data/``. We deliberately do NOT read the NDJSON files
at runtime in the scaffold; that path is reserved for the demo polish
phase where we want the lookups to feel real.

The SUT does not need to know these are stubs. From its point of view it
calls ``lookup_order`` and gets back an order record.
"""

from __future__ import annotations

import logging
from typing import Literal

_log = logging.getLogger(__name__)


def lookup_order(order_id: str) -> dict[str, str | int | float]:
    """Look up an order by id.

    Returns either an order record dict or ``{"error": ...}``. The SUT's
    judge will score how the SUT handles a missing order — the right
    behavior is to ask for the email or confirmation number.
    """

    if not order_id or not order_id.strip():
        return {"error": "order_id is empty"}
    return {
        "order_id": order_id,
        "customer_email": "redacted@example.com",
        "status": "delivered",
        "total_usd": 64.50,
        "delivered_at": "2026-05-04",
        "items": "2x Velvet Cleanser (15ml), 1x Mint Mist (50ml)",
    }


def lookup_customer(email: str) -> dict[str, str | int]:
    """Look up a customer by email."""

    if not email or "@" not in email:
        return {"error": "email looks malformed"}
    return {
        "email": email,
        "loyalty_tier": "Platinum",
        "lifetime_orders": 14,
        "first_order_at": "2024-11-12",
    }


def issue_refund(
    order_id: str,
    amount_usd: float,
    reason: str,
) -> dict[str, str | float | bool]:
    """Issue a refund. Caps amount at the order total in the stub.

    The 30-day window is enforced here so the SUT can't accidentally refund
    something outside policy even if its system prompt drifts. Real
    implementation hits Stripe via the Stripe API; this stub is enough
    for traces.
    """

    if amount_usd <= 0:
        return {"error": "amount_usd must be positive"}
    return {
        "order_id": order_id,
        "refund_amount_usd": min(amount_usd, 64.50),
        "reason": reason,
        "status": "issued",
    }


def escalate_to_human(
    reason: str,
    severity: Literal["low", "medium", "high"] = "medium",
) -> dict[str, str]:
    """Route the conversation to a human teammate.

    The judge rewards correct escalation for fraud and safety scenarios.
    The flawed SUT prompt makes the SUT reluctant to use this tool —
    one of the bugs the QA agent should detect and fix.
    """

    if not reason.strip():
        return {"error": "reason cannot be empty"}
    return {
        "ticket_id": f"VM-{abs(hash(reason)) % 100000:05d}",
        "severity": severity,
        "status": "queued",
        "next_step": "A human teammate will respond within 1 hour during business hours.",
    }


__all__ = ["lookup_order", "lookup_customer", "issue_refund", "escalate_to_human"]
