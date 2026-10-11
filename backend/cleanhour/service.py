"""Use cases: plan a day, approve, publish, set GRAP stage, ask, and the parent view."""

import copy
import json
import uuid
from datetime import datetime, timedelta, timezone

from . import agent, config, notices, optimizer, rules, store, voice
from . import forecast as fc
from .school import DEMO_SCHOOL

IST = timezone(timedelta(hours=5, minutes=30))
REPLAY_DATE = "2025-11-21"


class Conflict(Exception):
    pass


class NotFound(Exception):
    pass


def today_ist() -> str:
    return datetime.now(IST).date().isoformat()


HEAT_REPLAY_DATE = "2025-04-08"


def resolve(when: str) -> tuple[str, str]:
    if when == "replay":
        return REPLAY_DATE, "replay"
    if when in (REPLAY_DATE, HEAT_REPLAY_DATE):
        return when, "replay"
    if when == "tomorrow":
        return (datetime.now(IST).date() + timedelta(days=1)).isoformat(), "live"
    if when == "today":
        return today_ist(), "live"
    datetime.strptime(when, "%Y-%m-%d")
    return when, "live"


def school(sid: str) -> dict:
    s = store.get_school(sid)
    if s is None and sid == DEMO_SCHOOL["id"]:
        s = copy.deepcopy(DEMO_SCHOOL)
        store.put_school(s)
    if s is None:
        raise NotFound(f"school {sid}")
    return s


def set_grap(sid: str, stage: int) -> dict:
    if stage not in range(0, 5):
        raise ValueError("GRAP stage must be 0-4")
    s = school(sid)
    s["grap_stage"] = stage
    store.put_school(s)
    store.audit(sid, "grap_stage_set", f"GRAP stage set to {stage}")
    return s


def compute_plan(sid: str, date: str, mode: str, run_id: str | None = None) -> dict:
    s = school(sid)
    forecast = fc.fetch(s["lat"], s["lon"], date)
    plan = optimizer.build_plan(s, forecast, date, mode)
    plan["run_id"] = run_id or uuid.uuid4().hex[:12]
    plan["rule_text"] = {r: list(t) for r, t in rules.RULE_TEXT.items()}
    template = notices.build(plan, s)
    plan["notices_template"] = template
    plan["notices"] = template
    if agent.enabled():
        try:
            plan["notices"] = agent.write_notices(plan, s, template)
        except agent.AgentUnavailable as e:
            plan["notices"] = {**template, "agent_error": str(e)[:300]}
    else:
        plan["notices"] = {**template, "agent_error": "Bedrock not configured (template used)"}
    store.put_plan_item(sid, date, plan, status="pending_approval", run_id=plan["run_id"],
                        task_token=None, voice_key=None)
    store.audit(sid, "plan_ready", f"{date} ({mode}): {len(plan['changes'])} changes, "
                                   f"-{plan['metrics']['reduction_pct']}% PM2.5 dose; notices via {plan['notices']['source']}")
    return plan


def request_plan(sid: str, when: str) -> dict:
    date, mode = resolve(when)
    school(sid)
    if not config.STATE_MACHINE_ARN:
        plan = compute_plan(sid, date, mode)
        if plan["quiet"]:
            publish(sid, date, by="auto: normal day, nothing to change")
        return plan_view(sid, date)
    import boto3
    sfn = boto3.client("stepfunctions")
    previous = store.get_plan_item(sid, date)
    if previous and previous.get("execution_arn") and previous.get("status") in ("planning", "pending_approval"):
        try:
            sfn.stop_execution(executionArn=previous["execution_arn"], cause="superseded by a new plan")
        except Exception:
            pass
    run_id = uuid.uuid4().hex[:12]
    execution = sfn.start_execution(
        stateMachineArn=config.STATE_MACHINE_ARN, name=f"{sid}-{date}-{run_id}",
        input=json.dumps({"school_id": sid, "date": date, "mode": mode, "run_id": run_id}))
    store.put_plan_item(sid, date, status="planning", run_id=run_id, execution_arn=execution["executionArn"],
                        task_token=None)
    store.audit(sid, "plan_requested", f"{date} ({mode}) via Step Functions")
    return {"status": "planning", "date": date, "run_id": run_id}


def notify_principal(sid: str, date: str, plan: dict) -> bool:
    """Email the principal (SNS topic subscription) that today's plan is ready."""
    if not config.TOPIC_ARN:
        return False
    s = school(sid)
    f = plan["flag"]
    if plan["quiet"]:
        subject = f"CleanHour: {f['en']} air on {date} - normal timetable, nothing to approve"
    else:
        n = len(plan["changes"])
        subject = f"CleanHour: {f['en']} air on {date} - {n} change{'s' if n != 1 else ''} need your approval"
    link = f"{config.SITE_URL}/console.html?school={sid}&date={date}" if config.SITE_URL else "(open the CleanHour console)"
    lines = [f"Good morning. CleanHour's plan for {s['name']}, {date}:", ""]
    lines += [f"- {b}" for b in plan["notices"]["principal_brief_en"]]
    if not plan["quiet"]:
        lines += ["", f"Review and approve: {link}"]
        if plan["regulatory"]:
            lines += ["Changes required by GRAP apply automatically at the deadline if you don't respond."]
        else:
            lines += ["Nothing goes to parents until you approve."]
    import boto3
    boto3.client("sns").publish(TopicArn=config.TOPIC_ARN, Subject=subject[:99], Message="\n".join(lines))
    store.audit(sid, "principal_notified", subject)
    return True


def register_token(sid: str, date: str, run_id: str, token: str):
    item = store.get_plan_item(sid, date)
    if not item or item.get("run_id") != run_id:
        return
    store.put_plan_item(sid, date, task_token=token)


def approve(sid: str, date: str, by: str = "principal") -> dict:
    item = store.get_plan_item(sid, date)
    if not item or "plan" not in item:
        raise NotFound(f"no plan for {date}")
    if item["status"] != "pending_approval":
        raise Conflict(f"plan is {item['status']}")
    if config.STATE_MACHINE_ARN:
        if not item.get("task_token"):
            raise Conflict("workflow is still starting, retry in a second")
        import boto3
        boto3.client("stepfunctions").send_task_success(
            taskToken=item["task_token"], output=json.dumps({"approved_by": by}))
        store.put_plan_item(sid, date, status="approved", approved_by=by)
        store.audit(sid, "approved", f"{date} by {by}")
        return plan_view(sid, date)
    store.audit(sid, "approved", f"{date} by {by}")
    return publish(sid, date, by=by)


def publish(sid: str, date: str, auto: bool = False, by: str | None = None, run_id: str | None = None) -> dict:
    item = store.get_plan_item(sid, date)
    if not item or "plan" not in item:
        raise NotFound(f"no plan for {date}")
    if run_id and item.get("run_id") != run_id:
        return plan_view(sid, date)  # superseded plan; nothing to publish
    plan = item["plan"]
    if auto and not plan["regulatory"]:
        store.put_plan_item(sid, date, status="expired")
        store.audit(sid, "expired", f"{date}: not approved in time; advisory changes not applied")
        return plan_view(sid, date)
    key = None
    try:
        key = voice.synthesize(plan["notices"]["voice_script_hi"], f"voice/{sid}/{date}-{plan['run_id']}.mp3")
    except Exception as e:
        store.audit(sid, "voice_failed", str(e)[:200])
    store.put_plan_item(sid, date, status="published", voice_key=key,
                        approved_by=by or ("auto: GRAP rules" if auto else item.get("approved_by")),
                        published_at=store.now())
    store.audit(sid, "published", f"{date}{' (auto, regulatory)' if auto else ''}")
    return plan_view(sid, date)


def plan_view(sid: str, date: str) -> dict:
    item = store.get_plan_item(sid, date)
    if not item:
        raise NotFound(f"no plan for {date}")
    return {"status": item.get("status"), "date": date, "run_id": item.get("run_id"),
            "approved_by": item.get("approved_by"), "published_at": item.get("published_at"),
            "has_voice": bool(item.get("voice_key")), "plan": item.get("plan")}


def ask(sid: str, date: str, question: str) -> dict:
    item = store.get_plan_item(sid, date)
    if not item or "plan" not in item:
        raise NotFound(f"no plan for {date}")
    if not agent.enabled():
        return {"answer": None, "error": "The CleanHour agent needs Amazon Bedrock, which is not configured here."}
    try:
        answer = agent.ask(question, item["plan"], school(sid))
    except agent.AgentUnavailable as e:
        return {"answer": None, "error": f"Agent unavailable: {str(e)[:200]}"}
    store.audit(sid, "question", question[:200])
    return {"answer": answer}


def voice_url(sid: str, date: str) -> str:
    item = store.get_plan_item(sid, date)
    if not item or not item.get("voice_key"):
        raise NotFound("no voice note")
    return voice.url(item["voice_key"])


def public_latest(sid: str, date: str | None = None) -> dict:
    s = school(sid)
    items = [store.get_plan_item(sid, date)] if date else store.list_plan_items(sid)
    published = [i for i in items if i and i.get("status") == "published"]
    if not published:
        return {"school": {"id": s["id"], "name": s["name"], "name_hi": s.get("name_hi")}, "plan": None}
    latest = max(published, key=lambda i: i.get("published_at", ""))
    plan = json.loads(latest["data"])
    return {
        "school": {"id": s["id"], "name": s["name"], "name_hi": s.get("name_hi")},
        "date": plan["date"], "mode": plan["mode"], "published_at": latest.get("published_at"),
        "has_voice": bool(latest.get("voice_key")),
        "plan": {**{k: plan[k] for k in ("flag", "periods", "changes", "metrics", "timetable_after",
                                        "period_index", "grap_stage", "quiet", "rule_text")},
                 "heat": plan.get("heat")},
        "notices": {k: plan["notices"][k] for k in ("parent_notice_en", "parent_notice_hi")},
    }
