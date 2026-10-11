"""Onboarding: a photo of the school's timetable becomes a CleanHour school via a multimodal
Strands agent on Bedrock. The model only transcribes; normalisation and validation are code."""

import re
import uuid
from typing import Literal

from pydantic import BaseModel, Field

PE_PATTERN = re.compile(r"\b(p\.?\s?e\.?|p\.?\s?t\.?|physical|games|sports?|khel|yoga|drill)\b", re.I)

EXTRACT_PROMPT = """This is a photo of an Indian school's class timetable for one day (or a week; then use the
first weekday). Transcribe it exactly. Periods: give every row/column of the day in order with 24-hour
start/end times; mark morning assembly as kind "assembly", lunch/recess/break as "recess", lessons as
"teaching". Classes: one entry per class/section (e.g. "6A"), with the subject and teacher for each teaching
period id. If a teacher is not shown, write "". Do not invent periods, classes or times that are not in the image."""


class PeriodIn(BaseModel):
    label: str = Field(description='Name as written, e.g. "Period 1", "Assembly", "Lunch"')
    start: str = Field(description="24-hour HH:MM")
    end: str = Field(description="24-hour HH:MM")
    kind: Literal["assembly", "teaching", "recess"]


class CellIn(BaseModel):
    period_index: int = Field(description="0-based index into periods")
    subject: str
    teacher: str = ""


class ClassIn(BaseModel):
    name: str = Field(description='Class and section, e.g. "6A"')
    cells: list[CellIn]


class TimetableIn(BaseModel):
    periods: list[PeriodIn]
    classes: list[ClassIn]


class OnboardingError(Exception):
    pass


def extract(image: bytes, fmt: str) -> dict:
    from strands import Agent

    from .agent import AgentUnavailable, _model
    try:
        agent = Agent(model=_model(), callback_handler=None)
        result = agent([{"text": EXTRACT_PROMPT}, {"image": {"format": fmt, "source": {"bytes": image}}}],
                       structured_output_model=TimetableIn)
        return result.structured_output.model_dump()
    except Exception as e:
        raise AgentUnavailable(str(e)) from e


def _hhmm(value: str) -> str:
    m = re.match(r"^\s*(\d{1,2})[:.](\d{2})", value or "")
    if not m:
        raise OnboardingError(f"unreadable time {value!r}")
    h, mi = int(m.group(1)), int(m.group(2))
    if h < 6:  # "1:05" on a school timetable means 13:05
        h += 12
    return f"{h:02d}:{mi:02d}"


def to_school(parsed: dict, name: str, lat: float, lon: float, capacity: int = 2) -> dict:
    """Normalise a transcription into the CleanHour school model, or explain what is missing."""
    periods, teaching_ids = [], []
    for i, p in enumerate(parsed["periods"]):
        kind = p["kind"]
        pid = {"assembly": "ASM", "recess": "REC"}.get(kind, f"P{len(teaching_ids) + 1}")
        if pid in {x["id"] for x in periods}:
            pid = f"{pid}{i}"
        periods.append({"id": pid, "label": p["label"], "start": _hhmm(p["start"]), "end": _hhmm(p["end"]),
                        "kind": kind, "_index": i})
        if kind == "teaching":
            teaching_ids.append(pid)
    periods.sort(key=lambda p: p["start"])
    if len(teaching_ids) < 3:
        raise OnboardingError("found fewer than 3 teaching periods; try a sharper, straighter photo")
    by_index = {p["_index"]: p for p in periods}
    classes = []
    for c in parsed["classes"]:
        cid = re.sub(r"[^\w-]", "", c["name"].upper())[:8] or f"C{len(classes) + 1}"
        grade = int(re.search(r"\d+", cid).group()) if re.search(r"\d+", cid) else 6
        tt = {}
        for cell in c["cells"]:
            p = by_index.get(cell["period_index"])
            if not p or p["kind"] != "teaching":
                continue
            subject = "PE" if PE_PATTERN.search(cell["subject"]) else cell["subject"].strip() or "Free"
            tt[p["id"]] = {"subject": subject, "teacher": cell["teacher"].strip() or f"Teacher ({cid} {subject})"}
        for pid in teaching_ids:  # unknown cells must not create fake teacher clashes
            tt.setdefault(pid, {"subject": "Free", "teacher": f"(free {cid} {pid})"})
        classes.append({"id": cid, "grade": grade, "strength": 40, "asthma_watch": 0, "timetable": tt})
    if not classes:
        raise OnboardingError("no classes found in the photo")
    for p in periods:
        p.pop("_index")
    return {
        "id": f"{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:24] or 'school'}-{uuid.uuid4().hex[:5]}",
        "name": name, "name_hi": name, "city": "", "lat": lat, "lon": lon, "grap_stage": 0,
        "playground_capacity": capacity, "periods": periods, "classes": classes, "onboarded_from": "photo",
    }
