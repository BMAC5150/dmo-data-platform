"""Generate the SYNTHETIC Ixtapa-Zihuatanejo prototype dataset.

Everything here is invented: hotel names, organizers, figures. Only the
destination room count (6,800, Datatur) is real. Writes three files:
  data/Data (SINTETICO).xlsx
  data/Hotel responses (SINTETICO).xlsx
  data/imports/Cvent export 2026-10 (SINTETICO).csv
"""
import os
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

rng = np.random.default_rng(2026)
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT, exist_ok=True)
LABEL = "DATOS SINTÉTICOS: todo es inventado salvo las 6,800 habitaciones (Datatur). No usar como datos reales."

# ---------------------------------------------------------------- Assets
assets = pd.DataFrame([
    # type, name, rooms, meeting rooms, meeting space m2, max capacity (theatre)
    ("Hotel", "Hotel Palmar Grande", 510, 9, 1400, 900),
    ("Hotel", "Resort Punta Sol", 450, 7, 1000, 650),
    ("Hotel", "Hotel Coral Norte", 420, 8, 1100, 700),
    ("Hotel", "Resort Pelícano", 380, 6, 900, 550),
    ("Hotel", "Resort Bahía Quieta", 340, 5, 800, 500),
    ("Hotel", "Hotel Arrecife", 300, 5, 650, 400),
    ("Hotel", "Hotel Mirador Sur", 260, 4, 400, 250),
    ("Hotel", "Hotel Cerro Verde", 210, 3, 300, 180),
    ("Hotel", "Hotel Ola Mansa", 190, 2, 250, 150),
    ("Hotel", "Hotel Faro Viejo", 160, 2, 200, 120),
    ("Hotel", "Suites Manglar", 140, 0, 0, 0),
    ("Hotel", "Hotel Isla Pequeña", 120, 0, 0, 0),
    ("Venue", "Jardín Las Palmas (outdoor)", 0, 1, 1800, 600),
    ("Venue", "Club de Playa Marino", 0, 1, 500, 300),
    ("Supplier", "DMC Costa Grande", None, None, None, None),
    ("Supplier", "Audiovisual Pacífico", None, None, None, None),
    ("Supplier", "Transportes Sierra y Mar", None, None, None, None),
], columns=["Type", "Name", "Rooms", "Meeting rooms", "Meeting space (m2)", "Max capacity"])

FORM_HOTELS = ["Hotel Palmar Grande", "Resort Punta Sol", "Hotel Coral Norte", "Resort Pelícano",
               "Resort Bahía Quieta", "Hotel Arrecife", "Hotel Mirador Sur", "Hotel Cerro Verde"]
rooms = dict(zip(assets.Name, assets.Rooms))

# ---------------------------------------------------------------- Lists
SECTORS = ["Medical association", "Insurance & finance", "Mexican corporate", "Government",
           "Pharma", "Education", "Agriculture", "Religious", "Sports"]
SEGMENTS = ["Association", "Corporate", "Incentive", "Government & other"]
ORIGINS = ["Domestic", "International"]
STATUS = ["Open", "Won", "Lost"]
LOSS = ["Price", "Air access", "Safety perception", "Dates not available",
        "Venue too small", "Destination profile", "Event cancelled"]
COMPETITORS = ["Puerto Vallarta", "Huatulco", "Mazatlán", "Riviera Maya", "Acapulco", "Oaxaca", "Other"]
ORIGIN_REG = ["Mexico City", "Jalisco", "Nuevo León", "Bajío", "Other Mexico", "USA", "Canada"]
EVENT_TYPES = ["Congress", "Convention", "Incentive", "Corporate meeting", "Training"]
SOURCES = ["RFP (Cvent)", "Trade show", "Direct", "Hotel referral", "Referral"]

lists_cols = {
    "Hotels (form)": FORM_HOTELS, "Sectors": SECTORS, "Segments": SEGMENTS, "Origins": ORIGINS,
    "Origin regions": ORIGIN_REG, "Event types": EVENT_TYPES, "Sources": SOURCES,
    "Lead status": STATUS, "Loss reasons": LOSS, "Lost to": COMPETITORS,
}
n = max(len(v) for v in lists_cols.values())
lists = pd.DataFrame({k: v + [None] * (n - len(v)) for k, v in lists_cols.items()})

# ---------------------------------------------------------------- Settings
settings = pd.DataFrame([
    ("Report month", "2026-10", "Month the run reports on"),
    ("Destination hotel rooms", 6800, "Source: Datatur (real figure)"),
    ("Plan target sectors", "Medical association; Insurance & finance; Mexican corporate; Government", "From the DMO sales plan"),
    ("Need-period months", "5; 6; 9; 10; 11", "Months the DMO most needs group business (lead fit uses occupancy; this list is the fallback)"),
    ("Lead fit weight: target sector", 40, "Points"),
    ("Lead fit weight: need period", 30, "Points"),
    ("Lead fit weight: capacity fit", 30, "Points"),
    ("Lead fit: priority threshold", 80, "Score at or above this is a priority lead"),
    ("Max peak rooms for one group", 800, "Largest room block the destination can commit"),
    ("Capacity check: group size", 600, "Attendees, for the capacity-match query"),
    ("Minimum sample size", 5, "Below this, a result shows 'Not enough data'"),
    ("Secondary target sectors", "Pharma; Education", "Half the sector points"),
    ("Comfortable peak rooms", 400, "Full capacity points up to here, falling to 0 at the max peak rooms"),
    ("Comfortable attendees", 650, "Full capacity points up to here, falling to 0 at the largest venue's capacity"),
    ("Brief recipients", "director@ejemplo.mx", "Placeholder, not a real address"),
], columns=["Setting", "Value", "Note"])

# ---------------------------------------------------------------- Public data
months_24 = pd.period_range("2024-11", "2026-10", freq="M")
occ_base = {1: .72, 2: .76, 3: .78, 4: .74, 5: .52, 6: .50, 7: .70, 8: .66, 9: .40, 10: .48, 11: .58, 12: .74}
pub = []
for m in months_24:
    pub.append((str(m), "Hotel occupancy (%)", round(occ_base[m.month] * 100 + rng.normal(0, 2), 1), "SINTÉTICO"))
    pub.append((str(m), "Scheduled air seats (arrivals)", int(52000 * occ_base[m.month] / .65 + rng.normal(0, 1500)), "SINTÉTICO"))
public = pd.DataFrame(pub, columns=["Month", "Measure", "Value", "Source"])

# ---------------------------------------------------------------- Hotel responses (Google Form)
seasonal = {1: .9, 2: 1.2, 3: 1.1, 4: .8, 5: 1.0, 6: .9, 7: .6, 8: .6, 9: .7, 10: 1.0, 11: 1.1, 12: .5}
seg_mix = {"Association": .30, "Corporate": .35, "Incentive": .20, "Government & other": .15}
resp = []
for m in months_24:
    yr2 = m >= pd.Period("2025-11", "M")
    for h in FORM_HOTELS:
        if str(m) == "2026-10" and h == "Hotel Cerro Verde":
            continue  # did not submit: exercises the data check
        base = rooms[h] * m.days_in_month * 0.11 * seasonal[m.month]
        row = {"Timestamp": None, "Hotel": h, "Month": str(m)}
        for s in SEGMENTS:
            g = 1.0
            if yr2:
                g = {"Association": .97, "Corporate": 1.04, "Incentive": 1.12, "Government & other": 1.0}[s]
                if str(m) == "2026-10" and s == "Association":
                    g = .72  # a lost congress shows up in October
            seg = base * seg_mix[s] * g * rng.normal(1, .08)
            intl = {"Association": .08, "Corporate": .10, "Incentive": .30, "Government & other": .02}[s]
            row[f"{s} - Domestic"] = int(round(seg * (1 - intl)))
            row[f"{s} - International"] = int(round(seg * intl))
        nxt = (m + 1).to_timestamp()
        row["Timestamp"] = (nxt + timedelta(days=int(rng.integers(0, 2)), hours=int(rng.integers(9, 18)),
                                            minutes=int(rng.integers(0, 60)))).strftime("%Y-%m-%d %H:%M")
        resp.append(row)
# a resubmission: first entry for Sep 2026 had a typo, the hotel sent it again
dup = dict(next(r for r in resp if r["Hotel"] == "Hotel Mirador Sur" and r["Month"] == "2026-09"))
for r in resp:
    if r["Hotel"] == "Hotel Mirador Sur" and r["Month"] == "2026-09":
        r["Corporate - Domestic"] *= 10  # typo in the first submission
dup["Timestamp"] = "2026-10-02 16:41"
resp.append(dup)
responses = pd.DataFrame(resp)

# ---------------------------------------------------------------- Leads
ORG_WORDS = ["Altavista", "Cumbres", "Ribera", "Ceiba", "Nogal", "Sauce", "Tule", "Encino", "Laurel",
             "Mezquite", "Jacaranda", "Olmo", "Cedro", "Álamo", "Maguey", "Huizache", "Fresno", "Ocote"]
ORG_TMPL = {
    "Medical association": ["Sociedad {w} de Cardiología", "Colegio {w} de Pediatría", "Asociación {w} de Ortopedia",
                            "Sociedad {w} de Dermatología", "Colegio {w} de Anestesiología"],
    "Insurance & finance": ["Seguros {w}", "Grupo Financiero {w}", "Afianzadora {w}"],
    "Mexican corporate": ["Industrias {w}", "Grupo {w}", "Corporativo {w}", "Distribuidora {w}"],
    "Government": ["Secretaría Estatal {w}", "Instituto Estatal {w}"],
    "Pharma": ["Laboratorios {w}", "Farma {w}"],
    "Education": ["Universidad {w}", "Consorcio Educativo {w}"],
    "Agriculture": ["Unión Agrícola {w}", "Productores {w}"],
    "Religious": ["Congregación {w}"],
    "Sports": ["Liga {w}", "Federación {w}"],
}
SECTOR_P = [.22, .14, .18, .08, .10, .08, .08, .06, .06]
EVENT_BY_SECTOR = {"Medical association": ["Congress", "Convention"], "Insurance & finance": ["Incentive", "Convention"],
                   "Mexican corporate": ["Corporate meeting", "Incentive", "Training"], "Government": ["Convention", "Training"]}
used = set()


def org(sector):
    for _ in range(100):
        name = rng.choice(ORG_TMPL[sector]).format(w=rng.choice(ORG_WORDS))
        if name not in used:
            used.add(name)
            return name
    return name + " II"


leads = []
start_rx = date(2025, 1, 6)
for i in range(160):
    sector = rng.choice(SECTORS, p=SECTOR_P)
    received = start_rx + timedelta(days=int(rng.integers(0, 665)))  # to end Oct 2026
    lead_days = int(rng.integers(90, 420))
    start = received + timedelta(days=lead_days)
    nights = int(rng.integers(2, 5))
    att = int(rng.choice([rng.integers(40, 150), rng.integers(150, 450), rng.integers(450, 1200)], p=[.45, .4, .15]))
    peak = int(att * rng.uniform(.55, .8))
    et = rng.choice(EVENT_BY_SECTOR.get(sector, EVENT_TYPES))
    origin = rng.choice(ORIGIN_REG, p=[.3, .15, .15, .12, .14, .09, .05])
    decision = received + timedelta(days=int(rng.integers(45, 240)))
    row = dict(LeadID=f"L-{i + 1:04d}", Received=received.isoformat(), Organizer=org(sector), Sector=sector,
               **{"Event type": et}, Origin=origin, **{"Start date": start.isoformat(),
               "End date": (start + timedelta(days=nights)).isoformat()}, Attendees=att, **{"Peak rooms": peak},
               Source=rng.choice(SOURCES), Status="Open", **{"Decision date": None, "Loss reason": None,
               "Lost to": None, "Venues used": None, "Actual room nights": None, "Actual attendance": None})
    if decision <= date(2026, 10, 31):
        p_win = .38 if sector in ("Medical association", "Mexican corporate", "Insurance & finance", "Government") else .25
        if att > 900:
            p_win = .05
        if rng.random() < p_win:
            row["Status"] = "Won"
            fits = [h for h in FORM_HOTELS if rooms[h] >= peak * .5] or [FORM_HOTELS[0]]
            hosts = list(rng.choice(fits, size=min(2 if peak > 300 else 1, len(fits)), replace=False))
            row["Venues used"] = "; ".join(hosts)
            row["Actual room nights"] = int(peak * nights * rng.uniform(.8, .97))
            row["Actual attendance"] = int(att * rng.uniform(.85, 1.02))
        else:
            row["Status"] = "Lost"
            if att > 900:
                reason = "Venue too small"
            else:
                reason = rng.choice(LOSS, p=[.22, .24, .20, .12, .04, .10, .08])
            row["Loss reason"] = reason
            row["Lost to"] = None if reason == "Event cancelled" else rng.choice(
                COMPETITORS, p=[.28, .18, .14, .16, .10, .06, .08])
        row["Decision date"] = decision.isoformat()
    leads.append(row)
leads = pd.DataFrame(leads).sort_values("Received").reset_index(drop=True)
leads["LeadID"] = [f"L-{i + 1:04d}" for i in range(len(leads))]

# ---------------------------------------------------------------- Imports (Cvent-style export)
IND = {"Healthcare - Association": "Medical association", "Financial Services": "Insurance & finance",
       "Manufacturing": "Mexican corporate", "Retail": "Mexican corporate", "Public Sector": "Government",
       "Pharmaceutical": "Pharma", "Education": "Education", "Non-profit": "Religious"}
imp = []
for i in range(30):
    ind = rng.choice(list(IND), p=[.25, .15, .15, .07, .1, .1, .1, .08])
    start = date(2027, 1, 1) + timedelta(days=int(rng.integers(0, 330)))
    att = int(rng.choice([rng.integers(60, 200), rng.integers(200, 700), rng.integers(700, 1300)], p=[.4, .45, .15]))
    imp.append({"Organization": org(IND[ind]), "Industry": ind, "Preferred Start": start.strftime("%m/%d/%Y"),
                "Nights": int(rng.integers(2, 5)), "Est. Attendees": att, "Peak Room Night": int(att * rng.uniform(.55, .8)),
                "Home Market": rng.choice(["CDMX", "GDL", "MTY", "QRO", "USA"])})
imports = pd.DataFrame(imp)
open_orgs = leads.loc[leads.Status == "Open", "Organizer"].tolist()
for k, o in enumerate(open_orgs[:3]):  # three prospects are already leads: exercises de-duplication
    imports.loc[k, "Organization"] = o

# ---------------------------------------------------------------- Write files
def readme(ws_name):
    return pd.DataFrame({"": [LABEL]})


with pd.ExcelWriter(os.path.join(OUT, "Data (SINTETICO).xlsx"), engine="xlsxwriter") as xw:
    pd.DataFrame({"Read me": [LABEL,
                              "Staff type into Leads. The data owner updates PublicData monthly. Settings holds the business rules values.",
                              "Do not rename tabs or columns: the monthly run checks the structure and stops if it changes."]}
                 ).to_excel(xw, "Read me", index=False)
    for name, df in [("Leads", leads), ("Assets", assets), ("PublicData", public), ("Lists", lists), ("Settings", settings)]:
        df.to_excel(xw, name, index=False)
with pd.ExcelWriter(os.path.join(OUT, "Hotel responses (SINTETICO).xlsx"), engine="xlsxwriter") as xw:
    responses.to_excel(xw, "Form responses 1", index=False)
os.makedirs(os.path.join(OUT, "imports"), exist_ok=True)
imports.to_csv(os.path.join(OUT, "imports", "Cvent export 2026-10 (SINTETICO).csv"), index=False)

print("leads", len(leads), leads.Status.value_counts().to_dict())
print("responses", len(responses), "imports", len(imports))
