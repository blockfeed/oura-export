#!/usr/bin/env python3
"""
export_oura.py

Export sleep and heart rate data from the Oura Cloud API via the
hedgertronic/oura-ring Python client.

Dependency:
  https://github.com/hedgertronic/oura-ring

Auth:
  Provide a Bearer token via one of:
    - OURA_TOKEN
    - PERSONAL_ACCESS_TOKEN
    - OURA_ACCESS_TOKEN

Default export window:
  --days 7
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from oura_ring import OuraClient


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False))
            f.write("\n")


def _write_jsonl_gz(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False))
            f.write("\n")


def _as_list(maybe_list_or_obj: Any) -> List[Dict[str, Any]]:
    if maybe_list_or_obj is None:
        return []
    if isinstance(maybe_list_or_obj, list):
        return maybe_list_or_obj
    if isinstance(maybe_list_or_obj, dict):
        return [maybe_list_or_obj]
    raise TypeError(f"Unexpected type: {type(maybe_list_or_obj)!r}")


def _min_max_avg(nums: List[float]) -> Dict[str, Optional[float]]:
    if not nums:
        return {"min": None, "max": None, "avg": None}
    return {"min": float(min(nums)), "max": float(max(nums)), "avg": float(sum(nums) / len(nums))}


def summarize_daily_sleep(daily_sleep: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in daily_sleep:
        out.append(
            {
                "day": row.get("day"),
                "sleep_score": row.get("score"),
                "sleep_contrib": row.get("contributors") or {},
                "timestamp": row.get("timestamp"),
            }
        )
    return out


def summarize_daily_readiness(daily_readiness: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in daily_readiness:
        out.append(
            {
                "day": row.get("day"),
                "readiness_score": row.get("score"),
                "temperature_deviation": row.get("temperature_deviation"),
                "temperature_trend_deviation": row.get("temperature_trend_deviation"),
                "readiness_contrib": row.get("contributors") or {},
                "timestamp": row.get("timestamp"),
            }
        )
    return out


def summarize_sleep_periods(sleep_periods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in sleep_periods:
        out.append(
            {
                "id": r.get("id"),
                "day": r.get("day"),
                "type": r.get("type"),
                "bedtime_start": r.get("bedtime_start"),
                "bedtime_end": r.get("bedtime_end"),
                "time_in_bed_s": r.get("time_in_bed"),
                "total_sleep_duration_s": r.get("total_sleep_duration"),
                "efficiency_pct": r.get("efficiency"),
                "latency_s": r.get("latency"),
                "awake_time_s": r.get("awake_time"),
                "rem_sleep_duration_s": r.get("rem_sleep_duration"),
                "deep_sleep_duration_s": r.get("deep_sleep_duration"),
                "light_sleep_duration_s": r.get("light_sleep_duration"),
                "restless_periods_s": r.get("restless_periods"),
                "average_breath": r.get("average_breath"),
                "average_heart_rate_bpm": r.get("average_heart_rate"),
                "lowest_heart_rate_bpm": r.get("lowest_heart_rate"),
                "average_hrv_ms": r.get("average_hrv"),
            }
        )
    return out


def summarize_heartrate_daily(heartrate_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}

    def bucket_for(ts: str) -> str:
        return ts[:10]

    for r in heartrate_rows:
        ts = r.get("timestamp")
        bpm = r.get("bpm")
        src = r.get("source")
        if not ts or bpm is None:
            continue

        day = bucket_for(ts)
        b = buckets.setdefault(
            day,
            {"day": day, "n": 0, "all_bpm": [], "sleep_bpm": [], "awake_bpm": [], "sources": {}},
        )
        b["n"] += 1
        b["all_bpm"].append(float(bpm))
        b["sources"][str(src)] = b["sources"].get(str(src), 0) + 1
        if src == "sleep":
            b["sleep_bpm"].append(float(bpm))
        else:
            b["awake_bpm"].append(float(bpm))

    out: List[Dict[str, Any]] = []
    for day in sorted(buckets.keys()):
        b = buckets[day]
        out.append(
            {
                "day": day,
                "samples_5m": b["n"],
                "bpm_all": _min_max_avg(b["all_bpm"]),
                "bpm_sleep": _min_max_avg(b["sleep_bpm"]),
                "bpm_awake": _min_max_avg(b["awake_bpm"]),
                "sources_counts": b["sources"],
            }
        )
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Export Oura sleep and heart rate data.")
    ap.add_argument("--days", type=int, default=7, help="Number of days to export (default: 7).")
    ap.add_argument("--out-dir", default="oura_export", help="Output directory (default: oura_export).")
    ap.add_argument(
        "--include-raw-heartrate",
        action="store_true",
        help="Write gzipped raw 5-minute heart-rate samples (can be large).",
    )
    ap.add_argument(
        "--no-extras",
        action="store_true",
        help="Only export sleep + sleep periods + heart rate (skip readiness/activity/stress/spo2/etc.).",
    )
    args = ap.parse_args(argv)

    if args.days <= 0:
        print("ERROR: --days must be > 0", file=sys.stderr)
        return 2

    token = (os.getenv("OURA_TOKEN") or os.getenv("PERSONAL_ACCESS_TOKEN") or os.getenv("OURA_ACCESS_TOKEN") or "").strip()
    if not token:
        print("ERROR: missing token. Set OURA_TOKEN (or PERSONAL_ACCESS_TOKEN / OURA_ACCESS_TOKEN).", file=sys.stderr)
        return 2

    today = dt.date.today()
    start_date = today - dt.timedelta(days=args.days)
    start_date_s = start_date.isoformat()
    end_date_s = today.isoformat()

    # Heart-rate endpoint uses datetime strings
    start_dt_s = f"{start_date_s}T00:00:00"
    end_dt_s = f"{end_date_s}T00:00:00"

    out_dir = Path(args.out_dir)
    _ensure_dir(out_dir)

    meta = {
        "exported_at_utc": _utc_now_iso(),
        "range": {
            "days": args.days,
            "start_date": start_date_s,
            "end_date": end_date_s,
            "start_datetime": start_dt_s,
            "end_datetime": end_dt_s,
        },
        "env_token_source": "OURA_TOKEN|PERSONAL_ACCESS_TOKEN|OURA_ACCESS_TOKEN (not written to disk)",
    }
    _write_json(out_dir / "meta.json", meta)

    with OuraClient(token) as client:
        daily_sleep = _as_list(client.get_daily_sleep(start_date_s, end_date_s))
        sleep_periods = _as_list(client.get_sleep_periods(start_date_s, end_date_s))
        heartrate = _as_list(client.get_heart_rate(start_dt_s, end_dt_s))

        _write_json(out_dir / "daily_sleep.json", daily_sleep)
        _write_json(out_dir / "sleep_periods.json", sleep_periods)

        _write_jsonl(out_dir / "sleep_daily_summary.jsonl", summarize_daily_sleep(daily_sleep))
        _write_jsonl(out_dir / "sleep_periods_summary.jsonl", summarize_sleep_periods(sleep_periods))
        _write_jsonl(out_dir / "heartrate_daily_summary.jsonl", summarize_heartrate_daily(heartrate))

        if args.include_raw_heartrate:
            _write_jsonl_gz(out_dir / "heartrate_5m.jsonl.gz", heartrate)

        if not args.no_extras:
            # These are commonly useful for interpreting fatigue/sleepiness trends.
            personal_info = client.get_personal_info()
            ring_configuration = _as_list(client.get_ring_configuration(start_date_s, end_date_s))
            daily_readiness = _as_list(client.get_daily_readiness(start_date_s, end_date_s))
            daily_activity = _as_list(client.get_daily_activity(start_date_s, end_date_s))
            daily_stress = _as_list(client.get_daily_stress(start_date_s, end_date_s))
            daily_spo2 = _as_list(client.get_daily_spo2(start_date_s, end_date_s))
            sleep_time = _as_list(client.get_sleep_time(start_date_s, end_date_s))
            sessions = _as_list(client.get_sessions(start_date_s, end_date_s))
            enhanced_tag = _as_list(client.get_enhanced_tag(start_date_s, end_date_s))
            rest_mode_period = _as_list(client.get_rest_mode_period(start_date_s, end_date_s))

            _write_json(out_dir / "personal_info.json", personal_info)
            _write_json(out_dir / "ring_configuration.json", ring_configuration)
            _write_json(out_dir / "daily_readiness.json", daily_readiness)
            _write_jsonl(out_dir / "readiness_daily_summary.jsonl", summarize_daily_readiness(daily_readiness))
            _write_json(out_dir / "daily_activity.json", daily_activity)
            _write_json(out_dir / "daily_stress.json", daily_stress)
            _write_json(out_dir / "daily_spo2.json", daily_spo2)
            _write_json(out_dir / "sleep_time.json", sleep_time)
            _write_json(out_dir / "sessions.json", sessions)
            _write_json(out_dir / "enhanced_tag.json", enhanced_tag)
            _write_json(out_dir / "rest_mode_period.json", rest_mode_period)

    print(f"OK: wrote export to: {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
