"""Build 'Results YYYY-MM' from the engine's results, and check every number in the brief.

    python src/build_results.py        # runs the engine on data/, checks brief/brief_es.md, writes out/Results 2026-10.xlsx
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

import engine
import render_site

HERE = Path(__file__).parent
ROOT = HERE.parent
DATA = ROOT / "data"
OUT = ROOT / "out"
BANNER = "DATOS SINTÉTICOS · Prototipo · Todo es inventado salvo las 6,800 habitaciones de Ixtapa-Zihuatanejo (Datatur)"


# ------------------------------------------------------------------ results for the brief (the only thing Claude sees)
def brief_payload(R):
    S, t, tot, f = R["S"], R["trend"], R["tot"], R["fit"]
    seg = t["segment"].set_index("Segment")
    rm, ly = str(S["report_month"]), str(S["report_month"] - 12)
    top = f.iloc[0]
    return {
        "report_month": rm,
        "comparison_month": ly,
        "group_rn": {"month": int(seg.loc["Total", rm]), "same_month_last_year": int(seg.loc["Total", ly]),
                     "change": seg.loc["Total", "Change"], "comparable_hotels": t["comparable_hotels"],
                     "hotels_in_form": len(R["hotels"]), "excluded_hotels": t["excluded_hotels"],
                     "by_segment": t["segment"].to_dict("records"), "by_origin": t["origin"].to_dict("records"),
                     "trailing_12": t["ttm"], "prior_12": t["prior_ttm"], "trailing_12_change": t["ttm_change"]},
        "bids_last_12_months": {**tot, "by_sector": R["box"].to_dict("records")},
        "loss_reasons_last_12_months": R["loss"].to_dict("records"), "lost_to": R["lost_to"].to_dict("records"),
        "lead_targeting": {"candidates": len(f), "priority": int((f.Priority == "Yes").sum()),
                           "score_100": int((f.Score == 100).sum()), "threshold": S["threshold"],
                           "starting_within_3_months": f[pd.to_datetime(f["Start date"]) <= (S["report_month"] + 3).to_timestamp(how="end")][
                               ["Rank", "Organizer", "Type", "Sector", "Start date", "Attendees", "Peak rooms", "Score"]].to_dict("records"),
                           "top_10": f.head(10)[["Organizer", "Type", "Sector", "Start date", "Attendees",
                                                 "Peak rooms", "Score"]].to_dict("records")},
        "need_periods_next_6_months": R["need"].to_dict("records"),
        "need_months_setting": S["need_months"],
        "data_check_issues": R["check"].query("Status == 'CHECK'")[["Check", "Result"]].to_dict("records"),
        "insights": R["insights"],
        "delivery": {"brief_month": str(S["report_month"] + 1),
                     "act_by": (S["report_month"] + 1).to_timestamp(how="end").strftime("%Y-%m-%d")},
    }


# ------------------------------------------------------------------ number check
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def allowed_numbers(payload):
    vals = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            v = abs(float(x))
            vals.add(round(v, 3))
            if v < 1:  # shares and changes: allow them written as percentages
                vals.add(round(v * 100, 1))
                vals.add(float(round(v * 100)))
        elif isinstance(x, str):
            for m in NUM.findall(x):  # numbers inside text values, e.g. dates and months
                vals.add(round(float(m.replace(",", "")), 3))
                for part in m.split("-"):
                    if part:
                        vals.add(float(part))
    walk(payload)
    vals.update({12.0, 6.0, 3.0})  # the fixed windows: last 12 months, next 6 months, next 3 months
    return vals


def check_brief(text, payload):
    allowed = allowed_numbers(payload)
    rows = []
    text = re.sub(r"(?m)^\s*\d+\.\s", "", text)  # numbered-list markers are not figures
    for m in NUM.finditer(text):
        raw = m.group().rstrip(",.")
        v = round(float(raw.replace(",", "")), 3)
        rows.append({"Number in brief": raw, "Found in results": "Yes" if v in allowed else "NO"})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ workbook
def build_workbook(R, brief_text, check_df, path):
    S = R["S"]
    rm = str(S["report_month"])
    t = R["trend"]
    with pd.ExcelWriter(path, engine="xlsxwriter") as xw:
        wb = xw.book
        F = {
            "banner": wb.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#B42318", "font_name": "Arial"}),
            "title": wb.add_format({"bold": True, "font_size": 16, "font_name": "Arial"}),
            "h2": wb.add_format({"bold": True, "font_size": 12, "font_name": "Arial", "font_color": "#0F6E8C"}),
            "kpi": wb.add_format({"bold": True, "font_size": 20, "font_name": "Arial", "num_format": "#,##0", "align": "left"}),
            "kpi_pct": wb.add_format({"bold": True, "font_size": 20, "font_name": "Arial", "num_format": "0.0%", "align": "left"}),
            "kpi_lbl": wb.add_format({"font_size": 9, "font_name": "Arial", "font_color": "#5A6A7E", "text_wrap": True, "valign": "top"}),
            "hdr": wb.add_format({"bold": True, "bg_color": "#14253B", "font_color": "#FFFFFF", "font_name": "Arial", "text_wrap": True, "valign": "top"}),
            "txt": wb.add_format({"font_name": "Arial", "text_wrap": True, "valign": "top"}),
            "int": wb.add_format({"font_name": "Arial", "num_format": "#,##0"}),
            "pct": wb.add_format({"font_name": "Arial", "num_format": "0.0%;(0.0%);0.0%"}),
            "dec": wb.add_format({"font_name": "Arial", "num_format": "0.00"}),
            "note": wb.add_format({"font_name": "Arial", "italic": True, "font_color": "#5A6A7E"}),
            "base": wb.add_format({"font_name": "Arial"}),
        }

        def table(ws, df, row, col=0, fmts=None, widths=None):
            fmts = fmts or {}
            for j, c in enumerate(df.columns):
                ws.write(row, col + j, c, F["hdr"])
            for i, rec in enumerate(df.itertuples(index=False), start=1):
                for j, (c, v) in enumerate(zip(df.columns, rec)):
                    if v is None or (isinstance(v, float) and pd.isna(v)):
                        ws.write_blank(row + i, col + j, None, F["base"])
                    elif isinstance(v, str):
                        ws.write_string(row + i, col + j, v, F["txt"])
                    else:
                        ws.write_number(row + i, col + j, float(v), F[fmts.get(c, "int")])
            return row + len(df) + 1

        def sheet(name):
            ws = wb.add_worksheet(name)
            ws.write(0, 0, BANNER, F["banner"])
            ws.set_row(0, 20)
            return ws

        # ---------------- Dashboard
        ws = sheet("Dashboard")
        ws.set_column(0, 0, 26)
        ws.set_column(1, 8, 15)
        ws.write(2, 0, f"Ixtapa-Zihuatanejo · Business events results · {rm}", F["title"])
        seg = t["segment"].set_index("Segment")
        kpis = [
            ("Group room nights, " + rm + f" ({t['comparable_hotels']} comparable hotels)", seg.loc["Total", rm], "kpi"),
            ("Change vs same month last year", seg.loc["Total", "Change"], "kpi_pct"),
            ("Group room nights, last 12 months vs prior 12", t["ttm_change"], "kpi_pct"),
            ("Win rate, last 12 months", R["tot"]["win_rate"], "kpi_pct"),
            ("Room nights won, last 12 months", R["tot"]["rn_won"], "kpi"),
            ("Priority leads (score ≥ " + str(S["threshold"]) + ")", int((R["fit"].Priority == "Yes").sum()), "kpi"),
        ]
        for j, (lbl, v, f) in enumerate(kpis):
            c = j + 1
            ws.write_number(4, c, float(v), F[f])
            ws.write(5, c, lbl, F["kpi_lbl"])
        ws.write(4, 0, "Key numbers", F["h2"])
        ws.set_row(5, 42)

        r = 7
        ws.write(r, 0, "Group room nights by segment, like for like", F["h2"])
        r = table(ws, t["segment"], r + 1, fmts={"Change": "pct"})
        ws.write(r, 0, f"Excluded from the comparison (did not report both months): {', '.join(t['excluded_hotels']) or 'none'}", F["note"])
        seg_start, seg_end = 9, 9 + len(t["segment"]) - 2  # rows of the four segments, without Total

        r += 2
        ws.write(r, 0, "Group room nights by origin, like for like", F["h2"])
        r = table(ws, t["origin"], r + 1, fmts={"Change": "pct"})

        r += 1
        ws.write(r, 0, "Need periods: next 6 months", F["h2"])
        r = table(ws, R["need"], r + 1, fmts={"Index vs 12-month average": "dec"})

        r += 1
        ws.write(r, 0, "Loss reasons, last 12 months", F["h2"])
        loss_hdr = r + 1
        r = table(ws, R["loss"], r + 1, fmts={"Share": "pct"})
        loss_n = len(R["loss"])

        r += 1
        ws.write(r, 0, "Lost to, last 12 months", F["h2"])
        r = table(ws, R["lost_to"], r + 1)

        r += 1
        ws.write(r, 0, f"Capacity match: venues for {S['cap_group']} attendees or more", F["h2"])
        r = table(ws, R["cap"], r + 1)

        r += 1
        ws.write(r, 0, f"Group room nights by month, {t['comparable_hotels']} comparable hotels", F["h2"])
        mon_hdr = r + 1
        r = table(ws, t["monthly"], r + 1)
        mon_n = len(t["monthly"])

        # charts (to the right of the tables)
        ch = wb.add_chart({"type": "column"})
        ch.add_series({"name": "Group room nights", "categories": ["Dashboard", mon_hdr + 1, 0, mon_hdr + mon_n, 0],
                       "values": ["Dashboard", mon_hdr + 1, 1, mon_hdr + mon_n, 1], "fill": {"color": "#0F6E8C"}})
        ch.set_title({"name": "Group room nights by month"})
        ch.set_legend({"none": True})
        ch.set_size({"width": 620, "height": 300})
        ws.insert_chart(7, 10, ch)

        ch2 = wb.add_chart({"type": "column"})
        ch2.add_series({"name": rm, "categories": ["Dashboard", seg_start, 0, seg_end, 0],
                        "values": ["Dashboard", seg_start, 1, seg_end, 1], "fill": {"color": "#0F6E8C"}})
        ch2.add_series({"name": str(S["report_month"] - 12), "categories": ["Dashboard", seg_start, 0, seg_end, 0],
                        "values": ["Dashboard", seg_start, 2, seg_end, 2], "fill": {"color": "#C98A12"}})
        ch2.set_title({"name": "Segments: this month vs last year"})
        ch2.set_size({"width": 620, "height": 300})
        ws.insert_chart(23, 10, ch2)

        ch3 = wb.add_chart({"type": "bar"})
        ch3.add_series({"name": "Leads lost", "categories": ["Dashboard", loss_hdr + 1, 0, loss_hdr + loss_n, 0],
                        "values": ["Dashboard", loss_hdr + 1, 1, loss_hdr + loss_n, 1], "fill": {"color": "#B42318"}})
        ch3.set_title({"name": "Why we lost, last 12 months"})
        ch3.set_legend({"none": True})
        ch3.set_y_axis({"reverse": True})
        ch3.set_size({"width": 620, "height": 300})
        ws.insert_chart(39, 10, ch3)

        # ---------------- Lead targeting
        ws = sheet("Lead targeting")
        ws.write(2, 0, f"Lead targeting: open leads and imported prospects, ranked by lead fit (score ≥ {S['threshold']} = priority)", F["title"])
        ws.write(3, 0, f"Score out of 100. Sector ({S['w_sector']}): plan target full points, secondary target half. "
                       f"Need period ({S['w_need']}): scaled by the event month's hotel occupancy over the last 12 months, weakest month full points, strongest 0. "
                       f"Capacity ({S['w_capacity']}): full up to {S['comfort_rooms']} peak rooms and {S['comfort_att']} attendees, falling to 0 at "
                       f"{S['max_peak']} rooms and the largest venue's capacity. Ties ranked by estimated room nights.", F["note"])
        table(ws, R["fit"], 5, fmts={})
        ws.set_column(0, 0, 6)
        ws.set_column(1, 1, 32)
        ws.set_column(2, 3, 18)
        ws.set_column(4, 12, 11)
        ws.set_column(13, 13, 62)
        ws.freeze_panes(6, 2)

        # ---------------- Bid results
        ws = sheet("Bid results")
        tot = R["tot"]
        ws.write(2, 0, "Bid results boxscore: decisions in the last 12 months", F["title"])
        box_tot = pd.DataFrame([{"Decided": tot["decided"], "Won": tot["won"], "Lost": tot["lost"],
                                 "Win rate": tot["win_rate"], "Room nights won": tot["rn_won"],
                                 "Open leads": tot["open"], "Open peak rooms": tot["open_peak_rooms"]}])
        r = table(ws, box_tot, 4, fmts={"Win rate": "pct"})
        r = table(ws, R["box"], r + 2, fmts={"Win rate": "pct"})
        ws.write(r + 1, 0, f"Win rate shows '{engine.NOT_ENOUGH}' below {S['min_n']} decisions.", F["note"])
        ws.set_column(0, 0, 24)
        ws.set_column(1, 6, 14)

        # ---------------- Brief
        ws = sheet("Brief")
        ws.set_column(0, 0, 110)
        row = 4
        if brief_text is None:
            ws.write(2, 0, "Informe retenido: no pasó la verificación de cifras. El operador lo revisa antes de enviarlo.", F["title"])
            brief_text = ""
        else:
            ws.write(2, 0, "Informe del mes (redactado por Claude a partir de los resultados; cada cifra verificada)", F["title"])
        for line in brief_text.strip().splitlines():
            if line.startswith("#"):
                ws.write(row, 0, line.lstrip("# ").strip(), F["h2"])
            elif line.strip():
                ws.write(row, 0, line.replace("**", ""), F["txt"])
            row += 1
        row += 1
        ws.write(row, 0, "Number check", F["h2"])
        ws.set_column(1, 1, 18)
        table(ws, check_df, row + 1)

        # ---------------- Data check
        ws = sheet("Data check")
        ws.write(2, 0, "Data check", F["title"])
        table(ws, R["check"], 4)
        ws.set_column(0, 0, 32)
        ws.set_column(1, 1, 70)
        ws.set_column(2, 2, 10)


def step(n, text):
    print(f"[{n}/7] {text}", flush=True)


def main():
    import os
    OUT.mkdir(exist_ok=True)
    mode = os.environ.get("BRIEF_MODE") or ("api" if os.environ.get("ANTHROPIC_API_KEY") else "file")

    step(1, "Leer los archivos del destino (data/)")
    step(2, "Revisar la estructura contra el esquema")
    try:
        R = engine.run(DATA / "Data (SINTETICO).xlsx", DATA / "Hotel responses (SINTETICO).xlsx", DATA / "imports")
    except engine.StructureError as e:
        print(f"   ESTRUCTURA CAMBIADA: {e}\n   La corrida se detiene; no se publica nada.")
        sys.exit(2)
    chk = R["check"]
    print("   " + render_site.tr_check(chk.loc[chk.Check == "Rows read", "Result"].iloc[0]) + " · estructura OK")
    step(3, "Revisar los datos")
    for r in chk.query("Status == 'CHECK'").itertuples():
        print(f"   alerta: {render_site.CHECK.get(r.Check, r.Check)}: {render_site.tr_check(r.Result)}")
    step(4, "Correr las 6 consultas fijas")
    payload = brief_payload(R)
    (OUT / "brief_payload.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str))
    print(f"   {len(R['fit'])} candidatos puntuados; {payload['lead_targeting']['priority']} prioritarios")

    step(5, "Redactar el informe" + (" con la API de Claude" if mode == "api" else " (archivo brief/brief_es.md)"))
    if mode == "api":
        import brief_api
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("   Falta el secreto ANTHROPIC_API_KEY en el repositorio. La corrida se detiene.")
        try:
            brief, info = brief_api.draft_brief(payload, "Ixtapa-Zihuatanejo", lambda t: check_brief(t, payload))
        except RuntimeError as e:  # API down or refused: results still go out, the brief is held
            print(f"   La API de Claude no respondió: {e}")
            brief, info = None, {"model": brief_api.DEFAULT_MODEL, "attempts": 0, "bad_numbers": [], "error": str(e)}
        source = f"Redactado por la API de Claude ({info['model']}) a partir de los resultados de las consultas"
    else:
        brief = (ROOT / "brief" / "brief_es.md").read_text()
        info = {"model": None, "attempts": 0, "bad_numbers": []}
        source = "Redactado por Claude a partir de los resultados de las consultas"

    step(6, "Verificar cada cifra del informe")
    if brief is not None:
        check = check_brief(brief, payload)
        bad = check[check["Found in results"] != "Yes"]
        if len(bad):
            brief = None
            info["bad_numbers"] = bad["Number in brief"].tolist()
    if brief is None:
        check = pd.DataFrame([{"Number in brief": b, "Found in results": "NO"} for b in info["bad_numbers"]],
                             columns=["Number in brief", "Found in results"])
        why = f"cifras no encontradas en los resultados: {info['bad_numbers']}" if info["bad_numbers"] else "la API no respondió"
        print(f"   INFORME RETENIDO: {why}")
    else:
        print(f"   {len(check)} de {len(check)} cifras encontradas en los resultados")
        (OUT / "brief_es.md").write_text(brief, encoding="utf-8")

    step(7, "Publicar los resultados")
    out = OUT / f"Results {R['S']['report_month']}.xlsx"
    build_workbook(R, brief, check, out)
    site = OUT / "site"
    site.mkdir(exist_ok=True)
    meta = run_meta()
    meta["brief_source"] = os.environ.get("BRIEF_SOURCE_LABEL", source)
    (site / "index.html").write_text(render_site.render(R, brief, check, meta), encoding="utf-8")
    print(f"   {out.name} y site/index.html")
    write_summary(R, payload, brief, check, info, meta)


def write_summary(R, payload, brief, check, info, meta):
    """Markdown summary for the GitHub Actions run page."""
    import os
    chk = R["check"]
    g = payload["group_rn"]
    lines = [
        "## Corrida: Ixtapa-Zihuatanejo · " + payload["report_month"] + " · DATOS SINTÉTICOS",
        "",
        "| Paso | Resultado |", "|---|---|",
        f"| Leer y revisar estructura | ✅ {render_site.tr_check(chk.loc[chk.Check == 'Rows read', 'Result'].iloc[0])} |",
        f"| Revisar los datos | {'⚠️' if (chk.Status == 'CHECK').any() else '✅'} {int((chk.Status == 'CHECK').sum())} alertas |",
        f"| 6 consultas fijas | ✅ {payload['lead_targeting']['priority']} prospectos prioritarios |",
        f"| Informe | {'✅ ' + meta['brief_source'] if brief else '⛔ retenido'} |",
        f"| Verificación de cifras | {'✅ ' + str(len(check)) + ' de ' + str(len(check)) if brief else ('⛔ no encontradas: ' + ', '.join(info['bad_numbers']) if info['bad_numbers'] else '⛔ la API no respondió')} |",
        "",
        f"Noches de grupo {payload['report_month']}: **{g['month']:,}** ({g['change']*100:+.1f}% contra el mismo mes del año pasado, {g['comparable_hotels']} hoteles comparables).",
    ]
    if brief:
        lines += ["", "<details><summary>Informe</summary>", "", brief, "", "</details>"]
    text = "\n".join(lines) + "\n"
    (OUT / "run_summary.md").write_text(text, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(text)


def run_meta():
    import os
    import subprocess
    sha = os.environ.get("GITHUB_SHA", "")[:7]
    if not sha:
        try:
            sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        except OSError:
            sha = ""
    return {
        "version": sha or "local",
        "data_source": os.environ.get("DATA_SOURCE_LABEL", "copias de los archivos del destino guardadas en el repositorio"),
    }


if __name__ == "__main__":
    main()
