"""SRE Wrapped reporting endpoints."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.db.queries import get_all_tickets

router = APIRouter()

OPENAI_MODEL = "gpt-4o-mini"
OPENAI_PROMPT = (
    "you are an SRE analyst who writes like a sports commentator - "
    "given raw incident stats, return ONLY a valid JSON object with dramatic and specific "
    "phrases for each field, no markdown, no explanation"
)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "day":
        return now - timedelta(days=1)
    if period == "week":
        return now - timedelta(days=7)
    return now - timedelta(days=30)


def _period_days(period: str) -> int:
    if period == "day":
        return 1
    if period == "week":
        return 7
    return 30


def _compute_raw_stats(rows: list[dict[str, Any]], period: str) -> dict[str, Any]:
    threshold = _period_start(period)

    filtered: list[dict[str, Any]] = []
    for row in rows:
        opened_at = _parse_iso(str(row.get("created_at") or ""))
        if opened_at and opened_at >= threshold:
            row_copy = dict(row)
            row_copy["_opened_dt"] = opened_at
            row_copy["_resolved_dt"] = _parse_iso(str(row.get("resolved_at") or ""))
            filtered.append(row_copy)

    plugin_counts: dict[str, int] = {}
    category_duration_hours: dict[str, list[float]] = {}
    p1_hours = [0 for _ in range(24)]
    total_hours_lost = 0.0

    for row in filtered:
        plugin = (str(row.get("affected_plugin") or "unknown-plugin").strip() or "unknown-plugin")
        plugin_counts[plugin] = plugin_counts.get(plugin, 0) + 1

        severity = str(row.get("severity") or "").upper()
        opened_at = row["_opened_dt"]
        resolved_at = row.get("_resolved_dt")
        category = str(row.get("incident_type") or "uncategorized").strip() or "uncategorized"

        if severity == "P1":
            p1_hours[opened_at.hour] += 1

        if resolved_at and resolved_at >= opened_at:
            duration_hours = (resolved_at - opened_at).total_seconds() / 3600.0
            total_hours_lost += duration_hours
            category_duration_hours.setdefault(category, []).append(duration_hours)

    most_failing_plugin = "none"
    if plugin_counts:
        most_failing_plugin = max(plugin_counts.items(), key=lambda item: item[1])[0]

    avg_resolution_time_per_category: dict[str, float] = {}
    for category, durations in category_duration_hours.items():
        if durations:
            avg_resolution_time_per_category[category] = round(sum(durations) / len(durations), 2)

    fastest_resolved_category = "none"
    if avg_resolution_time_per_category:
        fastest_resolved_category = min(
            avg_resolution_time_per_category.items(),
            key=lambda item: item[1],
        )[0]

    peak_hour = max(range(24), key=lambda idx: p1_hours[idx]) if any(p1_hours) else 0
    estimated_cost = round(total_hours_lost * 150.0, 2)

    return {
        "period": period,
        "period_days": _period_days(period),
        "total_incidents": len(filtered),
        "most_failing_plugin": most_failing_plugin,
        "fastest_resolved_category": fastest_resolved_category,
        "p1_hour_distribution": p1_hours,
        "peak_p1_hour": peak_hour,
        "avg_resolution_time_per_category": avg_resolution_time_per_category,
        "total_hours_lost": round(total_hours_lost, 2),
        "estimated_cost_usd": estimated_cost,
    }


def _fallback_phrases(raw_stats: dict[str, Any]) -> dict[str, str]:
    plugin = raw_stats.get("most_failing_plugin", "unknown")
    category = raw_stats.get("fastest_resolved_category", "uncategorized")
    chaos_hour = int(raw_stats.get("peak_p1_hour", 0))
    cost = float(raw_stats.get("estimated_cost_usd", 0.0))

    return {
        "team_summary": (
            f"{raw_stats.get('total_incidents', 0)} incidents in the last {raw_stats.get('period_days', 30)} days "
            "kept your on-call rotation in constant motion."
        ),
        "villain_plugin": plugin,
        "villain_phrase": f"{plugin} attacked the scoreboard more often than any other service.",
        "superpower_category": category,
        "superpower_phrase": f"Your team neutralized {category} faster than every other category.",
        "chaos_hour_phrase": f"The loudest alarm bell rang around {chaos_hour:02d}:00.",
        "downtime_cost_phrase": f"Downtime pressure reached ${cost:,.2f} at $150 per hour.",
        "chef_recommendation": (
            "Prioritize hardening for the villain plugin, automate rollback playbooks, and run one focused game day "
            "on the busiest hour to cut next period's incident cost."
        ),
    }


async def _narrate_with_openai(raw_stats: dict[str, Any]) -> dict[str, str]:
    fallback = _fallback_phrases(raw_stats)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        # Assumption: local dev can run with deterministic fallback text when OpenAI key is absent.
        return fallback

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": OPENAI_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(raw_stats, ensure_ascii=True),
            }
        ],
        "temperature": 0.7,
        "max_tokens": 700,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code >= 400:
        return fallback

    data = response.json()
    text = str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()

    if not text:
        return fallback

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return fallback

    required_keys = [
        "team_summary",
        "villain_plugin",
        "villain_phrase",
        "superpower_category",
        "superpower_phrase",
        "chaos_hour_phrase",
        "downtime_cost_phrase",
        "chef_recommendation",
    ]
    merged: dict[str, str] = {}
    for key in required_keys:
        value = parsed.get(key)
        if value is None or str(value).strip() == "":
            merged[key] = fallback[key]
        else:
            merged[key] = str(value)

    return merged


@router.get("/reports/summary")
async def reports_summary(period: str = Query(default="month", pattern="^(day|week|month)$")) -> dict[str, Any]:
    rows = await get_all_tickets()
    raw_stats = _compute_raw_stats(rows, period)
    phrases = await _narrate_with_openai(raw_stats)

    return {
        "raw": raw_stats,
        "phrases": phrases,
    }
