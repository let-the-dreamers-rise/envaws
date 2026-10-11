"""India NAQI PM2.5 bands (CPCB). The bands are defined on 24-hour averages; CleanHour
applies them to hourly forecasts as an approximation, which is stated in the UI."""

BANDS = [
    # upper bound (inclusive), key, English, Hindi, colour
    (30, "good", "Good", "अच्छी", "#2e9e4f"),
    (60, "satisfactory", "Satisfactory", "संतोषजनक", "#8cc43f"),
    (90, "moderate", "Moderate", "मध्यम", "#f4c430"),
    (120, "poor", "Poor", "खराब", "#f08a24"),
    (250, "very_poor", "Very Poor", "बहुत खराब", "#d93b3b"),
    (float("inf"), "severe", "Severe", "गंभीर", "#7e1f3c"),
]


def band(pm25: float) -> dict:
    for upper, key, en, hi, colour in BANDS:
        if pm25 <= upper:
            return {"key": key, "en": en, "hi": hi, "colour": colour}
    raise ValueError(pm25)
