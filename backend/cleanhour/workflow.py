"""Step Functions task handlers and the EventBridge Scheduler entry point.

DailyPlan state machine: Plan -> WaitForApproval (task token, times out at the approval
deadline) -> Publish. On timeout, only changes required by GRAP are auto-published."""

from . import service, store


def plan_task(event, context=None):
    service.compute_plan(event["school_id"], event["date"], event["mode"], run_id=event["run_id"])
    return event


def wait_task(event, context=None):
    service.register_token(event["school_id"], event["date"], event["run_id"], event["task_token"])
    return {"ok": True}


def publish_task(event, context=None):
    service.publish(event["school_id"], event["date"], auto=bool(event.get("auto")),
                    by=(event.get("approval") or {}).get("approved_by"), run_id=event["run_id"])
    return {"ok": True}


def scheduled(event, context=None):
    """Fired at 05:30 IST: plan today for every school."""
    started = []
    for s in store.list_schools() or [service.school("demo-rohini")]:
        started.append(service.request_plan(s["id"], "today"))
    return {"started": started}
