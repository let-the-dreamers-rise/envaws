"""Cedar policy checks for outdoor activities (via cedarpy, the Python bindings for Cedar)."""

import os
import re
from functools import lru_cache

import cedarpy

POLICY_FILE = os.path.join(os.path.dirname(__file__), "policies.cedar")

ACTIVITIES = {
    "PE": {"exertion": "high", "kind": "pe"},
    "Recess": {"exertion": "moderate", "kind": "recess"},
    "Assembly": {"exertion": "low", "kind": "assembly"},
}

RULE_TEXT = {
    "grap4_all_outdoor": ("GRAP Stage IV in force: no outdoor activity",
                          "GRAP चरण 4 लागू: कोई बाहरी गतिविधि नहीं"),
    "grap3_outdoor_sports": ("GRAP Stage III in force: outdoor sports suspended",
                             "GRAP चरण 3 लागू: बाहरी खेल बंद"),
    "severe_air": ("Severe air (PM2.5 above 250): everyone stays indoors",
                   "गंभीर प्रदूषण (PM2.5 250 से ऊपर): सभी अंदर रहेंगे"),
    "very_poor_exertion": ("Very Poor air (PM2.5 above 120): no outdoor exertion",
                           "बहुत खराब हवा (PM2.5 120 से ऊपर): बाहर दौड़-भाग नहीं"),
    "very_poor_primary": ("Very Poor air: classes 1-5 stay indoors",
                          "बहुत खराब हवा: कक्षा 1-5 अंदर रहेंगी"),
    "poor_morning_assembly": ("Poor air at assembly time (PM2.5 above 90): assembly held indoors",
                              "प्रार्थना सभा के समय खराब हवा: सभा अंदर होगी"),
    "poor_asthma_watch": ("Poor air (PM2.5 above 90): asthma-watch students stay indoors",
                          "खराब हवा: अस्थमा वाले बच्चे अंदर रहेंगे"),
}

REGULATORY = {"grap4_all_outdoor", "grap3_outdoor_sports"}


@lru_cache(maxsize=1)
def _policies() -> tuple[str, list[str]]:
    with open(POLICY_FILE) as f:
        text = f.read()
    # cedarpy reports reasons as policy0, policy1, ... in file order; map them back to @id names.
    ids = re.findall(r'@id\("([^"]+)"\)', text)
    return text, ids


def _entities(class_id: str | None, grade: int | None, cohort: bool) -> list[dict]:
    groups = [{"uid": {"__entity": {"type": "Group", "id": g}}, "attrs": {}, "parents": []}
              for g in ("primary", "secondary", "asthma_watch", "school")]
    acts = [{"uid": {"__entity": {"type": "Activity", "id": name}}, "attrs": attrs, "parents": []}
            for name, attrs in ACTIVITIES.items()]
    if class_id is None:
        principal = {"uid": {"__entity": {"type": "School", "id": "all"}}, "attrs": {},
                     "parents": [{"__entity": {"type": "Group", "id": "school"}}]}
    else:
        group = "primary" if grade is not None and grade <= 5 else "secondary"
        parents = [{"__entity": {"type": "Group", "id": group}}]
        if cohort:
            parents.append({"__entity": {"type": "Group", "id": "asthma_watch"}})
        principal = {"uid": {"__entity": {"type": "Cohort" if cohort else "Class", "id": class_id}},
                     "attrs": {}, "parents": parents}
    return groups + acts + [principal]


def check(activity: str, pm25: float, grap_stage: int, class_id: str | None = None,
          grade: int | None = None, asthma_cohort: bool = False) -> dict:
    """Can this group do this activity outdoors at this PM2.5? Returns decision + rule ids."""
    text, ids = _policies()
    if class_id is None:
        principal = 'School::"all"'
    else:
        principal = f'{"Cohort" if asthma_cohort else "Class"}::"{class_id}"'
    request = {
        "principal": principal,
        "action": 'Action::"ScheduleOutdoor"',
        "resource": f'Activity::"{activity}"',
        "context": {"pm25": int(round(pm25)), "grap_stage": int(grap_stage)},
    }
    result = cedarpy.is_authorized(request, text, _entities(class_id, grade, asthma_cohort))
    if result.diagnostics.errors:
        raise RuntimeError(f"cedar evaluation error: {result.diagnostics.errors}")
    indexes = sorted(int(r.removeprefix("policy")) for r in result.diagnostics.reasons)
    forbids = [ids[i] for i in indexes if ids[i] != "default_allow"]
    return {"allowed": result.allowed, "rules": forbids,
            "regulatory": any(r in REGULATORY for r in forbids)}


def explain(rule_id: str, lang: str = "en") -> str:
    en, hi = RULE_TEXT.get(rule_id, (rule_id, rule_id))
    return hi if lang == "hi" else en
