"""Demo school. Fictional name and timetable; coordinates are in Rohini, Delhi."""

PERIODS = [
    {"id": "ASM", "label": "Assembly", "start": "07:45", "end": "08:05", "kind": "assembly"},
    {"id": "P1", "label": "Period 1", "start": "08:05", "end": "08:45", "kind": "teaching"},
    {"id": "P2", "label": "Period 2", "start": "08:45", "end": "09:25", "kind": "teaching"},
    {"id": "P3", "label": "Period 3", "start": "09:25", "end": "10:05", "kind": "teaching"},
    {"id": "P4", "label": "Period 4", "start": "10:05", "end": "10:45", "kind": "teaching"},
    {"id": "REC", "label": "Recess", "start": "10:45", "end": "11:05", "kind": "recess"},
    {"id": "P5", "label": "Period 5", "start": "11:05", "end": "11:45", "kind": "teaching"},
    {"id": "P6", "label": "Period 6", "start": "11:45", "end": "12:25", "kind": "teaching"},
    {"id": "P7", "label": "Period 7", "start": "12:25", "end": "13:05", "kind": "teaching"},
    {"id": "P8", "label": "Period 8", "start": "13:05", "end": "13:45", "kind": "teaching"},
]


def _tt(*cells):
    return {f"P{i + 1}": {"subject": s, "teacher": t} for i, (s, t) in enumerate(cells)}


CLASSES = [
    {"id": "3A", "grade": 3, "strength": 36, "asthma_watch": 3, "timetable": _tt(
        ("PE", "Mr. Rawat"), ("English", "Ms. Iyer"), ("Maths", "Ms. Iyer"), ("Hindi", "Mr. Yadav"),
        ("EVS", "Ms. Iyer"), ("Art", "Ms. Das"), ("Maths", "Ms. Iyer"), ("Story time", "Ms. Iyer"))},
    {"id": "4A", "grade": 4, "strength": 38, "asthma_watch": 2, "timetable": _tt(
        ("PE", "Ms. Kaur"), ("Hindi", "Mr. Yadav"), ("English", "Ms. Khan"), ("Maths", "Ms. Khan"),
        ("Art", "Ms. Das"), ("EVS", "Ms. Khan"), ("Music", "Mr. Thomas"), ("Maths", "Ms. Khan"))},
    {"id": "5A", "grade": 5, "strength": 40, "asthma_watch": 4, "timetable": _tt(
        ("English", "Ms. Roy"), ("PE", "Mr. Rawat"), ("Hindi", "Mr. Yadav"), ("EVS", "Ms. Roy"),
        ("Maths", "Ms. Roy"), ("Music", "Mr. Thomas"), ("Art", "Ms. Das"), ("Maths", "Ms. Roy"))},
    {"id": "6A", "grade": 6, "strength": 42, "asthma_watch": 3, "timetable": _tt(
        ("Maths", "Mr. Gupta"), ("PE", "Ms. Kaur"), ("Science", "Dr. Sharma"), ("English", "Ms. Fernandes"),
        ("Hindi", "Mr. Yadav"), ("Social Science", "Ms. Ali"), ("Computer", "Mr. Joshi"), ("Sanskrit", "Mr. Mishra"))},
    {"id": "7A", "grade": 7, "strength": 41, "asthma_watch": 5, "timetable": _tt(
        ("Science", "Dr. Sharma"), ("Maths", "Mr. Gupta"), ("PE", "Mr. Rawat"), ("Social Science", "Ms. Ali"),
        ("English", "Ms. Fernandes"), ("Computer", "Mr. Joshi"), ("Sanskrit", "Mr. Mishra"), ("Hindi", "Mr. Yadav"))},
    {"id": "8A", "grade": 8, "strength": 44, "asthma_watch": 4, "timetable": _tt(
        ("English", "Ms. Fernandes"), ("Science", "Dr. Sharma"), ("Maths", "Mrs. Bansal"), ("Computer", "Mr. Joshi"),
        ("Social Science", "Ms. Ali"), ("PE", "Ms. Kaur"), ("Maths", "Mrs. Bansal"), ("Science", "Dr. Sharma"))},
]

DEMO_SCHOOL = {
    "id": "demo-rohini",
    "name": "Sarvodaya Vidyalaya (Demo), Rohini",
    "name_hi": "सर्वोदय विद्यालय (डेमो), रोहिणी",
    "city": "Delhi",
    "lat": 28.7383,
    "lon": 77.0822,
    "grap_stage": 1,
    # PE needs the ground; at most this many classes can use it at once.
    "playground_capacity": 2,
    "periods": PERIODS,
    "classes": CLASSES,
}

OUTDOOR_SUBJECTS = {"PE": "high"}
