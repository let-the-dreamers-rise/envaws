"""Reproduce CleanHour's ground-truth numbers from measured CPCB station data.

    python analysis/ground_truth.py            # downloads ~24 MB of CSVs into analysis/data/

Data: CPCB continuous monitoring stations (15-minute), republished by OpenCity
(https://data.opencity.in/dataset/delhi-hourly-air-quality-reports). Timestamps are IST despite the
"+0000" suffix (the daily cycle peaks at 08:00 and bottoms out at 16:00 local time as labelled).
"""

import csv
import os
import statistics as st
import urllib.request
from collections import defaultdict
from datetime import datetime

BASE = "https://data.opencity.in/dataset/0dc7b9fe-9fd4-46ee-a37e-88f0bd6f6362/resource"
STATIONS = {
    "Rohini DPCC": f"{BASE}/f6be929b-151a-4b92-b5b4-507481b15128/download/del-rohini-dpcc-2024-25.csv",
    "R K Puram DPCC": f"{BASE}/d9dfd28d-038d-448f-8e33-5e6f6b32d15c/download/del-r-k-puram-dpcc-2024-25.csv",
}
DATA = os.path.join(os.path.dirname(__file__), "data")
PE_LIMIT = 120  # policies.cedar: no outdoor exertion above 120 µg/m³


def hourly(path):
    """{date: {hour: mean PM2.5}} from 15-minute rows."""
    raw = defaultdict(lambda: defaultdict(list))
    with open(path, newline="", encoding="utf-8") as f:
        rows = csv.reader(f)
        head = next(rows)
        ti = head.index("Timestamp")
        pi = next(i for i, h in enumerate(head) if h.startswith("PM2.5"))
        for row in rows:
            try:
                t = datetime.strptime(row[ti][:19], "%Y-%m-%dT%H:%M:%S")
                v = float(row[pi])
            except (ValueError, IndexError):
                continue
            if 0 < v < 1500:
                raw[t.date()][t.hour].append(v)
    return {d: {h: st.mean(v) for h, v in hs.items()} for d, hs in raw.items()}


def school_day(hs):
    return all(h in hs for h in range(8, 15))


def report(name, days):
    print(f"\n{name}")
    for year in (2024, 2025):
        season = {d: hs for d, hs in days.items() if d.year == year and school_day(hs)
                  and ((d.month == 10 and d.day >= 15) or d.month == 11)}
        cuts = [1 - min(hs[h] for h in range(8, 15)) / hs[8] for hs in season.values()]
        at8 = st.mean(hs[8] for hs in season.values())
        at13 = st.mean(hs[13] for hs in season.values())
        print(f"  15 Oct-30 Nov {year}: mean PM2.5 8 AM {at8:.0f} vs 1 PM {at13:.0f}; "
              f"median cut moving 8 AM to cleanest school hour {st.median(cuts) * 100:.0f}% ({len(season)} days)")
    winter = {d: hs for d, hs in days.items() if d.weekday() < 6 and school_day(hs)
              and ((d.year == 2024 and d.month >= 10) or (d.year == 2025 and d.month <= 2))}
    fine = sum(hs[8] <= PE_LIMIT for hs in winter.values())
    rescued = sum(hs[8] > PE_LIMIT and min(hs[h] for h in range(8, 15)) <= PE_LIMIT for hs in winter.values())
    print(f"  Oct 2024-Feb 2025, {len(winter)} school days: 8 AM fine {fine}, PE rescued by moving {rescued}, "
          f"nothing safe outdoors {len(winter) - fine - rescued}")


if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    for name, url in STATIONS.items():
        path = os.path.join(DATA, os.path.basename(url))
        if not os.path.exists(path):
            print(f"downloading {name}…")
            urllib.request.urlretrieve(url, path)
        report(name, hourly(path))
