import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["LLM_MODE"] = "off"

from cleanhour import api, forecast, notices, optimizer, rules  # noqa: E402
from cleanhour.school import DEMO_SCHOOL  # noqa: E402

REPLAY = forecast._fixture("2025-11-21")


def plan_for(grap=1, hours=None):
    school = copy.deepcopy(DEMO_SCHOOL)
    school["grap_stage"] = grap
    return optimizer.build_plan(school, {"hours": hours or REPLAY["hours"], "source": "test"}, "2025-11-21", "replay")


def test_cedar_blocks_exertion_in_very_poor_air():
    r = rules.check("PE", 150, 1, "7A", 7)
    assert not r["allowed"] and r["rules"] == ["very_poor_exertion"]


def test_cedar_grap3_is_regulatory():
    r = rules.check("PE", 50, 3, "7A", 7)
    assert not r["allowed"] and r["regulatory"]


def test_cedar_asthma_cohort_is_stricter():
    assert rules.check("PE", 95, 1, "7A", 7)["allowed"]
    assert not rules.check("PE", 95, 1, "7A", 7, asthma_cohort=True)["allowed"]


def test_replay_moves_pe_to_cleaner_slots():
    plan = plan_for()
    moves = [c for c in plan["changes"] if c["type"] == "move"]
    assert len(moves) == 5
    assert all(c["pm25_to"] < c["pm25_from"] * 0.8 for c in moves)
    assert plan["metrics"]["reduction_pct"] > 30


def test_moves_respect_playground_capacity_and_teachers():
    plan = plan_for()
    after = plan["timetable_after"]
    for pid in [p["id"] for p in DEMO_SCHOOL["periods"] if p["kind"] == "teaching"]:
        cells = [tt[pid] for tt in after.values()]
        assert sum(c["subject"] == "PE" for c in cells) <= DEMO_SCHOOL["playground_capacity"]
        teachers = [c["teacher"] for c in cells]
        assert len(teachers) == len(set(teachers)), f"teacher clash in {pid}"


def test_grap3_sends_all_pe_indoors():
    plan = plan_for(grap=3)
    assert plan["regulatory"]
    assert plan["metrics"]["pe_indoor"] == 6 and plan["metrics"]["pe_moved"] == 0


def test_clean_day_is_quiet():
    clean = [{**h, "pm25": 25} for h in REPLAY["hours"]]
    plan = plan_for(hours=clean)
    assert plan["quiet"] and plan["changes"] == []


def test_notices_mention_every_moved_class():
    plan = plan_for()
    n = notices.build(plan, DEMO_SCHOOL)
    for c in plan["changes"]:
        if c["type"] == "move":
            assert c["class_id"] in n["parent_notice_en"] and c["class_id"] in n["parent_notice_hi"]


def call(method, path, body=None):
    out = api.handler({"rawPath": path, "requestContext": {"http": {"method": method}},
                       "body": json.dumps(body) if body else None})
    return out["statusCode"], json.loads(out["body"]) if out["body"] else None


@pytest.fixture()
def local_store(tmp_path, monkeypatch):
    from cleanhour import config, store
    monkeypatch.setattr(config, "LOCAL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "_backend", None)
    monkeypatch.setattr(forecast, "fetch", lambda lat, lon, date: REPLAY)


def test_api_plan_approve_publish_flow(local_store):
    status, body = call("GET", "/api/schools/demo-rohini/plans/2025-11-21")
    assert status == 200 and body["status"] == "none"
    status, body = call("POST", "/api/schools/demo-rohini/plans", {"when": "replay"})
    assert status == 202 and body["status"] == "pending_approval"
    status, body = call("GET", "/api/public/demo-rohini/latest")
    assert body["plan"] is None, "nothing reaches parents before approval"
    status, body = call("POST", "/api/schools/demo-rohini/plans/2025-11-21/approve", {"by": "test"})
    assert status == 200 and body["status"] == "published"
    status, body = call("GET", "/api/public/demo-rohini/latest")
    assert body["plan"]["metrics"]["pe_moved"] == 5
    status, body = call("POST", "/api/schools/demo-rohini/plans/2025-11-21/approve", {})
    assert status == 409


def test_heat_day_pulls_pe_earlier():
    heat = forecast._fixture("2025-04-08")
    school = copy.deepcopy(DEMO_SCHOOL)
    plan = optimizer.build_plan(school, heat, "2025-04-08", "replay")
    moves = [c for c in plan["changes"] if c["type"] == "move"]
    assert len(moves) == 1 and moves[0]["driver"] == "heat"
    assert moves[0]["class_id"] == "8A" and moves[0]["feels_to"] <= moves[0]["feels_from"] - 3
    assert plan["period_index"][moves[0]["to"]]["start"] < plan["period_index"][moves[0]["from"]]["start"]


def test_cedar_heat_rules():
    assert not rules.check("PE", 50, 0, "8A", 8, feels_like=38)["allowed"]
    assert rules.check("PE", 50, 0, "8A", 8, feels_like=33)["allowed"]
    assert not rules.check("Recess", 50, 0, "3A", 3, feels_like=36)["allowed"]
    assert rules.check("PE", 50, 0, "8A", 8)["allowed"], "unknown heat never blocks"


def test_onboarding_normalises_a_transcription():
    from cleanhour import onboard
    parsed = {
        "periods": [
            {"label": "Assembly", "start": "7:40", "end": "8:00", "kind": "assembly"},
            {"label": "I", "start": "8:00", "end": "8:40", "kind": "teaching"},
            {"label": "II", "start": "8:40", "end": "9:20", "kind": "teaching"},
            {"label": "Lunch", "start": "10:40", "end": "11:00", "kind": "recess"},
            {"label": "III", "start": "11:00", "end": "11:40", "kind": "teaching"},
            {"label": "IV", "start": "1:00", "end": "1:40", "kind": "teaching"},
        ],
        "classes": [{"name": "VI-B", "cells": [
            {"period_index": 1, "subject": "Games", "teacher": "Mr. Singh"},
            {"period_index": 2, "subject": "Maths", "teacher": "Ms. Rao"},
            {"period_index": 4, "subject": "Hindi", "teacher": ""},
        ]}],
    }
    school = onboard.to_school(parsed, "Test School", 28.6, 77.2)
    tt = school["classes"][0]["timetable"]
    assert tt["P1"]["subject"] == "PE"
    assert [p["start"] for p in school["periods"]][-1] == "13:00"
    assert set(tt) == {"P1", "P2", "P3", "P4"}
    plan = optimizer.build_plan(school, REPLAY, "2025-11-21", "replay")
    assert any(c["type"] == "move" for c in plan["changes"])
