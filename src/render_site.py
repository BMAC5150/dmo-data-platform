"""Render the demo web page (Spanish) from the engine's results.

One self-contained HTML file: Corrida (the run), Tablero (dashboard), Prospección
(lead targeting) and Informe (the brief). Every number comes from the results
dict; nothing is typed by hand. Charts are inline SVG with hover titles, and
each chart has a table beside it.
"""
import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"   # validated categorical slots 1-3

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MES_CORTO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
SEG = {"Association": "Asociaciones", "Corporate": "Corporativo", "Incentive": "Incentivos",
       "Government & other": "Gobierno y otros", "Total": "Total"}
ORI = {"Domestic": "Nacional", "International": "Internacional", "Total": "Total"}
SECTOR = {"Medical association": "Asociación médica", "Insurance & finance": "Seguros y finanzas",
          "Mexican corporate": "Corporativo mexicano", "Government": "Gobierno", "Pharma": "Farmacéutico",
          "Education": "Educación", "Agriculture": "Agricultura", "Religious": "Religioso", "Sports": "Deportes"}
LOSS = {"Price": "Precio", "Air access": "Acceso aéreo", "Safety perception": "Percepción de seguridad",
        "Dates not available": "Fechas no disponibles", "Venue too small": "Sede insuficiente",
        "Event cancelled": "Evento cancelado", "Destination profile": "Perfil del destino"}
TIPO = {"Lead": "Oportunidad", "Prospect (import)": "Prospecto importado"}
ASSET = {"Hotel": "Hotel", "Venue": "Sede", "Supplier": "Proveedor"}
CHECK = {"Structure": "Estructura", "Rows read": "Filas leídas", "Hotel submissions": "Envíos de hoteles",
         "Missing hotels": "Hoteles sin enviar", "Resubmissions": "Reenvíos",
         "Open leads with past dates": "Oportunidades abiertas con fecha pasada",
         "Lost leads without a reason": "Perdidas sin motivo", "Imports": "Listas importadas",
         "Import files without a mapping": "Archivos sin mapeo", "Import sectors without a mapping": "Sectores sin mapeo"}


def esc(x):
    return html.escape(str(x))


def n0(x):
    return f"{int(round(float(x))):,}"


def pct(x, sign=False):
    v = float(x) * 100
    return (f"{v:+.1f}%" if sign else f"{v:.1f}%").replace("+-", "-")


def mes(period, corto=False):
    p = pd.Period(str(period), "M")
    return f"{(MES_CORTO if corto else MESES)[p.month - 1]} {p.year}"


def fecha(s):
    d = pd.Timestamp(s)
    return f"{d.day} {MES_CORTO[d.month - 1]} {d.year}"


def tr_check(result):
    r = str(result)
    r = r.replace("All tabs and columns match the schema", "Todas las pestañas y columnas coinciden con el esquema")
    r = re.sub(r"(\d+) of (\d+) hotels submitted for (\S+)", lambda m: f"{m[1]} de {m[2]} hoteles enviaron {mes(m[3])}", r)
    r = re.sub(r"(\d+) earlier submission\(s\) replaced by the hotel's latest",
               lambda m: f"{m[1]} envío anterior reemplazado por el más reciente del hotel", r)
    r = re.sub(r"(\d+) prospects added; (\d+) already in Leads, dropped",
               lambda m: f"{m[1]} prospectos añadidos; {m[2]} ya eran oportunidades y se descartaron", r)
    r = r.replace("Leads", "Oportunidades").replace("Assets", "Activos").replace("Hotel responses", "Respuestas de hoteles").replace("Imports", "Importaciones")
    return "Ninguno" if r == "None" else r


# ------------------------------------------------------------------ SVG charts
def col_chart(labels, values, highlight=(), w=960, h=280, title=""):
    pad_l, pad_b, pad_t = 48, 34, 16
    vmax = max(values) * 1.12
    step = 10 ** (len(str(int(vmax))) - 1)
    tick = step if vmax / step >= 3 else step / 2
    plot_w, plot_h = w - pad_l - 8, h - pad_b - pad_t
    bw = min(24, plot_w / len(values) * 0.62)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">']
    t = 0
    while t <= vmax:
        y = pad_t + plot_h - t / vmax * plot_h
        out.append(f'<line x1="{pad_l}" x2="{w-8}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                   f'<text x="{pad_l-6}" y="{y+4:.1f}" class="tick" text-anchor="end">{n0(t)}</text>')
        t += tick
    for i, (lab, v) in enumerate(zip(labels, values)):
        cx = pad_l + plot_w / len(values) * (i + .5)
        bh = v / vmax * plot_h
        y = pad_t + plot_h - bh
        r = min(4, bw / 2)
        path = (f"M{cx-bw/2:.1f},{pad_t+plot_h:.1f} V{y+r:.1f} Q{cx-bw/2:.1f},{y:.1f} {cx-bw/2+r:.1f},{y:.1f} "
                f"H{cx+bw/2-r:.1f} Q{cx+bw/2:.1f},{y:.1f} {cx+bw/2:.1f},{y+r:.1f} V{pad_t+plot_h:.1f} Z")
        op = "1" if (not highlight or i in highlight) else ".45"
        out.append(f'<g class="hit"><title>{esc(lab)}: {n0(v)} noches</title>'
                   f'<rect x="{cx-plot_w/len(values)/2:.1f}" y="{pad_t}" width="{plot_w/len(values):.1f}" height="{plot_h}" fill="transparent"/>'
                   f'<path d="{path}" fill="{BLUE}" opacity="{op}"/></g>')
        if i in highlight:
            out.append(f'<text x="{cx:.1f}" y="{y-6:.1f}" class="val" text-anchor="middle">{n0(v)}</text>')
        if i % 3 == 0 or i == len(values) - 1:
            out.append(f'<text x="{cx:.1f}" y="{h-pad_b+16}" class="tick" text-anchor="middle">{esc(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


def hbar_chart(labels, series, names=None, colors=(BLUE, ORANGE), w=520, row=30, fmt=n0, title=""):
    """Horizontal bars. series: list of value lists (1 or 2). Value at each bar tip."""
    pad_l, pad_r = 170, 56
    k = len(series)
    h = len(labels) * row * (1 if k == 1 else 1.5) + 12
    vmax = max(max(s) for s in series) or 1
    plot_w = w - pad_l - pad_r
    bh = 12 if k == 2 else 16
    out = [f'<svg viewBox="0 0 {w} {h:.0f}" role="img" aria-label="{esc(title)}">']
    for i, lab in enumerate(labels):
        y0 = 6 + i * row * (1 if k == 1 else 1.5)
        out.append(f'<text x="{pad_l-10}" y="{y0 + (row*(1 if k==1 else 1.5))/2 + 4:.1f}" class="lab" text-anchor="end">{esc(lab)}</text>')
        for j, s in enumerate(series):
            v = s[i]
            bw = max(2, v / vmax * plot_w)
            y = y0 + 6 + j * (bh + 2)
            r = min(4, bw / 2)
            path = (f"M{pad_l},{y:.1f} H{pad_l+bw-r:.1f} Q{pad_l+bw:.1f},{y:.1f} {pad_l+bw:.1f},{y+r:.1f} "
                    f"V{y+bh-r:.1f} Q{pad_l+bw:.1f},{y+bh:.1f} {pad_l+bw-r:.1f},{y+bh:.1f} H{pad_l} Z")
            nm = f"{names[j]}: " if names else ""
            out.append(f'<g class="hit"><title>{esc(lab)} · {esc(nm)}{fmt(v)}</title><path d="{path}" fill="{colors[j]}"/>'
                       f'<text x="{pad_l+bw+6:.1f}" y="{y+bh-2:.1f}" class="val">{fmt(v)}</text></g>')
    out.append("</svg>")
    return "".join(out)


def legend(items):
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{c}"></i>{esc(n)}</span>' for n, c in items) + "</div>"


def table(headers, rows, num=()):
    th = "".join(f'<th class="{"num" if i in num else ""}">{esc(h)}</th>' for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(f'<td class="{"num" if i in num else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
                   for r in rows)
    return f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


# ------------------------------------------------------------------ brief markdown
def md(text):
    out, in_ol, in_ul = [], False, False
    def inline(s):
        s = esc(s)
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    def close():
        nonlocal in_ol, in_ul
        if in_ol: out.append("</ol>"); in_ol = False
        if in_ul: out.append("</ul>"); in_ul = False
    rows = []
    def flush_table():
        if not rows:
            return
        head, body = rows[0], rows[1:]
        def cell(c, tag, i):
            cls = ' class="num"' if i > 0 else ""
            if tag == "td" and i == 3 and c.startswith("-"):
                cls = ' class="num neg"'
            return f"<{tag}{cls}>{inline(c)}</{tag}>"
        out.append('<div class="tw"><table class="score"><thead><tr>' + "".join(cell(c, "th", i) for i, c in enumerate(head))
                   + "</tr></thead><tbody>" + "".join("<tr>" + "".join(cell(c, "td", i) for i, c in enumerate(r)) + "</tr>" for r in body)
                   + "</tbody></table></div>")
        rows.clear()
    for line in text.strip().splitlines():
        s = line.strip()
        if s.startswith("|"):
            close()
            if not set(s.replace("|", "").strip()) <= set("-: "):
                rows.append([c.strip() for c in s.strip("|").split("|")])
            continue
        flush_table()
        if not s:
            close(); continue
        if s.startswith("# "):
            close(); out.append(f"<h2>{inline(s[2:])}</h2>")
        elif s.startswith("## "):
            close(); out.append(f"<h3>{inline(s[3:])}</h3>")
        elif re.match(r"\d+\.\s", s):
            if not in_ol: close(); out.append("<ol>"); in_ol = True
            out.append(f"<li>{inline(re.sub(r'^\d+\.\s', '', s))}</li>")
        elif s.startswith("- "):
            if not in_ul: close(); out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline(s[2:])}</li>")
        else:
            close(); out.append(f"<p>{inline(s)}</p>")
    flush_table()
    close()
    return "\n".join(out)


# ------------------------------------------------------------------ page
def render(R, brief_text, check_df, meta):
    S, t, tot, f = R["S"], R["trend"], R["tot"], R["fit"]
    rm = S["report_month"]
    ly = rm - 12
    seg = t["segment"].set_index("Segment")
    prio = f[f.Priority == "Yes"]
    now = datetime.now(ZoneInfo("America/Mexico_City"))

    # --- Corrida
    chk = R["check"]
    n_alert = int((chk.Status == "CHECK").sum())
    n_ok = int((check_df["Found in results"] == "Yes").sum()) if len(check_df) else 0
    held = brief_text is None
    steps = [
        ("Leer los archivos", tr_check(chk.loc[chk.Check == "Rows read", "Result"].iloc[0]), "ok"),
        ("Revisar la estructura", "Todas las pestañas y columnas coinciden con el esquema; si algo cambia, la corrida se detiene", "ok"),
        ("Revisar los datos", f"{n_alert} alertas para el equipo (ver abajo); no detienen la corrida", "warn" if n_alert else "ok"),
        ("Correr las 6 consultas fijas", "Temporadas de necesidad, ajuste de prospectos, motivos de pérdida, capacidad, tendencia de noches de grupo, resultados de propuestas", "ok"),
        ("Redactar el informe", meta["brief_source"], "ok"),
        ("Verificar cada cifra del informe",
         ("Informe retenido: cifras no encontradas en los resultados (" + ", ".join(check_df["Number in brief"].astype(str)) + ")"
          if len(check_df) else "Informe retenido: la API de Claude no respondió") if held
         else f"{n_ok} de {len(check_df)} cifras encontradas en los resultados", "warn" if held else "ok"),
        ("Publicar los resultados", f"Esta página y el libro de resultados de {mes(rm)}, con fecha y sin sobrescribir", "ok"),
    ]
    step_html = "".join(
        f'<li class="{st}"><b>{esc(a)}</b><span>{esc(b)}</span></li>' for a, b, st in steps)
    chk_rows = [[esc(CHECK.get(r.Check, r.Check)), esc(tr_check(r.Result)),
                 '<span class="pill ok">OK</span>' if r.Status == "OK" else '<span class="pill warn">Revisar</span>']
                for r in chk.itertuples()]
    corrida = f"""
<section id="corrida" class="tab">
  <h2>Cómo se generó esta página</h2>
  <p class="lead">Un script fijo y probado lee los archivos del destino, calcula cada número y publica los resultados. Nadie escribe cifras a mano. Claude solo redacta el informe, a partir de los resultados.</p>
  <div class="grid2">
    <div class="card"><h3>La corrida, paso a paso</h3><ol class="steps">{step_html}</ol></div>
    <div class="card"><h3>Datos que leyó</h3>
      <ul class="files">
        <li><b>Data</b><span>Oportunidades, activos, datos públicos, listas y parámetros (Google Sheet)</span></li>
        <li><b>Respuestas de hoteles</b><span>Formulario mensual de {len(R['hotels'])} hoteles (Google Form)</span></li>
        <li><b>Importaciones</b><span>Lista de prospectos exportada de Cvent</span></li>
      </ul>
      <p class="small">Fuente de esta corrida: {esc(meta['data_source'])}</p>
      <h3>Revisión de datos</h3>
      {table(["Revisión", "Resultado", "Estado"], chk_rows)}
    </div>
  </div>
</section>"""

    # --- Tablero
    kpis = [
        (n0(seg.loc["Total", str(rm)]), f"Noches de grupo en {mes(rm)}", f"{t['comparable_hotels']} hoteles comparables"),
        (pct(seg.loc["Total", "Change"], True), f"Contra {mes(ly)}", "mismos hoteles, ambos meses"),
        (pct(t["ttm_change"], True), "Últimos 12 meses", "contra los 12 anteriores"),
        (pct(tot["win_rate"]), "Tasa de éxito", f"{tot['won']} de {tot['decided']} decisiones, 12 meses"),
        (n0(tot["rn_won"]), "Noches ganadas", "grupos ganados, 12 meses"),
        (str(len(prio)), "Prospectos prioritarios", f"puntaje de {S['threshold']} o más"),
    ]
    kpi_html = "".join(f'<div class="kpi"><div class="kv">{a}</div><div class="kl">{esc(b)}</div><div class="ks">{esc(c)}</div></div>'
                       for a, b, c in kpis)
    mon = t["monthly"]
    labels = [mes(m, True) for m in mon["Month"]]
    vals = mon.iloc[:, 1].tolist()
    hl = {len(vals) - 1, len(vals) - 13} if len(vals) >= 13 else {len(vals) - 1}
    segs = [s for s in seg.index if s != "Total"]
    seg_chart = hbar_chart([SEG[s] for s in segs], [[seg.loc[s, str(rm)] for s in segs], [seg.loc[s, str(ly)] for s in segs]],
                           names=[mes(rm), mes(ly)], title="Noches de grupo por segmento")
    seg_rows = [[esc(SEG[s]), n0(seg.loc[s, str(rm)]), n0(seg.loc[s, str(ly)]),
                 f'<span class="{"neg" if seg.loc[s, "Change"] < 0 else ""}">{pct(seg.loc[s, "Change"], True)}</span>'] for s in seg.index]
    ori = t["origin"].set_index("Origin")
    ori_rows = [[esc(ORI[o]), n0(ori.loc[o, str(rm)]), n0(ori.loc[o, str(ly)]),
                 f'<span class="{"neg" if ori.loc[o, "Change"] < 0 else ""}">{pct(ori.loc[o, "Change"], True)}</span>'] for o in ori.index]
    loss = R["loss"]
    loss_chart = hbar_chart([LOSS.get(x, x) for x in loss["Loss reason"]], [loss["Leads lost"].tolist()], title="Motivos de pérdida")
    need = R["need"]
    need_rows = [[f'<span class="nw">{esc(mes(r["Month"]))}</span>', n0(r["Group room nights, same month last year"]), f'{r["Index vs 12-month average"]:.2f}',
                  "Sí" if r["Need period (Settings)"] == "Yes" else "No", n0(r["Groups won for the month"]),
                  n0(r["Peak rooms won"]), n0(r["Open leads for the month"])] for _, r in need.iterrows()]
    lost_rows = [[esc("Otro" if r["Lost to"] == "Other" else r["Lost to"]), n0(r["Leads lost"])] for _, r in R["lost_to"].iterrows()]
    cap_rows = [[esc(r["Name"]), esc(ASSET.get(r["Type"], r["Type"])), n0(r["Max capacity"]),
                 n0(r["Rooms"]) if r["Rooms"] else "—"] for _, r in R["cap"].iterrows()]
    box_rows = [[esc(SECTOR.get(r["Sector"], r["Sector"])), n0(r["Decided"]), n0(r["Won"]), n0(r["Lost"]),
                 "Datos insuficientes" if isinstance(r["Win rate"], str) else pct(r["Win rate"]), n0(r["Room nights won"])]
                for _, r in R["box"].iterrows()]
    excl = ", ".join(t["excluded_hotels"])
    tablero = f"""
<section id="tablero" class="tab">
  <div class="kpis">{kpi_html}</div>
  <div class="card wide"><h3>Noches de grupo por mes</h3>
    <p class="small">Los mismos {t['comparable_hotels']} hoteles en todos los meses. Resaltados: {mes(rm)} y {mes(ly)}.</p>
    <div class="chart">{col_chart(labels, vals, hl, title="Noches de grupo por mes")}</div></div>
  <div class="grid2">
    <div class="card"><h3>Segmentos: {mes(rm)} contra {mes(ly)}</h3>
      {legend([(mes(rm), BLUE), (mes(ly), ORANGE)])}
      <div class="chart">{seg_chart}</div>
      {table(["Segmento", mes(rm), mes(ly), "Cambio"], seg_rows, num=(1, 2, 3))}
      <p class="small">Mismos {t['comparable_hotels']} hoteles en ambos meses.{f' Fuera de la comparación: {esc(excl)} (no envió los dos meses).' if excl else ''}</p></div>
    <div class="card"><h3>Por qué perdimos (12 meses)</h3>
      <div class="chart">{loss_chart}</div>
      <p class="small">{tot['lost']} grupos perdidos en los últimos 12 meses.</p>
      <h3>Destinos que nos ganaron</h3>{table(["Destino", "Grupos"], lost_rows, num=(1,))}</div>
  </div>
  <div class="card"><h3>Temporadas de necesidad: próximos 6 meses</h3>
    {table(["Mes", "Noches de grupo hace un año", "Índice", "Necesidad", "Grupos ganados", "Hab. pico ganadas", "Oportunidades abiertas"], need_rows, num=(1, 2, 4, 5, 6))}
    <p class="small">Índice: noches de grupo del mismo mes del año pasado contra el promedio mensual de los últimos 12 meses. Necesidad: meses marcados en los parámetros.</p></div>
  <div class="grid2">
    <div class="card"><h3>Resultados de propuestas por sector (12 meses)</h3>
      {table(["Sector", "Decididas", "Ganadas", "Perdidas", "Tasa de éxito", "Noches ganadas"], box_rows, num=(1, 2, 3, 4, 5))}
      <p class="small">La tasa de éxito se muestra con {S['min_n']} decisiones o más.</p></div>
    <div class="card"><h3>Origen de las noches de grupo</h3>{table(["Origen", mes(rm), mes(ly), "Cambio"], ori_rows, num=(1, 2, 3))}
      <h3 style="margin-top:18px">Sedes para {S['cap_group']} asistentes o más</h3>{table(["Sede", "Tipo", "Capacidad máx.", "Habitaciones"], cap_rows, num=(2, 3))}</div>
  </div>
</section>"""

    # --- Prospección
    def razon(r):
        sec = "Sector meta del plan" if r["Sector pts"] >= S["w_sector"] else (
            "Sector secundario" if r["Sector pts"] > 0 else "Fuera de los sectores meta")
        o = r["Occupancy last year"]
        d = pd.Timestamp(r["Start date"])
        need = f"{MES_CORTO[d.month-1]}: ocupación {o:.0f}%" if pd.notna(o) else ""
        if r["Capacity pts"] >= S["w_capacity"]:
            cap = "cabe con holgura"
        elif r["Capacity pts"] > 0:
            cap = "cabe justo"
        else:
            cap = "demasiado grande"
        return " · ".join(x for x in [sec, need, cap] if x)

    def score_cell(r):
        segs_ = [(r["Sector pts"], BLUE, "Sector"), (r["Need period pts"], ORANGE, "Temporada"), (r["Capacity pts"], AQUA, "Capacidad")]
        bars = "".join(f'<i style="width:{v}%;background:{c}" title="{n}: {v}"></i>' for v, c, n in segs_ if v > 0)
        return (f'<div class="sc"><b>{int(r["Score"])}</b><span class="stack">{bars}</span>'
                f'<em>{int(r["Sector pts"])} · {int(r["Need period pts"])} · {int(r["Capacity pts"])}</em></div>')

    def lead_rows(df):
        return [[str(int(r["Rank"])), f'<b>{esc(r["Organizer"])}</b><br><span class="small">{esc(TIPO.get(r["Type"], r["Type"]))}</span>',
                 esc(SECTOR.get(r["Sector"], r["Sector"])), f'<span class="nw">{esc(fecha(r["Start date"]))}</span>', n0(r["Attendees"]), n0(r["Peak rooms"]),
                 n0(r["Est. room nights"]), score_cell(r), esc(razon(r))] for _, r in df.iterrows()]
    hdr = ["#", "Organización", "Sector", "Llegada", "Asistentes", "Hab. pico", "Noches est.", "Puntaje", "Por qué"]
    rest = f[f.Priority != "Yes"]
    prospeccion = f"""
<section id="prospeccion" class="tab">
  <h2>{len(prio)} prospectos prioritarios</h2>
  <p class="lead">Oportunidades abiertas y prospectos importados, ordenados por ajuste al destino. Prioritario: puntaje de {S['threshold']} o más.</p>
  <div class="card rule">
    <div><span class="sw" style="background:{BLUE}"></span><b>Sector ({S['w_sector']})</b> Sector meta del plan: {S['w_sector']}; secundario: {S['w_sector']//2}.</div>
    <div><span class="sw" style="background:{ORANGE}"></span><b>Temporada ({S['w_need']})</b> Según la ocupación hotelera del mes del evento en los últimos 12 meses: el mes más flojo recibe {S['w_need']}, el más lleno 0.</div>
    <div><span class="sw" style="background:{AQUA}"></span><b>Capacidad ({S['w_capacity']})</b> Completo hasta {n0(S['comfort_rooms'])} habitaciones pico y {n0(S['comfort_att'])} asistentes; baja a 0 en {n0(S['max_peak'])} habitaciones o la capacidad de la sede más grande.</div>
  </div>
  {table(hdr, lead_rows(prio), num=(0, 4, 5, 6))}
  <details><summary>Ver los otros {len(rest)} candidatos</summary>{table(hdr, lead_rows(rest), num=(0, 4, 5, 6))}</details>
</section>"""

    # --- Informe
    if held:
        informe = f"""
<section id="informe" class="tab">
  <div class="card verify"><p><span class="pill warn">Informe retenido</span></p>
    <p>{(f'El borrador de este mes usó cifras que no aparecen en los resultados ({esc(", ".join(check_df["Number in brief"].astype(str)))}), así que no se publica.') if len(check_df) else 'La API de Claude no respondió durante la corrida.'} El operador lo revisa; el tablero y la prospección sí se publican.</p></div>
</section>"""
    else:
        chk_tbl = table(["Cifra en el informe", "¿En los resultados?"],
                        [[esc(r["Number in brief"]), "Sí" if r["Found in results"] == "Yes" else "<b>NO</b>"] for _, r in check_df.iterrows()])
        informe = f"""
<section id="informe" class="tab">
  <div class="brief card">{md(brief_text)}</div>
  <div class="card verify">
    <p><span class="pill ok">✓ {n_ok} de {len(check_df)} cifras verificadas</span></p>
    <p class="small">{esc(meta['brief_source'])}. Claude recibe solo los resultados de las consultas, nunca los datos crudos ni datos personales. Antes de publicar, el script busca cada cifra del informe en los resultados; si alguna no aparece, el informe se retiene.</p>
    <details><summary>Ver la verificación cifra por cifra</summary>{chk_tbl}</details>
  </div>
</section>"""

    return PAGE.format(
        rm=esc(mes(rm)), dmo="Ixtapa-Zihuatanejo",
        stamp=esc(f"{now.day} {MES_CORTO[now.month-1]} {now.year}, {now:%H:%M} hora del centro de México"),
        version=esc(meta["version"]), source=esc(meta["data_source"]),
        corrida=corrida, tablero=tablero, prospeccion=prospeccion, informe=informe)


PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{dmo} · Resultados de {rm} · DATOS SINTÉTICOS</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>
:root {{ --bg:#f3f5f7; --surface:#fcfcfb; --ink:#14253b; --muted:#52606f; --line:#d5dde6; --accent:#0f6e8c; --warn:#b54708; --warn-soft:#fff4e5; --ok:#067647; --ok-soft:#e8f6ee; --red:#b42318; color-scheme: light; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 "IBM Plex Sans", "Segoe UI", Arial, sans-serif; }}
.banner {{ background:var(--red); color:#fff; font-weight:600; text-align:center; padding:7px 12px; font-size:13px; letter-spacing:.02em; }}
header {{ max-width:1240px; margin:0 auto; padding:22px 18px 4px; }}
.eyebrow {{ font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--accent); font-weight:600; }}
h1 {{ font:800 clamp(24px,3.6vw,34px)/1.1 Archivo, Arial, sans-serif; margin:4px 0 6px; }}
.meta {{ color:var(--muted); font-size:13px; }}
nav {{ max-width:1240px; margin:14px auto 0; padding:0 18px; display:flex; gap:6px; flex-wrap:wrap; border-bottom:1px solid var(--line); }}
nav button {{ font:600 14px "IBM Plex Sans", Arial, sans-serif; color:var(--muted); background:none; border:0; border-bottom:3px solid transparent; padding:10px 12px; cursor:pointer; }}
nav button[aria-selected="true"] {{ color:var(--ink); border-bottom-color:var(--accent); }}
nav button:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
nav button span {{ color:var(--muted); font-weight:400; margin-right:4px; }}
main {{ max-width:1240px; margin:0 auto; padding:18px; }}
.tab {{ display:none; }} .tab.on {{ display:block; }}
.no-js .tab {{ display:block; }}
h2 {{ font:800 22px/1.2 Archivo, Arial, sans-serif; margin:4px 0 6px; }}
h3 {{ font-size:15px; margin:0 0 8px; }}
.lead {{ color:var(--muted); max-width:80ch; margin:0 0 14px; }}
.card {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:16px; margin-bottom:14px; min-width:0; }}
.grid2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
.grid2 > .card {{ margin-bottom:0; }} .grid2 {{ margin-bottom:14px; }}
@media (max-width:860px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
.kpis {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:10px; margin-bottom:14px; }}
@media (max-width:1000px) {{ .kpis {{ grid-template-columns:repeat(3,1fr); }} }}
@media (max-width:560px) {{ .kpis {{ grid-template-columns:repeat(2,1fr); }} }}
.kpi {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:12px 14px; }}
.kv {{ font:800 26px/1.1 Archivo, Arial, sans-serif; }}
.kl {{ font-weight:600; font-size:13px; margin-top:4px; }}
.ks {{ color:var(--muted); font-size:12px; }}
.chart svg {{ width:100%; height:auto; display:block; font-family:"IBM Plex Sans", Arial, sans-serif; }}
.grid {{ stroke:#e6eaef; stroke-width:1; }}
.tick {{ fill:var(--muted); font-size:11px; }}
.lab {{ fill:var(--ink); font-size:12.5px; }}
.val {{ fill:var(--ink); font-size:12px; font-weight:600; }}
.hit:hover path {{ filter:brightness(.88); }}
.legend {{ display:flex; gap:14px; font-size:12.5px; color:var(--muted); margin-bottom:6px; }}
.legend i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px; }}
.tw {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
th {{ text-align:left; font-size:12px; color:var(--muted); font-weight:600; padding:7px 8px; border-bottom:1px solid var(--line); background:#f6f8fa; vertical-align:bottom; }}
td {{ padding:7px 8px; border-bottom:1px solid #edf0f3; vertical-align:top; }}
.num {{ text-align:right; white-space:nowrap; }}
.nw {{ white-space:nowrap; }}
.neg {{ color:var(--red); font-weight:600; }}
.small {{ font-size:12.5px; color:var(--muted); }}
.steps {{ margin:0; padding:0; list-style:none; counter-reset:s; }}
.steps li {{ counter-increment:s; display:grid; grid-template-columns:30px 1fr; column-gap:10px; padding:8px 0; border-bottom:1px solid #edf0f3; }}
.steps li::before {{ content:"✓"; grid-row:span 2; width:26px; height:26px; border-radius:50%; display:grid; place-items:center; font-weight:700; background:var(--ok-soft); color:var(--ok); }}
.steps li.warn::before {{ content:"!"; background:var(--warn-soft); color:var(--warn); }}
.steps li span {{ color:var(--muted); font-size:13px; }}
.files {{ list-style:none; padding:0; margin:0 0 6px; }}
.files li {{ padding:6px 0; border-bottom:1px solid #edf0f3; display:flex; flex-direction:column; }}
.files li span {{ color:var(--muted); font-size:13px; }}
.pill {{ display:inline-block; font-size:12px; font-weight:600; border-radius:999px; padding:2px 9px; }}
.pill.ok {{ background:var(--ok-soft); color:var(--ok); }} .pill.warn {{ background:var(--warn-soft); color:var(--warn); }}
.rule {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; font-size:13.5px; }}
@media (max-width:860px) {{ .rule {{ grid-template-columns:1fr; }} }}
.rule b {{ display:block; }}
.sw {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; }}
.rule b {{ display:inline; }}
.sc {{ display:flex; align-items:center; gap:8px; white-space:nowrap; }}
.sc b {{ font:800 16px Archivo, Arial, sans-serif; min-width:28px; text-align:right; }}
.stack {{ display:flex; gap:2px; width:100px; height:10px; background:#eef1f4; border-radius:3px; overflow:hidden; }}
.stack i {{ display:block; height:100%; }}
.sc em {{ font-style:normal; font-size:11.5px; color:var(--muted); }}
details {{ margin-top:12px; }} summary {{ cursor:pointer; font-weight:600; color:var(--accent); }}
.brief {{ max-width:860px; font-size:16px; }}
.brief h2 {{ font-size:24px; }}
.brief h3 {{ font:800 17px Archivo, Arial, sans-serif; margin:18px 0 6px; color:var(--accent); }}
.brief li {{ margin-bottom:8px; }}
.brief .score {{ font-size:14px; margin:4px 0 10px; }}
.brief .score td:first-child {{ font-weight:600; }}
.verify {{ max-width:860px; }}
footer {{ max-width:1240px; margin:0 auto; padding:6px 18px 30px; color:var(--muted); font-size:12px; }}
</style>
</head>
<body class="no-js">
<div class="banner">DATOS SINTÉTICOS · Prototipo de demostración · Hoteles, grupos y cifras inventados, salvo las 6,800 habitaciones del destino (Datatur)</div>
<header>
  <div class="eyebrow">Plataforma de datos de eventos de negocios</div>
  <h1>{dmo} · Resultados de {rm}</h1>
  <div class="meta">Corrida: {stamp} · Versión de reglas: {version} · Fuente: {source}</div>
</header>
<nav role="tablist">
  <button role="tab" data-t="corrida"><span>1</span>Corrida</button>
  <button role="tab" data-t="tablero"><span>2</span>Tablero</button>
  <button role="tab" data-t="prospeccion"><span>3</span>Prospección</button>
  <button role="tab" data-t="informe"><span>4</span>Informe</button>
</nav>
<main>
{corrida}
{tablero}
{prospeccion}
{informe}
</main>
<footer>Página generada automáticamente por el script a partir de los resultados de la corrida. No se edita a mano. Datos sintéticos para demostración.</footer>
<script>
document.body.classList.remove('no-js');
const tabs = [...document.querySelectorAll('nav button')];
function show(id) {{
  tabs.forEach(b => b.setAttribute('aria-selected', b.dataset.t === id));
  document.querySelectorAll('.tab').forEach(s => s.classList.toggle('on', s.id === id));
  try {{ history.replaceState(null, '', '#' + id); }} catch (e) {{ /* sandboxed preview: address bar can't change */ }}
}}
tabs.forEach(b => b.addEventListener('click', () => show(b.dataset.t)));
function fromHash() {{ const h = location.hash.slice(1); show(tabs.some(b => b.dataset.t === h) ? h : 'tablero'); }}
window.addEventListener('hashchange', fromHash);
fromHash();
try {{ window.scrollTo(0, 0); }} catch (e) {{}}
</script>
</body>
</html>
"""
