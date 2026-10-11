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


WEATHER_API = "https://api.open-meteo.com/v1/forecast"


def _feels_like(lat: float, lon: float, date: str) -> dict[str, float]:
    """Hourly apparent temperature (°C) for the day; empty if the weather API is unavailable."""
    query = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "hourly": "apparent_temperature",
        "start_date": date, "end_date": date, "timezone": "Asia/Kolkata",
    })
    try:
        with urllib.request.urlopen(f"{WEATHER_API}?{query}", timeout=10) as resp:
            hourly = json.load(resp)["hourly"]
        return {t[11:16]: v for t, v in zip(hourly["time"], hourly["apparent_temperature"]) if v is not None}
    except Exception:
        return {}


def calibrate(hours: list[dict], date: str, calibration: dict | None) -> str | None:
    """Bias-correct model PM2.5 to the school's nearest CPCB ground station.

    At Rohini, CAMS read 1.2-1.6x lower than the CPCB station in early October 2025 and 2.5-4.8x lower
    from late October through November. Thresholds are absolute, so uncorrected values under-protect."""
    window = next((w for w in (calibration or {}).get("windows", []) if w["from"] <= date[5:] <= w["to"]), None)
    if not window:
        return None
    factors = {int(k): v for k, v in window["factors"].items()}
    for h in hours:
        hour = int(h["time"][:2])
        nearest = min(factors, key=lambda k: abs(k - hour))
        h["pm25_model"] = h["pm25"]
        h["pm25"] = round(h["pm25"] * factors[nearest], 1)
    return f"{calibration['station']} ({window['basis']})"


def fetch(lat: float, lon: float, date: str, calibration: dict | None = None) -> dict:
    """Return {"date", "source", "hours": [{"time": "HH:MM", "pm25", "pm10", "feels"}]} for one IST day.
    Replay days are measured station data served from data/, so demos never depend on the network."""
    fixture = _fixture(date)
    if fixture:
        return fixture
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
            feels = _feels_like(lat, lon, date)
            for h in hours:
                h["feels"] = feels.get(h["time"])
            station = calibrate(hours, date, calibration)
            return {
                "date": date,
                "source": "Open-Meteo forecast (CAMS)" + (f", bias-corrected to CPCB {station}" if station else "")
                          + (" + feels-like temperature" if feels else ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "hours": hours,
            }
        except Exception as e:  # network, HTTP, or shape errors
            last_error = e
            time.sleep(1.5 * (attempt + 1))
    raise ForecastUnavailable(f"forecast for {date} unavailable: {last_error}")


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def at_minute(hours: list[dict], minute: float, key: str = "pm25") -> float | None:
    """Linear interpolation between hourly values (values are treated as on-the-hour)."""
    points = [(_minutes(h["time"]), h[key]) for h in hours if h.get(key) is not None]
    if not points:
        return None
    if minute <= points[0][0]:
        return points[0][1]
    for (m0, v0), (m1, v1) in zip(points, points[1:]):
        if m0 <= minute <= m1:
            return v0 + (v1 - v0) * (minute - m0) / (m1 - m0)
    return points[-1][1]


def period_average(hours: list[dict], start: str, end: str, key: str = "pm25") -> float | None:
    a, b = _minutes(start), _minutes(end)
    samples = [at_minute(hours, m, key) for m in range(a, b + 1, 5)]
    if samples[0] is None:
        return None
    return sum(samples) / len(samples)
