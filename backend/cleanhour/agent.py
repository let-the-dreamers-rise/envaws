"""Strands Agents on Amazon Bedrock. The model writes words and answers questions; it can read
the plan and run Cedar checks through tools, but it has no tool that changes the timetable."""

import json

from pydantic import BaseModel, Field

from . import config, rules
from . import forecast as fc

NOTICE_PROMPT = """You are CleanHour, the air-safety duty officer for an Indian school.
You rewrite a factual day plan into messages for the principal and for parents.
Rules:
- Use ONLY the facts given. Keep every class name, time and number exactly as given. Add no new facts,
  no medical advice beyond what is given, and no promises.
- Parents read these on WhatsApp on a phone: short lines starting with "• ", warm and calm, under 90 words.
- Hindi must be simple everyday Hindi in Devanagari that any parent understands (e.g. "खेल का पीरियड",
  "प्रार्थना सभा"), not formal or Sanskritised.
- The voice script is spoken Hindi for a 30-40 second voice note: no bullets, no symbols, numbers
  and times written the way they are spoken (e.g. "दोपहर एक बजकर पाँच मिनट").
- The principal brief is 3-5 short English lines with the numbers that matter."""

QA_PROMPT = """You are CleanHour, the air-safety duty officer for an Indian school, answering the
principal or a teacher. Answer in the language and script of the question (Hindi, Hinglish or English).
Always use the tools for numbers and rule checks; never guess. You cannot change the timetable; if asked
to, explain what the check says and that the principal can adjust it. Keep answers to 2-4 sentences."""


class Notices(BaseModel):
    principal_brief_en: list[str] = Field(description="3-5 short English lines for the principal")
    parent_notice_en: str = Field(description="English WhatsApp notice for parents, bullet lines")
    parent_notice_hi: str = Field(description="Hindi (Devanagari) WhatsApp notice for parents, bullet lines")
    voice_script_hi: str = Field(description="Spoken Hindi script for a 30-40 second voice note")


class AgentUnavailable(Exception):
    pass


def enabled() -> bool:
    if config.LLM_MODE == "off":
        return False
    import boto3
    return boto3.Session().get_credentials() is not None


def _model():
    from strands.models import BedrockModel
    return BedrockModel(model_id=config.MODEL_ID, region_name=config.BEDROCK_REGION,
                        temperature=0.2, max_tokens=1500)


def _facts(plan: dict, school: dict, template: dict) -> str:
    changes = [{k: v for k, v in c.items() if k not in ("skipped", "alternative")} for c in plan["changes"]]
    return json.dumps({
        "school": school["name"], "school_hi": school.get("name_hi"), "date": plan["date"],
        "grap_stage": plan["grap_stage"], "flag": plan["flag"], "metrics": plan["metrics"],
        "periods": {pid: f"{p['start']}-{p['end']}" for pid, p in plan["period_index"].items()},
        "changes": changes,
        "rule_meanings": {r: rules.explain(r) for c in plan["changes"] for r in c["rules"]},
        "reference_notice_en": template["parent_notice_en"],
        "reference_notice_hi": template["parent_notice_hi"],
    }, ensure_ascii=False)


def write_notices(plan: dict, school: dict, template: dict) -> dict:
    from strands import Agent
    try:
        agent = Agent(model=_model(), system_prompt=NOTICE_PROMPT, callback_handler=None)
        result = agent("Write today's messages from these facts:\n" + _facts(plan, school, template),
                       structured_output_model=Notices)
        out = result.structured_output.model_dump()
    except Exception as e:
        raise AgentUnavailable(str(e)) from e
    out["source"] = "bedrock"
    return out


def ask(question: str, plan: dict, school: dict) -> str:
    from strands import Agent, tool

    classes = {c["id"]: c for c in school["classes"]}
    hours = plan["forecast"]["hours"]

    @tool
    def get_day_plan() -> dict:
        """Today's CleanHour plan: air flag, every timetable change with the rule that caused it, and impact metrics."""
        return {"date": plan["date"], "grap_stage": plan["grap_stage"], "flag": plan["flag"],
                "metrics": plan["metrics"], "periods": plan["period_index"],
                "changes": [{k: v for k, v in c.items() if k != "skipped"} for c in plan["changes"]],
                "rule_meanings": {r: rules.explain(r) for c in plan["changes"] for r in c["rules"]}}

    @tool
    def get_air_by_period() -> list:
        """Forecast PM2.5 (µg/m³) and India NAQI band for every period of the school day."""
        return [{"period": p["id"], "label": p["label"], "start": p["start"], "end": p["end"],
                 "pm25": p["pm25"], "band": p["band"]["en"]} for p in plan["periods"]]

    @tool
    def check_outdoor(class_id: str, start_time: str, activity: str = "PE", minutes: int = 40) -> dict:
        """Check the school's Cedar rules: can this class do this activity outdoors starting at start_time?

        Args:
            class_id: class such as "6A"
            start_time: 24-hour time "HH:MM", for example "13:05"
            activity: "PE", "Recess" or "Assembly"
            minutes: how long the activity lasts
        """
        if class_id not in classes:
            return {"error": f"unknown class {class_id}; classes are {sorted(classes)}"}
        if activity not in rules.ACTIVITIES:
            return {"error": f"activity must be one of {sorted(rules.ACTIVITIES)}"}
        h, m = map(int, start_time.split(":"))
        end = h * 60 + m + int(minutes)
        pm25 = fc.period_average(hours, start_time, f"{end // 60:02d}:{end % 60:02d}")
        c = classes[class_id]
        whole = rules.check(activity, pm25, plan["grap_stage"], class_id, c["grade"])
        asthma = rules.check(activity, pm25, plan["grap_stage"], class_id, c["grade"], asthma_cohort=True)
        return {"class": class_id, "activity": activity, "pm25": round(pm25),
                "allowed_for_class": whole["allowed"],
                "blocked_by": {r: rules.explain(r) for r in whole["rules"]},
                "allowed_for_asthma_watch": asthma["allowed"],
                "asthma_watch_blocked_by": {r: rules.explain(r) for r in asthma["rules"]}}

    try:
        agent = Agent(model=_model(), system_prompt=QA_PROMPT, callback_handler=None,
                      tools=[get_day_plan, get_air_by_period, check_outdoor])
        return str(agent(question)).strip()
    except Exception as e:
        raise AgentUnavailable(str(e)) from e
