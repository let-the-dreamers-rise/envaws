"""Staff authorization: Cognito identity + Cedar policies (authz.cedar)."""

import os
import re
from functools import lru_cache

import cedarpy

POLICY_FILE = os.path.join(os.path.dirname(__file__), "authz.cedar")
ROLES = ("principal", "teacher", "admin")

# Local development has no Cognito; these stand in for the demo accounts the deploy script creates.
DEMO_USERS = {
    "principal": {"sub": "demo-principal", "email": "principal@demo-rohini.cleanhour.in",
                  "name": "Mrs. Sharma (Principal)", "custom:role": "principal", "custom:school": "demo-rohini"},
    "teacher": {"sub": "demo-teacher", "email": "pe.teacher@demo-rohini.cleanhour.in",
                "name": "Mr. Rawat", "custom:role": "teacher", "custom:school": "demo-rohini"},
    "admin": {"sub": "demo-admin", "email": "district.admin@cleanhour.in",
              "name": "District admin", "custom:role": "admin", "custom:school": "*"},
}

REASONS = {
    "only_principals_approve": "Only the school's principal can approve what children do (Cedar staff policy).",
}


class Unauthorized(Exception):
    pass


class Forbidden(Exception):
    pass


@lru_cache(maxsize=1)
def _policies():
    with open(POLICY_FILE) as f:
        text = f.read()
    return text, re.findall(r'@id\("([^"]+)"\)', text)


def user_from_claims(claims: dict | None) -> dict:
    if not claims or not claims.get("sub"):
        raise Unauthorized("sign in required")
    role = claims.get("custom:role", "")
    if role not in ROLES:
        raise Forbidden("this account has no CleanHour role")
    return {"id": claims["sub"], "email": claims.get("email", ""), "name": claims.get("name") or claims.get("email", ""),
            "role": role, "school": claims.get("custom:school", "")}


def check(user: dict, action: str, school_id: str) -> dict:
    text, ids = _policies()
    entities = [
        {"uid": {"__entity": {"type": "Role", "id": r}}, "attrs": {}, "parents": []} for r in ROLES
    ] + [
        {"uid": {"__entity": {"type": "User", "id": user["id"]}}, "attrs": {"school": user["school"]},
         "parents": [{"__entity": {"type": "Role", "id": user["role"]}}]},
        {"uid": {"__entity": {"type": "School", "id": school_id}}, "attrs": {"school": school_id}, "parents": []},
    ]
    result = cedarpy.is_authorized({
        "principal": f'User::"{user["id"]}"', "action": f'Action::"{action}"',
        "resource": f'School::"{school_id}"', "context": {},
    }, text, entities)
    if result.diagnostics.errors:
        raise RuntimeError(f"cedar evaluation error: {result.diagnostics.errors}")
    reasons = [ids[int(r.removeprefix("policy"))] for r in result.diagnostics.reasons]
    return {"allowed": result.allowed, "policies": reasons}


def require(user: dict, action: str, school_id: str) -> None:
    decision = check(user, action, school_id)
    if not decision["allowed"]:
        why = next((REASONS[p] for p in decision["policies"] if p in REASONS),
                   f"Your role ({user['role']}) can't {action} for this school (Cedar staff policy).")
        raise Forbidden(why)


def allowed_actions(user: dict, school_id: str) -> list[str]:
    return [a for a in ("ViewPlan", "RunPlan", "Approve", "SetGrap", "Ask", "CreateSchool")
            if check(user, a, school_id)["allowed"]]
