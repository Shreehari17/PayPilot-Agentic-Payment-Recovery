from langchain_core.tools import tool
from agent.commerce_data import get_transactions
from collections import defaultdict
import requests
def _pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)
@tool
def get_payment_analytics(query: str = "") -> str:
    """Get today's vs yesterday's payment performance analytics.
    Returns overall success rates, per-payment-method breakdown, and
    top failure reasons for today. Use this FIRST whenever the merchant
    mentions a drop in payment success, revenue at risk, or asks you
    to investigate payment performance."""
    try:
        txns = get_transactions()
        today = [t for t in txns if t["timestamp"].startswith("2026-09-03")]
        yesterday = [t for t in txns if t["timestamp"].startswith("2026-09-02")]

        def success_rate(rows):
            success = sum(1 for r in rows if r["status"] == "SUCCESS")
            return _pct(success, len(rows)), success, len(rows) - success

        today_rate, today_success, today_failed = success_rate(today)
        yest_rate, yest_success, yest_failed = success_rate(yesterday)

        methods = sorted(set(t["payment_method"] for t in txns))
        method_lines = []
        for m in methods:
            t_rows = [t for t in today if t["payment_method"] == m]
            y_rows = [t for t in yesterday if t["payment_method"] == m]
            t_rate, _, _ = success_rate(t_rows) if t_rows else (0.0, 0, 0)
            y_rate, _, _ = success_rate(y_rows) if y_rows else (0.0, 0, 0)
            method_lines.append(f"  {m}: {t_rate}% success today (was {y_rate}% yesterday)")

        today_failures = [t for t in today if t["status"] == "FAILED"]
        reason_counts = defaultdict(int)
        for t in today_failures:
            reason_counts[t["failure_reason"]] += 1
        reason_lines = []
        if today_failures:
            for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
                reason_lines.append(f"  {reason}: {_pct(count, len(today_failures))}% of today's failures ({count} txns)")

        revenue_at_risk = sum(t["amount"] for t in today_failures)

        report = f"""Today's Performance (Sept 3):
  Total transactions: {len(today)}
  Successful: {today_success}
  Failed: {today_failed}
  Success rate: {today_rate}%
  Revenue at risk (failed transaction value): Rs.{revenue_at_risk:,}

Yesterday's Performance (Sept 2):
  Success rate: {yest_rate}%

Change: {round(today_rate - yest_rate, 1)} percentage points

By payment method (today vs yesterday):
{chr(10).join(method_lines)}

Top failure reasons today:
{chr(10).join(reason_lines) if reason_lines else "  No failures today"}
"""
        return report
    except Exception as e:
        return f"Error retrieving payment analytics: {str(e)}"
@tool
def get_payment_recovery_guidance(issue_description: str) -> str:
    """Get merchant recovery guidance for a specific payment failure pattern.
    Call this AFTER get_payment_analytics has identified a specific issue
    (e.g. 'UPI timeout failures'). Pass a short description of the issue.
    Returns knowledge-grounded recovery steps, not fabricated advice.
    """
    try:
        response = requests.post(
            "http://localhost:8000/retrieve",
            json={
                "tenant_id": "default",
                "query": issue_description,
                "top_k": 3
            },
            timeout=10
        )

        data = response.json()
        results = data.get("chunks", [])

        if not results:
            return f"No recovery guidance found for: {issue_description}"

        guidance = "\n\n---\n\n".join(
            [r["chunk_text"] for r in results]
        )

        return f"""
Recovery guidance retrieved from the internal knowledge base
for the identified payment issue:

{guidance}

IMPORTANT:
This is the authoritative recovery guidance for this issue.
Do not add thresholds, SLAs, percentages, retry limits, timeout values,
deadlines, targets, or other operational policies that are not explicitly
present in the retrieved guidance.
"""

    except Exception as e:
        return f"Error retrieving recovery guidance: {str(e)}"