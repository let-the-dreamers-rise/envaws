"""Turns an hourly PM2.5 forecast into a day plan: which outdoor activities move, which go
indoors, and why. Everything here is deterministic code + Cedar; no LLM involved."""

import copy
from collections import Counter
from datetime import datetime, timezone

from . import aqi, rules
from . import forecast as fc
from .school import OUTDOOR_SUBJECTS

# Inhaled-dose assumptions (m³ of air per minute for a school-age child) and the indoor/outdoor
# PM2.5 ratio for a naturally ventilated classroom. Rough, documented in the README.
VENTILATION = {"low": 0.008, "moderate": 0.015, "high": 0.025}
INDOOR_RATIO = 0.8
MIN_GAIN = 0.2      # move PE only if the new slot is at least 20% cleaner
MIN_COOLER = 3      # ...or, when heat is the problem, at least 3 °C cooler (feels-like)
QUIET_BELOW = 60    # Satisfactory or better: leave the timetable alone

INDOOR_ALTERNATIVE = {
    "PE": ("Indoor PE (yoga & stretching)", "इनडोर पीटी (योग और स्ट्रेचिंग)"),
    "Assembly": ("Assembly in classrooms (PA system)", "प्रार्थना सभा कक्षाओं में (माइक से)"),
    "Recess": ("Indoor recess (reading, board games)", "इनडोर रिसेस (किताबें, बोर्ड गेम)"),
}


def _minutes(p: dict) -> int:
    (h0, m0), (h1, m1) = (map(int, p["start"].split(":")), map(int, p["end"].split(":")))
    return (h1 * 60 + m1) - (h0 * 60 + m0)


def build_plan(school: dict, forecast: dict, date: str, mode: str) -> dict:
    hours = forecast["hours"]
    grap = int(school.get("grap_stage", 0))
    capacity = int(school.get("playground_capacity", 2))
    classes = {c["id"]: c for c in school["classes"]}

    pm, feels, periods = {}, {}, []
    for p in school["periods"]:
        value = fc.period_average(hours, p["start"], p["end"])
        heat = fc.period_average(hours, p["start"], p["end"], "feels")
        pm[p["id"]], feels[p["id"]] = value, heat
        periods.append({**p, "pm25": round(value), "band": aqi.band(value), "minutes": _minutes(p),
                        "feels": round(heat) if heat is not None else None})
    by_id = {p["id"]: p for p in periods}
    teaching = [p["id"] for p in periods if p["kind"] == "teaching"]

    before = {cid: copy.deepcopy(c["timetable"]) for cid, c in classes.items()}
    after = copy.deepcopy(before)
    busy = {(cell["teacher"], pid): cid for cid, tt in after.items() for pid, cell in tt.items()}
    ground = Counter(pid for tt in after.values() for pid, cell in tt.items()
                     if cell["subject"] in OUTDOOR_SUBJECTS)
    changes = []

    # 1. School-wide outdoor events stay at their time; they can only change venue.
    for p in periods:
        if p["kind"] not in ("assembly", "recess"):
            continue
        activity = "Assembly" if p["kind"] == "assembly" else "Recess"
        whole = rules.check(activity, pm[p["id"]], grap, feels_like=feels[p["id"]])
        if not whole["allowed"]:
            changes.append({"type": "venue", "activity": activity, "scope": "all", "period": p["id"],
                            "pm25": p["pm25"], "rules": whole["rules"], "regulatory": whole["regulatory"],
                            "alternative": INDOOR_ALTERNATIVE[activity]})
            continue
        blocked = [cid for cid, c in classes.items()
                   if not rules.check(activity, pm[p["id"]], grap, cid, c["grade"], feels_like=feels[p["id"]])["allowed"]]
        if blocked:
            r = rules.check(activity, pm[p["id"]], grap, blocked[0], classes[blocked[0]]["grade"],
                            feels_like=feels[p["id"]])
            changes.append({"type": "venue", "activity": activity, "scope": blocked, "period": p["id"],
                            "pm25": p["pm25"], "rules": r["rules"], "regulatory": r["regulatory"],
                            "alternative": INDOOR_ALTERNATIVE[activity]})

    # 2. PE moves to the cleanest feasible slot. Younger classes pick first.
    pe_slots = [(cid, pid) for cid, tt in before.items() for pid, cell in tt.items()
                if cell["subject"] in OUTDOOR_SUBJECTS]
    pe_slots.sort(key=lambda x: (classes[x[0]]["grade"], -pm[x[1]]))
    for cid, pid in pe_slots:
        grade = classes[cid]["grade"]
        current = pm[pid]
        here = rules.check("PE", current, grap, cid, grade, feels_like=feels[pid])
        if here["allowed"] and current <= QUIET_BELOW:
            continue
        # What makes this slot bad decides what "better" means: cleaner air, or cooler air.
        driver = "heat" if any(r.startswith("heat") for r in here["rules"]) else "air"
        if driver == "heat":
            key, good_enough = feels.get, lambda q: feels[q] <= feels[pid] - MIN_COOLER
        else:
            key, good_enough = pm.get, lambda q: pm[q] <= current * (1 - MIN_GAIN)
        pe_teacher = after[cid][pid]["teacher"]
        skipped, moved = [], False
        for q in sorted((q for q in teaching if q != pid), key=key):
            if not good_enough(q):
                break
            other = after[cid][q]
            if other["subject"] in OUTDOOR_SUBJECTS:
                continue
            there = rules.check("PE", pm[q], grap, cid, grade, feels_like=feels[q])
            if not there["allowed"]:
                skipped.append({"period": q, "why": "rule", "rules": there["rules"]})
                continue
            if ground[q] >= capacity:
                skipped.append({"period": q, "why": "ground_full"})
                continue
            clash = busy.get((pe_teacher, q))
            if clash not in (None, cid):
                skipped.append({"period": q, "why": "teacher_busy", "teacher": pe_teacher, "with": clash})
                continue
            clash = busy.get((other["teacher"], pid))
            if clash not in (None, cid):
                skipped.append({"period": q, "why": "teacher_busy", "teacher": other["teacher"], "with": clash})
                continue
            pe_cell = after[cid][pid]
            after[cid][pid] = {**other, "moved_from": q}
            after[cid][q] = {**pe_cell, "moved_from": pid}
            del busy[(pe_teacher, pid)]
            del busy[(other["teacher"], q)]
            busy[(pe_teacher, q)] = cid
            busy[(other["teacher"], pid)] = cid
            ground[pid] -= 1
            ground[q] += 1
            changes.append({"type": "move", "activity": "PE", "class_id": cid, "from": pid, "to": q,
                            "driver": driver, "pm25_from": round(current), "pm25_to": round(pm[q]),
                            "gain_pct": round((1 - pm[q] / current) * 100),
                            "feels_from": _r(feels[pid]), "feels_to": _r(feels[q]),
                            "rules": here["rules"], "regulatory": here["regulatory"],
                            "swapped": {"subject": other["subject"], "teacher": other["teacher"]},
                            "skipped": skipped})
            moved = True
            break
        if not moved and not here["allowed"]:
            name_en, name_hi = INDOOR_ALTERNATIVE["PE"]
            after[cid][pid] = {"subject": name_en, "subject_hi": name_hi, "teacher": pe_teacher,
                               "indoor_from": "PE"}
            ground[pid] -= 1
            changes.append({"type": "indoor", "activity": "PE", "class_id": cid, "period": pid, "driver": driver,
                            "pm25": round(current), "rules": here["rules"], "regulatory": here["regulatory"],
                            "skipped": skipped})

    # 3. Asthma-watch cohorts: stricter rule on whatever outdoor PE slot remains.
    for cid, tt in after.items():
        count = classes[cid].get("asthma_watch", 0)
        for pid, cell in tt.items():
            if cell["subject"] in OUTDOOR_SUBJECTS and count:
                r = rules.check("PE", pm[pid], grap, cid, classes[cid]["grade"], asthma_cohort=True,
                                feels_like=feels[pid])
                if not r["allowed"]:
                    changes.append({"type": "asthma", "activity": "PE", "class_id": cid, "period": pid,
                                    "count": count, "pm25": round(pm[pid]), "rules": r["rules"],
                                    "regulatory": r["regulatory"]})

    metrics = _metrics(school, periods, pm, before, after, changes)
    pe_feels = lambda tt: [feels[pid] for t in tt.values() for pid, c in t.items()
                           if c["subject"] in OUTDOOR_SUBJECTS and feels[pid] is not None]
    if pe_feels(before):
        metrics["pe_feels_before"] = round(max(pe_feels(before)))
        metrics["pe_feels_after"] = round(max(pe_feels(after))) if pe_feels(after) else None
    metrics["heat_moves"] = sum(1 for c in changes if c.get("driver") == "heat")
    worst = max((p for p in periods), key=lambda p: p["pm25"])
    hottest = max((p for p in periods if p["feels"] is not None), key=lambda p: p["feels"], default=None)
    return {
        "school_id": school["id"],
        "date": date,
        "mode": mode,
        "grap_stage": grap,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "forecast": {"source": forecast.get("source"), "hours": hours},
        "periods": periods,
        "flag": {**aqi.band(worst["pm25"]), "pm25": worst["pm25"], "period": worst["id"]},
        "heat": {"feels": hottest["feels"], "period": hottest["id"]} if hottest else None,
        "timetable_before": before,
        "timetable_after": after,
        "changes": changes,
        "regulatory": any(c.get("regulatory") for c in changes),
        "metrics": metrics,
        "quiet": not changes,
        "period_index": {pid: {"label": p["label"], "start": p["start"], "end": p["end"]}
                         for pid, p in by_id.items()},
    }


def _r(value):
    return round(value) if value is not None else None


def _dose(pm25: float, minutes: int, effort: str, indoor: bool) -> float:
    return pm25 * (INDOOR_RATIO if indoor else 1.0) * minutes * VENTILATION[effort]


def _metrics(school, periods, pm, before, after, changes) -> dict:
    """Estimated PM2.5 inhaled (µg) during the day's outdoor activities, before vs after."""
    classes = {c["id"]: c for c in school["classes"]}
    mins = {p["id"]: p["minutes"] for p in periods}
    venue_all = {(c["activity"], c["period"]) for c in changes if c["type"] == "venue" and c["scope"] == "all"}
    venue_some = {(c["activity"], c["period"], cid) for c in changes
                  if c["type"] == "venue" and c["scope"] != "all" for cid in c["scope"]}
    asthma = {c["class_id"] for c in changes if c["type"] == "asthma"}
    total_before = total_after = 0.0
    pe_before, pe_after, kids = [], [], 0
    for cid, c in classes.items():
        n, sick = c["strength"], c.get("asthma_watch", 0)
        kids += n
        for p in periods:
            if p["kind"] in ("assembly", "recess"):
                act = "Assembly" if p["kind"] == "assembly" else "Recess"
                effort = "low" if act == "Assembly" else "moderate"
                indoor = (act, p["id"]) in venue_all or (act, p["id"], cid) in venue_some
                total_before += n * _dose(pm[p["id"]], p["minutes"], effort, False)
                total_after += n * _dose(pm[p["id"]], p["minutes"], "low" if indoor else effort, indoor)
        for pid, cell in before[cid].items():
            if cell["subject"] in OUTDOOR_SUBJECTS:
                total_before += n * _dose(pm[pid], mins[pid], "high", False)
                pe_before.append(pm[pid])
        for pid, cell in after[cid].items():
            if cell["subject"] in OUTDOOR_SUBJECTS:
                out = n - (sick if cid in asthma else 0)
                total_after += out * _dose(pm[pid], mins[pid], "high", False)
                total_after += (n - out) * _dose(pm[pid], mins[pid], "moderate", True)
                pe_after.append(pm[pid])
            elif cell.get("indoor_from"):
                total_after += n * _dose(pm[pid], mins[pid], "moderate", True)
                pe_after.append(pm[pid] * INDOOR_RATIO)
    avg = lambda xs: round(sum(xs) / len(xs)) if xs else 0
    reduction = round((1 - total_after / total_before) * 100) if total_before else 0
    return {
        "students": kids,
        "dose_before_mg": round(total_before / 1000, 1),
        "dose_after_mg": round(total_after / 1000, 1),
        "reduction_pct": reduction,
        "pe_pm25_before": avg(pe_before),
        "pe_pm25_after": avg(pe_after),
        "pe_moved": sum(1 for c in changes if c["type"] == "move"),
        "pe_indoor": sum(1 for c in changes if c["type"] == "indoor"),
        "asthma_kids_indoor": sum(c["count"] for c in changes if c["type"] == "asthma"),
    }
