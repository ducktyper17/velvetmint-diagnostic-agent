"""Generate synthetic data for the VelvetMint demo across all 6 SaaS sources.

The data deliberately encodes the three "ground truth" findings the agent must
surface. See STORY.md for the narrative. Run with:

    python generate.py --seed 42

Outputs NDJSON files into the per-source subdirectories. Deterministic given
the same seed.
"""

from __future__ import annotations

import argparse
import json
import random
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).parent

# The demo "today". Hard-coded so the data is reproducible across runs even if
# the human regenerates it months later. The agent's reasoning will be anchored
# to this date.
DEMO_TODAY = date(2026, 5, 23)
START_DATE = DEMO_TODAY - timedelta(days=90)

# The two inflection points encoded in the data.
TIKTOK_CREATIVE_STALE_SINCE = date(2026, 4, 7)
SHOPIFY_THEME_DEPLOY = date(2026, 5, 3)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def daterange(start: date, end: date) -> Iterable[date]:
    """Yields each date in [start, end)."""
    days = (end - start).days
    for i in range(days):
        yield start + timedelta(days=i)


def write_ndjson(path: Path, records: Iterable[dict]) -> int:
    """Writes records to NDJSON. Returns the count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")
            count += 1
    return count


def gauss_int(mu: float, sigma: float, lo: int = 0) -> int:
    return max(lo, int(random.gauss(mu, sigma)))


# -----------------------------------------------------------------------------
# Shopify
# -----------------------------------------------------------------------------

# Pre-bug iOS Safari checkout rate vs post-bug
IOS_SAFARI_CHECKOUT_PRE = 0.78
IOS_SAFARI_CHECKOUT_POST = 0.41

# Browser share of mobile sessions
BROWSER_SHARE = {
    "ios_safari": 0.32,
    "android_chrome": 0.28,
    "chrome_mobile": 0.18,
    "chrome_desktop": 0.16,
    "safari_desktop": 0.04,
    "edge_desktop": 0.02,
}

OTHER_BROWSER_CHECKOUT = {
    "android_chrome": (0.71, 0.70),
    "chrome_mobile": (0.75, 0.73),
    "chrome_desktop": (0.81, 0.80),
    "safari_desktop": (0.79, 0.79),
    "edge_desktop": (0.77, 0.77),
}


def base_traffic_for(d: date) -> int:
    """Daily session volume. Weekly seasonality + slow growth + May dip."""
    weekday_boost = 1.15 if d.weekday() < 5 else 0.85
    # Monthly trend: roughly flat, slight May drop from lower paid attribution
    if d.month == 5 and d.year == 2026:
        monthly = 0.85
    elif d.month == 4 and d.year == 2026:
        monthly = 1.0
    else:
        monthly = 0.95
    return gauss_int(3200 * weekday_boost * monthly, 250)


def shopify_data():
    """Generates Shopify orders, checkouts, and session-level browser data."""
    orders = []
    checkouts = []
    customers = []
    customer_ids: list[str] = []

    for d in daterange(START_DATE, DEMO_TODAY + timedelta(days=1)):
        sessions = base_traffic_for(d)

        for browser, share in BROWSER_SHARE.items():
            browser_sessions = int(sessions * share)
            for _ in range(browser_sessions):
                # Funnel: session -> add to cart (15%) -> checkout started -> completed
                if random.random() > 0.15:
                    continue
                cart_id = uuid.uuid4().hex[:12]

                # Checkout-completion rate depends on browser and date
                if browser == "ios_safari":
                    completion_rate = (
                        IOS_SAFARI_CHECKOUT_POST
                        if d >= SHOPIFY_THEME_DEPLOY
                        else IOS_SAFARI_CHECKOUT_PRE
                    )
                else:
                    pre, post = OTHER_BROWSER_CHECKOUT[browser]
                    completion_rate = post if d >= SHOPIFY_THEME_DEPLOY else pre

                checkout_started = random.random() < 0.92  # add-to-cart -> checkout
                checkout_completed = checkout_started and random.random() < completion_rate

                checkouts.append({
                    "id": cart_id,
                    "created_at": (datetime.combine(d, datetime.min.time())
                                   + timedelta(seconds=random.randint(0, 86400))).isoformat(),
                    "browser": browser,
                    "checkout_started": checkout_started,
                    "checkout_completed": checkout_completed,
                    "abandoned": checkout_started and not checkout_completed,
                })

                if checkout_completed:
                    aov = max(20, random.gauss(54, 18))
                    is_returning = random.random() < 0.32 and customer_ids
                    if is_returning:
                        customer_id = random.choice(customer_ids)
                    else:
                        customer_id = "cust_" + uuid.uuid4().hex[:10]
                        customer_ids.append(customer_id)
                        customers.append({
                            "id": customer_id,
                            "created_at": (datetime.combine(d, datetime.min.time())).isoformat(),
                            "accepts_marketing": random.random() < 0.65,
                        })

                    orders.append({
                        "id": "ord_" + uuid.uuid4().hex[:10],
                        "created_at": (datetime.combine(d, datetime.min.time())
                                       + timedelta(seconds=random.randint(0, 86400))).isoformat(),
                        "customer_id": customer_id,
                        "total_price": round(aov, 2),
                        "currency": "USD",
                        "browser": browser,
                        "checkout_id": cart_id,
                        "financial_status": "paid",
                        "fulfillment_status": "fulfilled" if d <= DEMO_TODAY - timedelta(days=3) else "pending",
                    })

    n_orders = write_ndjson(ROOT / "shopify" / "orders.ndjson", orders)
    n_checkouts = write_ndjson(ROOT / "shopify" / "checkouts.ndjson", checkouts)
    n_customers = write_ndjson(ROOT / "shopify" / "customers.ndjson", customers)
    print(f"  shopify: {n_orders} orders, {n_checkouts} checkouts, {n_customers} customers")


# -----------------------------------------------------------------------------
# Klaviyo
# -----------------------------------------------------------------------------


def klaviyo_data():
    """Email profiles, campaigns, flows. Encodes the broken popup story."""
    profiles = []
    campaigns = []
    flow_revenue = []

    # Profiles (email signups) — popup drops daily signups from ~85 to ~11
    for d in daterange(START_DATE, DEMO_TODAY + timedelta(days=1)):
        signups_today = (gauss_int(85, 12) if d < SHOPIFY_THEME_DEPLOY else gauss_int(11, 4))
        for _ in range(signups_today):
            source = (
                "popup" if d < SHOPIFY_THEME_DEPLOY and random.random() < 0.85
                else "checkout" if random.random() < 0.5
                else "organic_form"
            )
            profiles.append({
                "id": "prof_" + uuid.uuid4().hex[:10],
                "email": f"u{uuid.uuid4().hex[:8]}@example.com",
                "created_at": datetime.combine(d, datetime.min.time()).isoformat(),
                "source": source,
                "is_subscribed": True,
            })

    # Campaigns — sent ~weekly, open rate slowly decaying
    for i, d in enumerate(daterange(START_DATE, DEMO_TODAY)):
        if d.weekday() != 1:  # Tuesday sends only
            continue
        # Open rate trends down because the list is aging (fewer fresh subs)
        weeks_since_popup_broke = max(0, (d - SHOPIFY_THEME_DEPLOY).days / 7)
        open_rate = 0.22 - 0.005 * weeks_since_popup_broke  # gentle decay
        ctr = open_rate * 0.18
        sent = gauss_int(28000, 2000)
        campaigns.append({
            "id": "camp_" + uuid.uuid4().hex[:10],
            "name": f"Weekly Newsletter {d.isoformat()}",
            "sent_at": datetime.combine(d, datetime.min.time()).isoformat(),
            "recipients": sent,
            "open_rate": round(open_rate, 4),
            "click_rate": round(ctr, 4),
            "attributed_revenue": round(sent * open_rate * ctr * 12.0, 2),
        })

    # Flows — abandoned cart, welcome series, post-purchase
    for d in daterange(START_DATE, DEMO_TODAY + timedelta(days=1)):
        for flow_name in ["abandoned_cart", "welcome_series", "post_purchase"]:
            # Welcome series collapses because no new signups feed it
            if flow_name == "welcome_series" and d >= SHOPIFY_THEME_DEPLOY:
                revenue = gauss_int(120, 40)
            elif flow_name == "welcome_series":
                revenue = gauss_int(680, 90)
            elif flow_name == "abandoned_cart":
                # Abandoned-cart revenue dips a bit (fewer carts to recover)
                revenue = gauss_int(700, 100) if d < SHOPIFY_THEME_DEPLOY else gauss_int(550, 90)
            else:  # post_purchase
                revenue = gauss_int(280, 50)
            flow_revenue.append({
                "date": d.isoformat(),
                "flow_name": flow_name,
                "attributed_revenue": revenue,
            })

    n_p = write_ndjson(ROOT / "klaviyo" / "profiles.ndjson", profiles)
    n_c = write_ndjson(ROOT / "klaviyo" / "campaigns.ndjson", campaigns)
    n_f = write_ndjson(ROOT / "klaviyo" / "flows.ndjson", flow_revenue)
    print(f"  klaviyo: {n_p} profiles, {n_c} campaigns, {n_f} flow_revenue rows")


# -----------------------------------------------------------------------------
# TikTok Ads — the stale-creative story
# -----------------------------------------------------------------------------


def tiktok_data():
    # Three ads created on April 7, 2026 — no new creative since
    ads = [
        {"id": "tt_ad_001", "name": "Mint Renewal Serum - Hook A", "created_at": TIKTOK_CREATIVE_STALE_SINCE.isoformat(), "status": "active"},
        {"id": "tt_ad_002", "name": "Mint Renewal Serum - Hook B", "created_at": TIKTOK_CREATIVE_STALE_SINCE.isoformat(), "status": "active"},
        {"id": "tt_ad_003", "name": "Foundation Routine Demo",   "created_at": TIKTOK_CREATIVE_STALE_SINCE.isoformat(), "status": "active"},
    ]
    # Older ads that have been paused
    for i in range(4):
        ads.append({
            "id": f"tt_ad_paused_{i}",
            "name": f"Q1 Test {i}",
            "created_at": (START_DATE + timedelta(days=10 + i*5)).isoformat(),
            "status": "paused",
        })

    insights = []
    for d in daterange(START_DATE, DEMO_TODAY + timedelta(days=1)):
        days_stale = max(0, (d - TIKTOK_CREATIVE_STALE_SINCE).days)
        # Frequency rises linearly with staleness
        freq = 1.8 + min(days_stale, 50) * 0.07  # ~1.8 → 5.4
        # CTR drops as frequency rises
        ctr = max(0.005, 0.023 - min(days_stale, 50) * 0.0003)
        # CPM rises (TikTok penalizes stale creative)
        cpm = 8.0 + min(days_stale, 50) * 0.12
        spend = gauss_int(800, 80)  # ~$24K/mo total
        impressions = int(spend / cpm * 1000)
        clicks = int(impressions * ctr)
        # Conversion rate stable but volume falls
        purchases = int(clicks * 0.018)
        revenue = round(purchases * 54.0, 2)
        for ad in ads:
            if ad["status"] != "active":
                continue
            insights.append({
                "date": d.isoformat(),
                "ad_id": ad["id"],
                "ad_name": ad["name"],
                "spend": round(spend / 3.0, 2),
                "impressions": int(impressions / 3),
                "clicks": int(clicks / 3),
                "ctr": round(ctr, 4),
                "frequency": round(freq, 2),
                "cpm": round(cpm, 2),
                "purchases": int(purchases / 3),
                "attributed_revenue": round(revenue / 3, 2),
                "roas": round((revenue / 3) / (spend / 3) if spend else 0, 2),
            })

    n_ads = write_ndjson(ROOT / "tiktok-ads" / "ads.ndjson", ads)
    n_ins = write_ndjson(ROOT / "tiktok-ads" / "insights.ndjson", insights)
    print(f"  tiktok-ads: {n_ads} ads, {n_ins} insights rows")


# -----------------------------------------------------------------------------
# Meta Ads + Google Ads — stable performance (control)
# -----------------------------------------------------------------------------


def meta_ads_data():
    campaigns = [
        {"id": "fb_camp_001", "name": "Prospecting - Lookalikes", "objective": "CONVERSIONS"},
        {"id": "fb_camp_002", "name": "Retargeting - Cart Abandoners", "objective": "CONVERSIONS"},
        {"id": "fb_camp_003", "name": "Brand - Reels", "objective": "REACH"},
    ]
    insights = []
    for d in daterange(START_DATE, DEMO_TODAY + timedelta(days=1)):
        for c in campaigns:
            spend = gauss_int(450, 50) if "Prospecting" in c["name"] else gauss_int(250, 40)
            roas = max(0.5, random.gauss(2.3, 0.25))
            insights.append({
                "date": d.isoformat(),
                "campaign_id": c["id"],
                "campaign_name": c["name"],
                "spend": spend,
                "impressions": gauss_int(120000, 15000),
                "clicks": gauss_int(2400, 300),
                "ctr": round(random.gauss(0.02, 0.002), 4),
                "roas": round(roas, 2),
                "attributed_revenue": round(spend * roas, 2),
            })

    write_ndjson(ROOT / "meta-ads" / "campaigns.ndjson", campaigns)
    n = write_ndjson(ROOT / "meta-ads" / "insights.ndjson", insights)
    print(f"  meta-ads: {len(campaigns)} campaigns, {n} insights rows")


def google_ads_data():
    campaigns = [
        {"id": "ga_camp_001", "name": "Search - Brand", "type": "SEARCH"},
        {"id": "ga_camp_002", "name": "Shopping - All Products", "type": "SHOPPING"},
        {"id": "ga_camp_003", "name": "Performance Max", "type": "PMAX"},
    ]
    insights = []
    for d in daterange(START_DATE, DEMO_TODAY + timedelta(days=1)):
        for c in campaigns:
            if c["type"] == "SEARCH":
                spend, roas_mu = gauss_int(180, 25), 6.5
            elif c["type"] == "SHOPPING":
                spend, roas_mu = gauss_int(360, 40), 3.1
            else:
                spend, roas_mu = gauss_int(280, 35), 2.4
            roas = max(0.5, random.gauss(roas_mu, 0.35))
            insights.append({
                "date": d.isoformat(),
                "campaign_id": c["id"],
                "campaign_name": c["name"],
                "spend": spend,
                "impressions": gauss_int(45000, 6000),
                "clicks": gauss_int(800, 100),
                "ctr": round(random.gauss(0.018, 0.002), 4),
                "roas": round(roas, 2),
                "attributed_revenue": round(spend * roas, 2),
            })

    write_ndjson(ROOT / "google-ads" / "campaigns.ndjson", campaigns)
    n = write_ndjson(ROOT / "google-ads" / "insights.ndjson", insights)
    print(f"  google-ads: {len(campaigns)} campaigns, {n} insights rows")


# -----------------------------------------------------------------------------
# Stripe — payment data (mostly mirrors Shopify orders)
# -----------------------------------------------------------------------------


def stripe_data(approx_orders: int = 11000):
    """We don't reconcile precisely with Shopify here; the agent will see the
    same revenue trend across both sources."""
    charges = []
    refunds = []
    for d in daterange(START_DATE, DEMO_TODAY + timedelta(days=1)):
        daily = base_traffic_for(d) // 30  # rough order count
        for _ in range(daily):
            amount_cents = int(max(2000, random.gauss(5400, 1800)))
            charges.append({
                "id": "ch_" + uuid.uuid4().hex[:12],
                "amount": amount_cents,
                "currency": "usd",
                "created": int(datetime.combine(d, datetime.min.time()).timestamp()),
                "status": "succeeded",
                "payment_method_details_type": random.choice(["card", "card", "card", "apple_pay", "link"]),
            })
            if random.random() < 0.012:
                refunds.append({
                    "id": "re_" + uuid.uuid4().hex[:12],
                    "amount": amount_cents,
                    "charge": charges[-1]["id"],
                    "created": int(datetime.combine(d + timedelta(days=random.randint(1, 14)), datetime.min.time()).timestamp()),
                    "reason": random.choice(["requested_by_customer", "duplicate", "fraudulent"]),
                })

    n_ch = write_ndjson(ROOT / "stripe" / "charges.ndjson", charges)
    n_re = write_ndjson(ROOT / "stripe" / "refunds.ndjson", refunds)
    print(f"  stripe: {n_ch} charges, {n_re} refunds")


# -----------------------------------------------------------------------------
# Yotpo — reviews, mostly stable (so the agent confirms it's NOT a product issue)
# -----------------------------------------------------------------------------


def yotpo_data():
    reviews = []
    for d in daterange(START_DATE, DEMO_TODAY + timedelta(days=1)):
        n = gauss_int(8, 3)
        for _ in range(n):
            score = random.choices([5, 4, 3, 2, 1], weights=[55, 28, 10, 4, 3])[0]
            reviews.append({
                "id": "rev_" + uuid.uuid4().hex[:10],
                "created_at": datetime.combine(d, datetime.min.time()).isoformat(),
                "score": score,
                "product_name": random.choice([
                    "Mint Renewal Serum", "Mint Renewal Serum",
                    "Velvet Cleansing Balm", "Polish Daily Moisturizer",
                    "Rebloom Eye Cream",
                ]),
                "verified_buyer": True,
            })

    n = write_ndjson(ROOT / "yotpo" / "reviews.ndjson", reviews)
    print(f"  yotpo: {n} reviews")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42, help="Seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)
    print(f"Generating synthetic VelvetMint data ({START_DATE} to {DEMO_TODAY})")
    print(f"  TikTok creative stale since: {TIKTOK_CREATIVE_STALE_SINCE}")
    print(f"  Shopify theme deploy / bugs introduced: {SHOPIFY_THEME_DEPLOY}")
    print()

    shopify_data()
    klaviyo_data()
    tiktok_data()
    meta_ads_data()
    google_ads_data()
    stripe_data()
    yotpo_data()

    print()
    print(f"Done. Output in {ROOT}/")


if __name__ == "__main__":
    main()
