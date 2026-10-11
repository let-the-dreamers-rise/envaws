"""Lambda handler for the HTTP API (payload format 2.0). Also used by the local dev server.

Routes under /api/public and /api/health are open (parents, health checks). Everything else needs a
Cognito ID token (checked by the API Gateway JWT authorizer) and passes the Cedar staff policies."""

import json
import re
import traceback

from . import authz, config, service, store

HEADERS = {"content-type": "application/json", "access-control-allow-origin": "*",
           "access-control-allow-headers": "content-type,authorization,x-demo-user",
           "access-control-allow-methods": "GET,POST,OPTIONS"}


def _resp(status, body):
    return {"statusCode": status, "headers": HEADERS, "body": json.dumps(body, ensure_ascii=False)}


def _body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        raw = base64.b64decode(raw).decode()
    return json.loads(raw)


def _user(event) -> dict:
    claims = (event.get("requestContext", {}).get("authorizer") or {}).get("jwt", {}).get("claims")
    if claims is None and not config.running_in_aws():
        # Local dev server: act as a demo account (x-demo-user: principal | teacher | admin).
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        claims = authz.DEMO_USERS.get(headers.get("x-demo-user", "principal"))
    return authz.user_from_claims(claims)


ROUTES = []


def route(method, pattern, action=None):
    """action=None: public route. Otherwise the Cedar staff action required on the school."""
    def wrap(fn):
        ROUTES.append((method, re.compile(f"^{pattern}$"), fn, action))
        return fn
    return wrap


@route("GET", r"/api/health")
def health(event):
    return 200, {"ok": True}


@route("GET", r"/api/me", action="Me")
def me(event, user):
    school = user["school"] if user["school"] != "*" else "demo-rohini"
    return 200, {**user, "home_school": school, "can": authz.allowed_actions(user, school)}


@route("POST", r"/api/schools", action="CreateSchool")
def create_school(event, user):
    b = _body(event)
    return 201, service.create_school_from_photo(b.get("name", ""), float(b["lat"]), float(b["lon"]),
                                                 b["image_base64"], b.get("image_format", "jpeg"))


@route("GET", r"/api/schools/(?P<sid>[\w-]+)", action="ViewPlan")
def get_school(event, user, sid):
    return 200, service.school(sid)


@route("POST", r"/api/schools/(?P<sid>[\w-]+)/grap", action="SetGrap")
def set_grap(event, user, sid):
    return 200, service.set_grap(sid, int(_body(event)["stage"]), by=user["name"])


@route("POST", r"/api/schools/(?P<sid>[\w-]+)/plans", action="RunPlan")
def create_plan(event, user, sid):
    return 202, service.request_plan(sid, _body(event).get("when", "today"))


@route("GET", r"/api/schools/(?P<sid>[\w-]+)/plans/(?P<date>\d{4}-\d{2}-\d{2})", action="ViewPlan")
def get_plan(event, user, sid, date):
    try:
        return 200, service.plan_view(sid, date)
    except service.NotFound:
        return 200, {"status": "none", "date": date, "plan": None}


@route("POST", r"/api/schools/(?P<sid>[\w-]+)/plans/(?P<date>\d{4}-\d{2}-\d{2})/approve", action="Approve")
def approve(event, user, sid, date):
    return 200, service.approve(sid, date, user["name"])


@route("POST", r"/api/schools/(?P<sid>[\w-]+)/plans/(?P<date>\d{4}-\d{2}-\d{2})/ask", action="Ask")
def ask(event, user, sid, date):
    question = (_body(event).get("question") or "").strip()
    if not question:
        return 400, {"error": "question is required"}
    return 200, service.ask(sid, date, question[:500], speak=bool(_body(event).get("speak")))


@route("POST", r"/api/schools/(?P<sid>[\w-]+)/plans/(?P<date>\d{4}-\d{2}-\d{2})/recheck", action="RunPlan")
def recheck(event, user, sid, date):
    return 200, service.recheck(sid, date, _body(event).get("at"))


@route("GET", r"/api/schools/(?P<sid>[\w-]+)/audit", action="ViewPlan")
def audit(event, user, sid):
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
    for m, pattern, fn, action in ROUTES:
        match = pattern.match(path)
        if not match or m != method:
            continue
        try:
            args = match.groupdict()
            if action is not None:
                user = _user(event)
                if action not in ("Me", "CreateSchool"):
                    authz.require(user, action, args["sid"])
                elif action == "CreateSchool":
                    authz.require(user, action, "new")
                status, body = fn(event, user, **args)
            else:
                status, body = fn(event, **args)
            if status == 302:
                return {"statusCode": 302, "headers": {**HEADERS, "location": body["location"]}, "body": ""}
            return _resp(status, body)
        except authz.Unauthorized as e:
            return _resp(401, {"error": str(e)})
        except authz.Forbidden as e:
            return _resp(403, {"error": str(e)})
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
