"""Hourly PM2.5 for a school's coordinates from the Open-Meteo Air Quality API (CAMS, no key)."""

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://air-quality-api.open-meteo.com/v1/air-quality"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class ForecastUnavailable(Exception):
    pass


def _fixture(date: str) -> dict | None:
    path = os.path.join(DATA_DIR, f"replay-{date}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    data["source"] = data.get("source", "archived")
    return data


def fetch(lat: float, lon: float, date: str) -> dict:
    """Return {"date", "source", "hours": [{"time": "HH:MM", "pm25", "pm10"}]} for one IST day."""
    query = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "hourly": "pm2_5,pm10",
        "start_date": date, "end_date": date, "timezone": "Asia/Kolkata",
    })
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f"{API}?{query}", timeout=12) as resp:
                body = json.load(resp)
            hourly = body["hourly"]
            hours = [
                {"time": t[11:16], "pm25": p, "pm10": q}
                for t, p, q in zip(hourly["time"], hourly["pm2_5"], hourly["pm10"])
                if p is not None
            ]
            if len(hours) < 20:
                raise ForecastUnavailable(f"only {len(hours)} hours returned for {date}")
            return {
                "date": date,
                "source": "Open-Meteo Air Quality API (CAMS)",
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "hours": hours,
            }
        except Exception as e:  # network, HTTP, or shape errors
            last_error = e
            time.sleep(1.5 * (attempt + 1))
    fixture = _fixture(date)
    if fixture:
        return fixture
    raise ForecastUnavailable(f"forecast for {date} unavailable: {last_error}")


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def at_minute(hours: list[dict], minute: float, key: str = "pm25") -> float:
    """Linear interpolation between hourly values (values are treated as on-the-hour)."""
    points = [(_minutes(h["time"]), h[key]) for h in hours]
    if minute <= points[0][0]:
        return points[0][1]
    for (m0, v0), (m1, v1) in zip(points, points[1:]):
        if m0 <= minute <= m1:
            return v0 + (v1 - v0) * (minute - m0) / (m1 - m0)
    return points[-1][1]


def period_average(hours: list[dict], start: str, end: str) -> float:
    a, b = _minutes(start), _minutes(end)
    samples = [at_minute(hours, m) for m in range(a, b + 1, 5)]
    return sum(samples) / len(samples)
