"""Small-DMO Business Events Data Platform: rules engine (prototype).

Reads the DMO's Data sheet, Hotel responses sheet and Imports, checks the
structure, runs the six locked queries and returns one results dict. The
workbook builder and the brief number check live in build_results.py.

In production the three readers below call the Sheets and Drive APIs; in this
prototype they read local exports of the same files. Nothing else changes.
"""
import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
SEGMENTS = ["Association", "Corporate", "Incentive", "Government & other"]
ORIGINS = ["Domestic", "International"]
NOT_ENOUGH = "Not enough data"


class StructureError(Exception):
    """Raised when a tab or column has changed. The run stops; the operator is told."""


# ------------------------------------------------------------------ readers
def read_inputs(data_xlsx, responses_xlsx, imports_dir):
    data = pd.read_excel(data_xlsx, sheet_name=None, dtype=object)
    responses = pd.read_excel(responses_xlsx, sheet_name=None, dtype=object)
    imports = {p.name: pd.read_csv(p, dtype=object) for p in Path(imports_dir).glob("*.csv")}
    return data, responses, imports


# ------------------------------------------------------------------ step 3: structure check
def check_structure(data, responses, schema):
    problems = []
    for book, tabs, label in [(data, schema["data"], "Data"), (responses, schema["responses"], "Hotel responses")]:
        for tab, cols in tabs.items():
            if tab not in book:
                problems.append(f"{label}: tab '{tab}' is missing")
                continue
            missing = [c for c in cols if c not in book[tab].columns]
            if missing:
                problems.append(f"{label} / {tab}: missing column(s) {missing}")
    if problems:
        raise StructureError("; ".join(problems))


def settings_dict(settings_df):
    s = dict(zip(settings_df["Setting"], settings_df["Value"]))
    return {
        "report_month": pd.Period(str(s["Report month"]), "M"),
        "rooms": int(s["Destination hotel rooms"]),
        "targets": [x.strip() for x in str(s["Plan target sectors"]).split(";")],
        "secondary": [x.strip() for x in str(s.get("Secondary target sectors", "")).split(";") if x.strip()],
        "comfort_rooms": int(s.get("Comfortable peak rooms", 0)) or None,
        "comfort_att": int(s.get("Comfortable attendees", 0)) or None,
        "need_months": [int(x) for x in str(s["Need-period months"]).split(";")],
        "w_sector": int(s["Lead fit weight: target sector"]),
        "w_need": int(s["Lead fit weight: need period"]),
        "w_capacity": int(s["Lead fit weight: capacity fit"]),
        "threshold": int(s["Lead fit: priority threshold"]),
        "max_peak": int(s["Max peak rooms for one group"]),
        "cap_group": int(s["Capacity check: group size"]),
        "min_n": int(s["Minimum sample size"]),
    }


# ------------------------------------------------------------------ ingestion
def prepare_responses(resp):
    """Latest submission per hotel and month wins; reshape to one row per segment and origin."""
    r = resp.copy()
    r["Timestamp"] = pd.to_datetime(r["Timestamp"])
    r["Month"] = r["Month"].astype(str).str[:7]
    before = len(r)
    r = r.sort_values("Timestamp").drop_duplicates(["Hotel", "Month"], keep="last")
    replaced = before - len(r)
    long = r.melt(id_vars=["Timestamp", "Hotel", "Month"], var_name="key", value_name="rn")
    long[["Segment", "Origin"]] = long["key"].str.split(" - ", n=1, expand=True)
    long["rn"] = pd.to_numeric(long["rn"]).fillna(0).astype(int)
    long["Month"] = pd.PeriodIndex(long["Month"], freq="M")
    return long.drop(columns="key"), replaced


def prepare_leads(leads):
    l = leads.copy()
    for c in ["Received", "Start date", "End date", "Decision date"]:
        l[c] = pd.to_datetime(l[c], errors="coerce")
    for c in ["Attendees", "Peak rooms", "Actual room nights", "Actual attendance"]:
        l[c] = pd.to_numeric(l[c], errors="coerce")
    return l


def norm(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def prepare_imports(imports, config, leads):
    rows, unmapped, dupes = [], [], 0
    known = {norm(o) for o in leads["Organizer"]}
    for fname, df in imports.items():
        spec = next((v for v in config["imports"].values() if v["match"] in fname), None)
        if spec is None:
            unmapped.append(fname)
            continue
        d = df.rename(columns=spec["columns"])[list(spec["columns"].values())].copy()
        d["Sector"] = d["Sector"].map(spec["sector_map"]).fillna("Unmapped: " + df["Industry"].astype(str))
        d["Start date"] = pd.to_datetime(d["Start date"], format=spec["date_format"], errors="coerce")
        for c in ["Attendees", "Peak rooms", "Nights"]:
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d["Origin file"] = fname
        is_dup = d["Organizer"].map(norm).isin(known)
        dupes += int(is_dup.sum())
        rows.append(d[~is_dup].drop_duplicates("Organizer"))
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return out, unmapped, dupes


# ------------------------------------------------------------------ locked queries
def q_need_periods(long, leads, S):
    """Next 6 months: last year's group room nights, index vs the 12-month average, need flag, business on the books."""
    rm = S["report_month"]
    ttm = long[(long.Month > rm - 12) & (long.Month <= rm)]
    monthly = ttm.groupby("Month")["rn"].sum()
    avg = monthly.mean()
    won = leads[leads.Status == "Won"]
    opn = leads[leads.Status == "Open"]
    out = []
    for k in range(1, 7):
        m = rm + k
        ly = m - 12
        rn_ly = int(long.loc[long.Month == ly, "rn"].sum())
        n_hotels = long.loc[long.Month == ly, "Hotel"].nunique()
        on_books = won[won["Start date"].dt.to_period("M") == m]
        pipe = opn[opn["Start date"].dt.to_period("M") == m]
        out.append({
            "Month": str(m),
            "Group room nights, same month last year": rn_ly,
            "Index vs 12-month average": round(rn_ly / avg, 2) if avg else None,
            "Need period (Settings)": "Yes" if m.month in S["need_months"] else "No",
            "Groups won for the month": len(on_books),
            "Peak rooms won": int(on_books["Peak rooms"].sum()),
            "Open leads for the month": len(pipe),
            "Hotels reporting": n_hotels,
        })
    return pd.DataFrame(out)


def occupancy_by_calendar_month(public, S):
    """Latest 12 months of hotel occupancy from PublicData, keyed by calendar month (1-12)."""
    p = public[public["Measure"] == "Hotel occupancy (%)"].copy()
    p["Month"] = pd.PeriodIndex(p["Month"].astype(str).str[:7], freq="M")
    p["Value"] = pd.to_numeric(p["Value"], errors="coerce")
    rm = S["report_month"]
    p = p[(p.Month > rm - 12) & (p.Month <= rm)].dropna(subset=["Value"])
    return {m.month: v for m, v in zip(p.Month, p.Value)}


def ramp(x, full_at, zero_at):
    """1 at or below full_at, 0 above zero_at, straight line in between."""
    if pd.isna(x):
        return 0.0
    if x <= full_at:
        return 1.0
    if x > zero_at or zero_at <= full_at:
        return 0.0
    return (zero_at - x) / (zero_at - full_at)


def q_lead_fit(leads, prospects, assets, S, occ=None):
    """Lead fit, out of 100, graded on three parts (weights from Settings):

    Sector:      plan target = full points; secondary target = half; other = 0.
    Need period: scaled by how weak the event's month is, from the last 12 months of
                 hotel occupancy in PublicData: lowest month = full points, highest = 0.
                 Falls back to the Settings need-period months if occupancy is missing.
    Capacity:    full points up to the comfortable peak rooms and attendees, falling in a
                 straight line to 0 at the maximum (max peak rooms; largest venue capacity).
                 The tighter of rooms and space sets the points.
    Ties are ranked by estimated room nights (peak rooms x nights).
    """
    rm_end = S["report_month"].to_timestamp(how="end")
    max_cap = pd.to_numeric(assets["Max capacity"], errors="coerce").max()
    comfort_rooms = S.get("comfort_rooms") or S["max_peak"]
    comfort_att = S.get("comfort_att") or max_cap
    occ = occ or {}
    cols = ["Organizer", "Sector", "Start date", "Attendees", "Peak rooms", "Nights"]
    l = leads.assign(Nights=(leads["End date"] - leads["Start date"]).dt.days)
    cand = l[(l.Status == "Open") & (l["Start date"] > rm_end)][cols].assign(Type="Lead")
    if len(prospects):
        cand = pd.concat([cand, prospects[cols].assign(Type="Prospect (import)")], ignore_index=True)
    c = cand.copy()

    c["Sector pts"] = c["Sector"].map(lambda x: S["w_sector"] if x in S["targets"]
                                      else S["w_sector"] / 2 if x in S.get("secondary", []) else 0)

    lo, hi = (min(occ.values()), max(occ.values())) if len(occ) >= 12 else (None, None)
    def need_pts(d):
        m = d.month
        if lo is not None and hi > lo:
            return S["w_need"] * (hi - occ[m]) / (hi - lo)
        return S["w_need"] if m in S["need_months"] else 0
    c["Need period pts"] = c["Start date"].map(need_pts)
    c["Occupancy last year"] = c["Start date"].map(lambda d: occ.get(d.month))

    c["Capacity pts"] = [S["w_capacity"] * min(ramp(r, comfort_rooms, S["max_peak"]), ramp(a, comfort_att, max_cap))
                         for r, a in zip(c["Peak rooms"], c["Attendees"])]
    for k in ["Sector pts", "Need period pts", "Capacity pts"]:
        c[k] = c[k].astype(float).round(0)
    c["Score"] = (c["Sector pts"] + c["Need period pts"] + c["Capacity pts"]).astype(int)
    c["Est. room nights"] = (c["Peak rooms"] * c["Nights"].fillna(3)).astype(int)
    c["Priority"] = (c["Score"] >= S["threshold"]).map({True: "Yes", False: "No"})

    def why(r):
        sec = "plan target" if r["Sector"] in S["targets"] else (
            "secondary target" if r["Sector"] in S.get("secondary", []) else "not a target sector")
        o = r["Occupancy last year"]
        if o is None or pd.isna(o):
            need = "need period" if r["Need period pts"] else "not a need period"
        else:
            need = f"{r['Start date']:%b} occupancy {o:.0f}%"
        if r["Capacity pts"] >= S["w_capacity"]:
            cap = "fits comfortably"
        elif r["Capacity pts"] > 0:
            cap = f"tight fit: {int(r['Attendees'])} attendees, {int(r['Peak rooms'])} peak rooms"
        else:
            cap = f"too big: {int(r['Attendees'])} attendees, {int(r['Peak rooms'])} peak rooms"
        return "; ".join([sec, need, cap])

    c["Why"] = c.apply(why, axis=1)
    c = c.sort_values(["Score", "Est. room nights"], ascending=[False, False]).reset_index(drop=True)
    c.insert(0, "Rank", range(1, len(c) + 1))
    c["Start date"] = c["Start date"].dt.strftime("%Y-%m-%d")
    for k in ["Sector pts", "Need period pts", "Capacity pts"]:
        c[k] = c[k].astype(int)
    return c[["Rank", "Organizer", "Type", "Sector", "Start date", "Attendees", "Peak rooms", "Est. room nights",
              "Sector pts", "Need period pts", "Capacity pts", "Score", "Priority", "Occupancy last year", "Why"]]


def last_12(leads, S):
    rm = S["report_month"]
    start = (rm - 11).to_timestamp()
    end = rm.to_timestamp(how="end")
    return leads[(leads["Decision date"] >= start) & (leads["Decision date"] <= end)]


def q_loss_reasons(leads, S):
    lost = last_12(leads, S).query("Status == 'Lost'")
    n = len(lost)
    if n < S["min_n"]:
        return pd.DataFrame([{"Loss reason": NOT_ENOUGH, "Leads lost": n}]), pd.DataFrame(), n
    r = lost["Loss reason"].value_counts().rename_axis("Loss reason").reset_index(name="Leads lost")
    r["Share"] = (r["Leads lost"] / n).round(3)
    t = lost["Lost to"].dropna().value_counts().rename_axis("Lost to").reset_index(name="Leads lost")
    return r, t, n


def q_capacity(assets, S):
    a = assets.copy()
    a["Max capacity"] = pd.to_numeric(a["Max capacity"], errors="coerce")
    a["Rooms"] = pd.to_numeric(a["Rooms"], errors="coerce")
    fit = a[a["Max capacity"] >= S["cap_group"]].sort_values("Max capacity", ascending=False)
    return fit[["Type", "Name", "Rooms", "Max capacity"]].reset_index(drop=True)


def q_trend(long, S):
    """Report month vs same month last year, like for like (only hotels that reported both months)."""
    rm, ly = S["report_month"], S["report_month"] - 12
    h_now = set(long.loc[long.Month == rm, "Hotel"])
    h_ly = set(long.loc[long.Month == ly, "Hotel"])
    comp = h_now & h_ly
    base = long[long.Hotel.isin(comp)]

    def by(col, keys):
        rows = []
        for k in keys:
            now = int(base.loc[(base.Month == rm) & (base[col] == k), "rn"].sum())
            prev = int(base.loc[(base.Month == ly) & (base[col] == k), "rn"].sum())
            rows.append({col: k, str(rm): now, str(ly): prev, "Change": round(now / prev - 1, 3) if prev else None})
        tn = sum(r[str(rm)] for r in rows)
        tp = sum(r[str(ly)] for r in rows)
        rows.append({col: "Total", str(rm): tn, str(ly): tp, "Change": round(tn / tp - 1, 3) if tp else None})
        return pd.DataFrame(rows)

    # trailing 12 months vs prior 12, same comparable hotels
    t12 = int(base.loc[(base.Month > rm - 12) & (base.Month <= rm), "rn"].sum())
    p12 = int(base.loc[(base.Month > rm - 24) & (base.Month <= rm - 12), "rn"].sum())
    monthly = base.groupby("Month")["rn"].sum().reset_index()  # same comparable hotels every month
    monthly["Month"] = monthly["Month"].astype(str)
    monthly.columns = ["Month", "Group room nights (comparable hotels)"]
    return {
        "segment": by("Segment", SEGMENTS),
        "origin": by("Origin", ORIGINS),
        "comparable_hotels": len(comp),
        "excluded_hotels": sorted((h_now | h_ly) - comp),
        "ttm": t12, "prior_ttm": p12, "ttm_change": round(t12 / p12 - 1, 3) if p12 else None,
        "monthly": monthly,
    }


def q_boxscore(leads, S):
    d = last_12(leads, S)
    rows = []
    for sector, g in d.groupby("Sector"):
        n = len(g)
        won = int((g.Status == "Won").sum())
        rows.append({"Sector": sector, "Decided": n, "Won": won, "Lost": n - won,
                     "Win rate": round(won / n, 3) if n >= S["min_n"] else NOT_ENOUGH,
                     "Room nights won": int(g.loc[g.Status == "Won", "Actual room nights"].sum())})
    by_sector = pd.DataFrame(rows).sort_values("Decided", ascending=False).reset_index(drop=True)
    won = int((d.Status == "Won").sum())
    opn = leads[leads.Status == "Open"]
    totals = {"decided": len(d), "won": won, "lost": len(d) - won,
              "win_rate": round(won / len(d), 3) if len(d) >= S["min_n"] else NOT_ENOUGH,
              "rn_won": int(d.loc[d.Status == "Won", "Actual room nights"].sum()),
              "open": len(opn), "open_peak_rooms": int(opn["Peak rooms"].sum())}
    return by_sector, totals


def q_insights(leads, fit, occ, S, stale_days=90):
    """The 'so what' queries: room nights at stake, where and to whom we lose, which channels win,
    stale leads, and need months with an empty pipeline. Room nights for leads are estimates:
    peak rooms x nights."""
    rm = S["report_month"]
    rm_end = rm.to_timestamp(how="end")
    l = leads.assign(Nights=(leads["End date"] - leads["Start date"]).dt.days)
    l = l.assign(**{"Est. room nights": (l["Peak rooms"] * l["Nights"]).fillna(0).astype(int)})
    d = last_12(l, S)
    lost = d[d.Status == "Lost"]

    by_reason = (lost.groupby("Loss reason").agg(leads_lost=("LeadID", "size"), room_nights_lost=("Est. room nights", "sum"))
                 .sort_values("room_nights_lost", ascending=False).reset_index())
    pairs = (lost.dropna(subset=["Lost to"]).groupby(["Lost to", "Loss reason"])
             .agg(leads_lost=("LeadID", "size"), room_nights_lost=("Est. room nights", "sum"))
             .sort_values(["leads_lost", "room_nights_lost"], ascending=False).head(5).reset_index())

    src = []
    for source, g in d.groupby("Source"):
        n, won = len(g), int((g.Status == "Won").sum())
        src.append({"source": source, "decided": n, "won": won,
                    "win_rate": round(won / n, 3) if n >= S["min_n"] else NOT_ENOUGH,
                    "room_nights_won": int(g.loc[g.Status == "Won", "Actual room nights"].sum())})
    src = sorted(src, key=lambda r: (r["win_rate"] if not isinstance(r["win_rate"], str) else -1), reverse=True)

    o = l[(l.Status == "Open") & (l["Start date"] > rm_end)].copy()
    o["days_open"] = (rm_end.normalize() - o["Received"]).dt.days
    o["days_from_month_end_to_event"] = (o["Start date"] - rm_end.normalize()).dt.days
    stale = o[o["days_open"] > stale_days].sort_values("Start date")
    stale_list = [{"lead_id": r.LeadID, "organizer": r.Organizer, "sector": r.Sector,
                   "start_date": r["Start date"].strftime("%Y-%m-%d"),
                   "days_open": int(r.days_open), "days_from_month_end_to_event": int(r.days_from_month_end_to_event),
                   "est_room_nights": int(r["Est. room nights"])}
                  for _, r in stale.iterrows()]

    prio = fit[fit.Priority == "Yes"]
    won = l[l.Status == "Won"]
    months = []
    for k in range(1, 13):
        m = rm + k
        pm = prio[pd.to_datetime(prio["Start date"]).dt.to_period("M") == m]
        om = o[o["Start date"].dt.to_period("M") == m]
        wm = won[won["Start date"].dt.to_period("M") == m]
        months.append({"month": str(m), "need_month": m.month in S["need_months"],
                       "occupancy_last_year_pct": occ.get(m.month),
                       "groups_won": len(wm), "won_est_room_nights": int(wm["Est. room nights"].sum()),
                       "open_leads": len(om), "open_est_room_nights": int(om["Est. room nights"].sum()),
                       "priority_leads": len(pm), "priority_est_room_nights": int(pm["Est. room nights"].sum())})
    empty_need = [x["month"] for x in months if x["need_month"] and x["priority_leads"] == 0]

    return {
        "room_nights_note": "Room nights for lost and open leads are estimates: peak rooms x nights.",
        "lost_last_12_months": {"leads": len(lost), "est_room_nights": int(lost["Est. room nights"].sum()),
                                "by_reason": by_reason.to_dict("records"),
                                "top_competitor_reason_pairs": pairs.to_dict("records")},
        "win_rate_by_source_last_12_months": src,
        "stale_open_leads": {"rule_days_open_over": stale_days, "count": len(stale_list), "leads": stale_list},
        "priority_pipeline": {"leads": len(prio), "est_room_nights": int(prio["Est. room nights"].sum()),
                              "top_5_by_room_nights": prio.sort_values("Est. room nights", ascending=False).head(5)[
                                  ["Organizer", "Sector", "Start date", "Est. room nights", "Score"]].to_dict("records")},
        "next_12_months": months,
        "need_months_without_priority_leads": empty_need,
    }


# ------------------------------------------------------------------ data check
def data_check(leads, long, replaced, prospects, unmapped, dupes, hotels, S, raw):
    rm = S["report_month"]
    sub = set(long.loc[long.Month == rm, "Hotel"])
    missing = [h for h in hotels if h not in sub]
    rm_end = rm.to_timestamp(how="end")
    stale = leads[(leads.Status == "Open") & (leads["Start date"] <= rm_end)]
    no_reason = leads[(leads.Status == "Lost") & leads["Loss reason"].isna()]
    unm_sector = prospects[prospects["Sector"].astype(str).str.startswith("Unmapped")] if len(prospects) else []
    rows = [
        ("Structure", "All tabs and columns match the schema", "OK"),
        ("Rows read", f"Leads {raw['leads']}, Assets {raw['assets']}, Hotel responses {raw['responses']}, Imports {raw['imports']}", "OK"),
        ("Hotel submissions", f"{len(sub)} of {len(hotels)} hotels submitted for {rm}", "OK" if not missing else "CHECK"),
        ("Missing hotels", ", ".join(missing) or "None", "OK" if not missing else "CHECK"),
        ("Resubmissions", f"{replaced} earlier submission(s) replaced by the hotel's latest", "OK"),
        ("Open leads with past dates", ", ".join(stale["LeadID"]) or "None", "OK" if stale.empty else "CHECK"),
        ("Lost leads without a reason", ", ".join(no_reason["LeadID"]) or "None", "OK" if no_reason.empty else "CHECK"),
        ("Imports", f"{len(prospects)} prospects added; {dupes} already in Leads, dropped", "OK"),
        ("Import files without a mapping", ", ".join(unmapped) or "None", "OK" if not unmapped else "CHECK"),
        ("Import sectors without a mapping", str(len(unm_sector)), "OK" if not len(unm_sector) else "CHECK"),
    ]
    return pd.DataFrame(rows, columns=["Check", "Result", "Status"]), missing


# ------------------------------------------------------------------ run
def run(data_xlsx, responses_xlsx, imports_dir, config_path=HERE / "config_ixtapa.json", schema_path=HERE / "schema.json"):
    schema = json.loads(Path(schema_path).read_text())
    config = json.loads(Path(config_path).read_text())
    data, responses, imports = read_inputs(data_xlsx, responses_xlsx, imports_dir)
    check_structure(data, responses, schema)
    S = settings_dict(data["Settings"])
    leads = prepare_leads(data["Leads"])
    long, replaced = prepare_responses(responses["Form responses 1"])
    prospects, unmapped, dupes = prepare_imports(imports, config, leads)
    hotels = data["Lists"]["Hotels (form)"].dropna().tolist()
    assets = data["Assets"]

    need = q_need_periods(long, leads, S)
    occ = occupancy_by_calendar_month(data["PublicData"], S)
    fit = q_lead_fit(leads, prospects, assets, S, occ)
    loss, lost_to, n_lost = q_loss_reasons(leads, S)
    cap = q_capacity(assets, S)
    trend = q_trend(long, S)
    box, tot = q_boxscore(leads, S)
    insights = q_insights(leads, fit, occ, S)
    raw = {"leads": len(data["Leads"]), "assets": len(assets),
           "responses": len(responses["Form responses 1"]), "imports": sum(len(v) for v in imports.values())}
    check, missing = data_check(leads, long, replaced, prospects, unmapped, dupes, hotels, S, raw)
    return dict(S=S, config=config, need=need, fit=fit, loss=loss, lost_to=lost_to, n_lost=n_lost, cap=cap,
                trend=trend, box=box, tot=tot, insights=insights, check=check, missing=missing, hotels=hotels)
