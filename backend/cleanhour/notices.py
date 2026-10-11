"""Deterministic English/Hindi notices built straight from the plan. Used as-is when Bedrock is
unavailable, and given to the agent as the fact sheet it must not deviate from."""

from collections import defaultdict
from datetime import date as Date

from . import rules

HINDI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर",
                "अक्टूबर", "नवंबर", "दिसंबर"]


def clock_en(hhmm: str) -> str:
    h, m = map(int, hhmm.split(":"))
    return f"{(h - 1) % 12 + 1}:{m:02d} {'AM' if h < 12 else 'PM'}"


def clock_hi(hhmm: str) -> str:
    h, m = map(int, hhmm.split(":"))
    part = "सुबह" if h < 12 else ("दोपहर" if h < 16 else "शाम")
    return f"{part} {(h - 1) % 12 + 1}:{m:02d}"


def _date_en(iso: str) -> str:
    return Date.fromisoformat(iso).strftime("%a %d %b %Y")


def _date_hi(iso: str) -> str:
    d = Date.fromisoformat(iso)
    return f"{d.day} {HINDI_MONTHS[d.month - 1]} {d.year}"


def build(plan: dict, school: dict) -> dict:
    idx = plan["period_index"]
    flag = plan["flag"]
    m = plan["metrics"]
    en, hi = [], []

    if plan["quiet"]:
        en.append(f"Air during school hours is {flag['en']} (PM2.5 up to {flag['pm25']}). Normal timetable today.")
        hi.append(f"आज स्कूल के समय हवा {flag['hi']} है (PM2.5 {flag['pm25']} तक)। समय-सारणी में कोई बदलाव नहीं।")
    else:
        en.append(f"Air today: {flag['en']} (PM2.5 {flag['pm25']} at {clock_en(idx[flag['period']]['start'])}).")
        hi.append(f"आज की हवा: {flag['hi']} ({clock_hi(idx[flag['period']]['start'])} पर PM2.5 {flag['pm25']})।")

    heat = plan.get("heat")
    if heat and heat["feels"] >= 35:
        en.append(f"Heat: feels like {heat['feels']} °C by {clock_en(idx[heat['period']]['start'])}.")
        hi.append(f"गर्मी: {clock_hi(idx[heat['period']]['start'])} तक {heat['feels']} °C जैसा महसूस होगा।")

    regulatory = sorted({r for c in plan["changes"] for r in c["rules"] if r in rules.REGULATORY})
    for r in regulatory:
        en.append(f"{rules.explain(r)}.")
        hi.append(f"{rules.explain(r, 'hi')}।")

    for c in plan["changes"]:
        if c["type"] != "venue":
            continue
        who_en = "" if c["scope"] == "all" else f" for classes {', '.join(c['scope'])}"
        who_hi = "" if c["scope"] == "all" else f" (कक्षा {', '.join(c['scope'])})"
        if c["activity"] == "Assembly":
            en.append(f"Assembly{who_en} will be held in classrooms over the PA system.")
            hi.append(f"प्रार्थना सभा{who_hi} आज कक्षाओं में माइक से होगी।")
        else:
            en.append(f"Recess{who_en} will be indoors (reading, board games).")
            hi.append(f"रिसेस{who_hi} आज अंदर होगा (किताबें, बोर्ड गेम)।")

    for c in plan["changes"]:
        if c["type"] == "move" and c.get("driver") == "heat":
            en.append(f"PE for {c['class_id']} moved to a cooler hour: {clock_en(idx[c['to']]['start'])} "
                      f"(feels like {c['feels_from']} → {c['feels_to']} °C).")
            hi.append(f"गर्मी के कारण कक्षा {c['class_id']} का खेल ठंडे समय पर: {clock_hi(idx[c['to']]['start'])} "
                      f"({c['feels_from']} → {c['feels_to']} °C महसूस)।")
    moves = defaultdict(list)
    for c in plan["changes"]:
        if c["type"] == "move" and c.get("driver") != "heat":
            moves[c["to"]].append(c)
    if moves:
        parts_en, parts_hi = [], []
        for to, cs in sorted(moves.items(), key=lambda kv: idx[kv[0]]["start"]):
            names = " & ".join(c["class_id"] for c in cs)
            parts_en.append(f"{names} at {clock_en(idx[to]['start'])}")
            parts_hi.append(f"{', '.join(c['class_id'] for c in cs)}: {clock_hi(idx[to]['start'])}")
        best = max(c["gain_pct"] for cs in moves.values() for c in cs)
        en.append(f"PE moved to cleaner hours: {'; '.join(parts_en)} (up to {best}% cleaner air). Send PE shoes as usual.")
        hi.append(f"खेल का पीरियड साफ़ हवा वाले समय पर: {'; '.join(parts_hi)} (हवा {best}% तक साफ़)। पीटी के जूते रोज़ की तरह भेजें।")

    indoor = [c["class_id"] for c in plan["changes"] if c["type"] == "indoor"]
    if indoor:
        en.append(f"PE indoors (yoga & stretching) for {', '.join(indoor)}.")
        hi.append(f"कक्षा {', '.join(indoor)} का खेल अंदर होगा (योग और स्ट्रेचिंग)।")

    if m["asthma_kids_indoor"]:
        en.append("Children on the asthma-watch list will do light indoor activity during PE.")
        hi.append("अस्थमा सूची वाले बच्चे खेल के समय अंदर हल्की गतिविधि करेंगे।")

    if not plan["quiet"] and m.get("heat_moves") or (heat and heat["feels"] >= 35 and not plan["quiet"]):
        en.append("Please send a water bottle and a cap. Tell the class teacher if your child feels dizzy or unwell.")
        hi.append("कृपया पानी की बोतल और टोपी भेजें। चक्कर या तबीयत खराब लगे तो कक्षा अध्यापक को बताएं।")
    elif not plan["quiet"]:
        en.append("Please send a water bottle. Tell the class teacher if your child has a cough or breathlessness.")
        hi.append("कृपया पानी की बोतल भेजें। खांसी या सांस फूलने पर कक्षा अध्यापक को बताएं।")

    header_en = f"{school['name']} · {_date_en(plan['date'])}"
    header_hi = f"{school.get('name_hi', school['name'])} · {_date_hi(plan['date'])}"
    parent_en = header_en + "\n" + "\n".join(f"• {line}" for line in en)
    parent_hi = header_hi + "\n" + "\n".join(f"• {line}" for line in hi)

    if plan["quiet"]:
        brief = [f"{flag['en']} air all day (max PM2.5 {flag['pm25']}). No changes needed."]
    else:
        brief = [
            f"{flag['en']} at {clock_en(idx[flag['period']]['start'])} (PM2.5 {flag['pm25']}).",
            f"{m['pe_moved']} PE period{'s' if m['pe_moved'] != 1 else ''} moved, {m['pe_indoor']} indoors; "
            f"PE air {m['pe_pm25_before']} → {m['pe_pm25_after']} µg/m³.",
            f"Estimated PM2.5 inhaled during outdoor time: -{m['reduction_pct']}% "
            f"({m['dose_before_mg']} → {m['dose_after_mg']} mg across {m['students']} students).",
        ]
        if m["asthma_kids_indoor"]:
            brief.append(f"{m['asthma_kids_indoor']} asthma-watch students indoors during PE.")
        if m.get("heat_moves"):
            brief.append(f"Heat: {m['heat_moves']} PE period{'s' if m['heat_moves'] != 1 else ''} moved to cooler hours; hottest PE now feels like "
                         f"{m['pe_feels_after']} °C (was {m['pe_feels_before']} °C).")
        if plan["regulatory"]:
            brief.append("Includes changes required by GRAP; these auto-apply if not approved by 6:45 AM.")

    voice_hi = "नमस्ते। " + " ".join(hi) + f" धन्यवाद, {school.get('name_hi', school['name'])}।"
    return {
        "principal_brief_en": brief,
        "parent_notice_en": parent_en,
        "parent_notice_hi": parent_hi,
        "voice_script_hi": voice_hi,
        "source": "template",
    }
