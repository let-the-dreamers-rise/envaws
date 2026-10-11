"""Lambda handler for the HTTP API (payload format 2.0). Also used by the local dev server."""

import json
import re
import traceback

from . import service, store

HEADERS = {"content-type": "application/json", "access-control-allow-origin": "*",
           "access-control-allow-headers": "content-type", "access-control-allow-methods": "GET,POST,OPTIONS"}


def _resp(status, body):
    return {"statusCode": status, "headers": HEADERS, "body": json.dumps(body, ensure_ascii=False)}


def _body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        raw = base64.b64decode(raw).decode()
    return json.loads(raw)


ROUTES = []


def route(method, pattern):
    def wrap(fn):
        ROUTES.append((method, re.compile(f"^{pattern}$"), fn))
        return fn
    return wrap


@route("GET", r"/api/health")
def health(event):
    return 200, {"ok": True}


@route("GET", r"/api/schools/(?P<sid>[\w-]+)")
def get_school(event, sid):
    return 200, service.school(sid)


@route("POST", r"/api/schools/(?P<sid>[\w-]+)/grap")
def set_grap(event, sid):
    return 200, service.set_grap(sid, int(_body(event)["stage"]))


@route("POST", r"/api/schools/(?P<sid>[\w-]+)/plans")
def create_plan(event, sid):
    return 202, service.request_plan(sid, _body(event).get("when", "today"))


@route("GET", r"/api/schools/(?P<sid>[\w-]+)/plans/(?P<date>\d{4}-\d{2}-\d{2})")
def get_plan(event, sid, date):
    try:
        return 200, service.plan_view(sid, date)
    except service.NotFound:
        return 200, {"status": "none", "date": date, "plan": None}


@route("POST", r"/api/schools/(?P<sid>[\w-]+)/plans/(?P<date>\d{4}-\d{2}-\d{2})/approve")
def approve(event, sid, date):
    return 200, service.approve(sid, date, _body(event).get("by", "principal"))


@route("POST", r"/api/schools/(?P<sid>[\w-]+)/plans/(?P<date>\d{4}-\d{2}-\d{2})/ask")
def ask(event, sid, date):
    question = (_body(event).get("question") or "").strip()
    if not question:
        return 400, {"error": "question is required"}
    return 200, service.ask(sid, date, question[:500])


@route("GET", r"/api/schools/(?P<sid>[\w-]+)/audit")
def audit(event, sid):
    return 200, store.list_audit(sid)


@route("GET", r"/api/public/(?P<sid>[\w-]+)/latest")
def public_latest(event, sid):
    return 200, service.public_latest(sid, (event.get("queryStringParameters") or {}).get("date"))


@route("GET", r"/api/public/(?P<sid>[\w-]+)/voice/(?P<date>\d{4}-\d{2}-\d{2})")
def public_voice(event, sid, date):
    return 302, {"location": service.voice_url(sid, date)}


def handler(event, context=None):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": HEADERS, "body": ""}
    for m, pattern, fn in ROUTES:
        match = pattern.match(path)
        if match and m == method:
            try:
                status, body = fn(event, **match.groupdict())
                if status == 302:
                    return {"statusCode": 302, "headers": {**HEADERS, "location": body["location"]}, "body": ""}
                return _resp(status, body)
            except service.NotFound as e:
                return _resp(404, {"error": str(e)})
            except service.Conflict as e:
                return _resp(409, {"error": str(e)})
            except (ValueError, KeyError) as e:
                return _resp(400, {"error": f"bad request: {e}"})
            except Exception as e:
                traceback.print_exc()
                return _resp(500, {"error": f"{type(e).__name__}: {e}"})
    return _resp(404, {"error": f"no route for {method} {path}"})
