"""Step Functions task handlers and the EventBridge Scheduler entry point.

DailyPlan state machine: Plan -> IsQuiet? -> WaitForApproval (task token, times out at the approval
deadline) -> Publish. On timeout, only changes required by GRAP are auto-published.

Every run records its impact as CloudWatch metrics (Powertools for AWS Lambda, embedded metric format),
so "PE periods rescued" and "dose avoided" are numbers on a dashboard, not claims in a pitch."""

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit

from . import service, store

logger = Logger(service="cleanhour")
metrics = Metrics(namespace="CleanHour", service="cleanhour")


def _record_impact(plan: dict) -> None:
    m = plan["metrics"]
    metrics.add_metric(name="PlansMade", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="PEPeriodsMoved", unit=MetricUnit.Count, value=m["pe_moved"])
    metrics.add_metric(name="PEPeriodsIndoor", unit=MetricUnit.Count, value=m["pe_indoor"])
    metrics.add_metric(name="HeatMoves", unit=MetricUnit.Count, value=m.get("heat_moves", 0))
    metrics.add_metric(name="AsthmaKidsKeptIn", unit=MetricUnit.Count, value=m["asthma_kids_indoor"])
    metrics.add_metric(name="DoseReductionPercent", unit=MetricUnit.Percent, value=m["reduction_pct"])
    metrics.add_metric(name="DoseAvoidedMg", unit=MetricUnit.Count,
                       value=round(max(0.0, m["dose_before_mg"] - m["dose_after_mg"]), 1))


@metrics.log_metrics
def plan_task(event, context=None):
    plan = service.compute_plan(event["school_id"], event["date"], event["mode"], run_id=event["run_id"])
    _record_impact(plan)
    logger.info("plan ready", extra={"school": event["school_id"], "date": event["date"],
                                     "changes": len(plan["changes"]), "metrics": plan["metrics"],
                                     "notices": plan["notices"]["source"]})
    try:
        service.notify_principal(event["school_id"], event["date"], plan)
    except Exception as e:  # a failed email must not block the plan
        logger.exception("principal notification failed")
        store.audit(event["school_id"], "notify_failed", str(e)[:200])
    return {**event, "quiet": plan["quiet"]}


def wait_task(event, context=None):
    service.register_token(event["school_id"], event["date"], event["run_id"], event["task_token"])
    return {"ok": True}


@metrics.log_metrics
def publish_task(event, context=None):
    by = (event.get("approval") or {}).get("approved_by")
    if event.get("quiet"):
        by = "auto: normal day, nothing to change"
    view = service.publish(event["school_id"], event["date"], auto=bool(event.get("auto")), by=by,
                           run_id=event["run_id"])
    if view.get("status") == "published":
        metrics.add_metric(name="PlansPublished", unit=MetricUnit.Count, value=1)
        if event.get("auto"):
            metrics.add_metric(name="AutoPublishedForGRAP", unit=MetricUnit.Count, value=1)
    elif view.get("status") == "expired":
        metrics.add_metric(name="PlansExpired", unit=MetricUnit.Count, value=1)
    logger.info("publish step", extra={"school": event["school_id"], "status": view.get("status")})
    return {"ok": True}


def scheduled(event, context=None):
    """Fired at 05:30 IST: plan today for every school."""
    started = []
    for s in store.list_schools() or [service.school("demo-rohini")]:
        started.append(service.request_plan(s["id"], "today"))
    logger.info("morning run started", extra={"schools": len(started)})
    return {"started": started}


@metrics.log_metrics
def midday_recheck(event, context=None):
    """Fired at 09:30 and 11:30 IST: re-check the rest of today for every school with a published plan."""
    date = service.today_ist()
    for s in store.list_schools():
        try:
            result = service.recheck(s["id"], date)
        except Exception:
            logger.exception("recheck failed", extra={"school": s["id"]})
            continue
        if result.get("tightened"):
            metrics.add_metric(name="PEPeriodsTightenedMidday", unit=MetricUnit.Count, value=len(result["tightened"]))
    return {"ok": True}
