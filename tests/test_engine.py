"""Tests for the locked rules. Run: python tests/test_engine.py"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import build_results as b
import engine

D, H, I = ROOT / "data/Data (SINTETICO).xlsx", ROOT / "data/Hotel responses (SINTETICO).xlsx", ROOT / "data/imports"


def test_latest_submission_wins():
    resp = pd.read_excel(H, dtype=object)
    long, replaced = engine.prepare_responses(resp)
    assert replaced == 1
    v = long[(long.Hotel == "Hotel Mirador Sur") & (long.Month == pd.Period("2026-09", "M"))
             & (long.Segment == "Corporate") & (long.Origin == "Domestic")]["rn"]
    assert len(v) == 1 and v.iloc[0] < 2000, "the typo submission must be replaced by the later one"


def test_structure_check_stops_on_renamed_column():
    import json
    data, resp, _ = engine.read_inputs(D, H, I)
    data["Leads"] = data["Leads"].rename(columns={"Status": "Estado"})
    try:
        engine.check_structure(data, resp, json.load(open(ROOT / "src/schema.json")))
        assert False, "should have stopped"
    except engine.StructureError as e:
        assert "Status" in str(e)


def test_lead_fit_rule():
    S = {"report_month": pd.Period("2026-10", "M"), "targets": ["Government"], "need_months": [5],
         "w_sector": 40, "w_need": 30, "w_capacity": 30, "threshold": 70, "max_peak": 800}
    leads = pd.DataFrame([
        {"Organizer": "A", "Sector": "Government", "Start date": pd.Timestamp("2027-05-10"), "End date": pd.Timestamp("2027-05-13"), "Attendees": 100, "Peak rooms": 80, "Status": "Open"},
        {"Organizer": "B", "Sector": "Sports", "Start date": pd.Timestamp("2027-02-10"), "End date": pd.Timestamp("2027-02-12"), "Attendees": 2000, "Peak rooms": 900, "Status": "Open"},
        {"Organizer": "C", "Sector": "Government", "Start date": pd.Timestamp("2026-05-10"), "End date": pd.Timestamp("2026-05-12"), "Attendees": 100, "Peak rooms": 80, "Status": "Open"},
    ])
    assets = pd.DataFrame({"Max capacity": [900]})
    f = engine.q_lead_fit(leads, pd.DataFrame(), assets, S).set_index("Organizer")
    assert f.loc["A", "Score"] == 100 and f.loc["A", "Priority"] == "Yes"
    assert f.loc["B", "Score"] == 0
    assert "C" not in f.index, "past events are not candidates"


def test_lead_fit_is_graded():
    S = {"report_month": pd.Period("2026-10", "M"), "targets": ["Government"], "secondary": ["Pharma"],
         "need_months": [9], "w_sector": 40, "w_need": 30, "w_capacity": 30, "threshold": 70,
         "max_peak": 800, "comfort_rooms": 400, "comfort_att": 650}
    occ = {m: 70 for m in range(1, 13)}
    occ.update({9: 40, 3: 80, 6: 60})  # Sep weakest, Mar strongest, Jun in between
    def lead(o, sector, start, att, peak):
        return {"Organizer": o, "Sector": sector, "Start date": pd.Timestamp(start),
                "End date": pd.Timestamp(start) + pd.Timedelta(days=3), "Attendees": att, "Peak rooms": peak, "Status": "Open"}
    leads = pd.DataFrame([
        lead("weak month", "Government", "2027-09-10", 100, 80),
        lead("strong month", "Government", "2027-03-10", 100, 80),
        lead("mid month", "Government", "2027-06-10", 100, 80),
        lead("secondary", "Pharma", "2027-09-10", 100, 80),
        lead("tight", "Government", "2027-09-10", 775, 600),
    ])
    f = engine.q_lead_fit(leads, pd.DataFrame(), pd.DataFrame({"Max capacity": [900]}), S, occ).set_index("Organizer")
    assert f.loc["weak month", "Need period pts"] == 30 and f.loc["strong month", "Need period pts"] == 0
    assert f.loc["mid month", "Need period pts"] == 15
    assert f.loc["secondary", "Sector pts"] == 20
    # 775 attendees is halfway from 650 to 900; 600 rooms is halfway from 400 to 800: 15 of 30 points
    assert f.loc["tight", "Capacity pts"] == 15


def test_sample_size_rule():
    R = engine.run(D, H, I)
    box = R["box"].set_index("Sector")
    assert box.loc["Government", "Win rate"] == engine.NOT_ENOUGH  # 4 decisions < 5


def test_like_for_like_trend_excludes_non_reporting_hotel():
    R = engine.run(D, H, I)
    assert R["trend"]["excluded_hotels"] == ["Hotel Cerro Verde"]
    assert R["trend"]["comparable_hotels"] == 7


def test_number_check_catches_a_wrong_number():
    R = engine.run(D, H, I)
    p = b.brief_payload(R)
    ok = b.check_brief("Ganamos 26 de 92 (28.3%).", p)
    bad = b.check_brief("Registramos 8,590 noches.", p)  # true value is 8,580
    assert (ok["Found in results"] == "Yes").all()
    assert (bad["Found in results"] == "NO").any()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
