"""Render the demo web page (Spanish) from the engine's results.

One self-contained HTML file: La corrida (the run), Tablero (dashboard),
Prospección (lead targeting) and Informe (the brief). Every number comes from
the results dict; nothing is typed by hand. Charts are inline SVG with hover
titles, and each chart has a table beside it.

Design: "Costa Grande". Ocean ink, lagoon teal, sea-mist ground, one sunset-gold
accent for the month being reported. Cormorant Garamond for display, Hanken
Grotesk for data. The hero is a horizon line of 24 months of group room nights.
"""
import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd


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
    r = re.sub(r"(\d+) of (\d+) hotels submitted for ([0-9-]+)", lambda m: f"{m[1]} de {m[2]} hoteles enviaron {mes(m[3])}", r)
    r = r.replace("; missing: ", "; falta: ")
    r = re.sub(r"(\d+) earlier submission\(s\) replaced by the hotel's latest",
               lambda m: f"{m[1]} envío anterior reemplazado por el más reciente del hotel", r)
    r = re.sub(r"(\d+) prospects added; (\d+) already in Leads, dropped",
               lambda m: f"{m[1]} prospectos añadidos; {m[2]} ya eran oportunidades y se descartaron", r)
    r = r.replace("Leads", "Oportunidades").replace("Assets", "Activos").replace("Hotel responses", "Respuestas de hoteles").replace("Imports", "Importaciones")
    return "Ninguno" if r == "None" else r


# ------------------------------------------------------------------ SVG charts

TEAL, GOLD, INDIGO = "#00839b", "#c9801a", "#5b6fd6"   # validated: categorical, CVD-safe, 3:1 on white
HORIZON = "#e8a63c"                                     # hero line on the ocean background


# ------------------------------------------------------------------ charts
def horizon(labels, values, marks, w=1180, h=230):
    """The hero: 24 months of group room nights drawn as one line across the ocean."""
    pad_x, pad_t, pad_b = 8, 34, 30
    vmin, vmax = min(values) * 0.85, max(values) * 1.04
    n = len(values)
    xs = [pad_x + i * (w - 2 * pad_x) / (n - 1) for i in range(n)]
    ys = [pad_t + (1 - (v - vmin) / (vmax - vmin)) * (h - pad_t - pad_b) for v in values]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"M{xs[0]:.1f},{h - pad_b} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys)) + f" L{xs[-1]:.1f},{h - pad_b} Z"
    out = [f'<svg viewBox="0 0 {w} {h}" class="horizon" role="img" aria-label="Noches de grupo por mes, últimos 24 meses">',
           f'<defs><linearGradient id="hzg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{HORIZON}" stop-opacity=".22"/>'
           f'<stop offset="1" stop-color="{HORIZON}" stop-opacity="0"/></linearGradient></defs>',
           f'<path d="{area}" fill="url(#hzg)"/>',
           f'<polyline points="{pts}" fill="none" stroke="{HORIZON}" stroke-width="2.25" stroke-linejoin="round" stroke-linecap="round" class="draw" pathLength="1"/>']
    for i, (x, y, v) in enumerate(zip(xs, ys, values)):
        out.append(f'<g class="hz"><title>{esc(labels[i])}: {n0(v)} noches de grupo</title>'
                   f'<rect x="{x - (w / n) / 2:.1f}" y="0" width="{w / n:.1f}" height="{h}" fill="transparent"/></g>')
    for i, kind in marks:
        x, y = xs[i], ys[i]
        anchor = "end" if i > n * 0.8 else ("start" if i < n * 0.2 else "middle")
        dx = -10 if anchor == "end" else (10 if anchor == "start" else 0)
        if kind == "now":
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{HORIZON}" stroke="#0e2a33" stroke-width="2"/>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#0e2a33" stroke="#cfe0e3" stroke-width="2"/>')
        out.append(f'<text x="{x + dx:.1f}" y="{y - 14:.1f}" text-anchor="{anchor}" class="hz-v">{n0(values[i])}</text>'
                   f'<text x="{x + dx:.1f}" y="{y - 30:.1f}" text-anchor="{anchor}" class="hz-l">{esc(labels[i])}</text>')
    for i in range(n):
        if labels[i].startswith("ene") or i in (0, n - 1):
            out.append(f'<text x="{xs[i]:.1f}" y="{h - 8}" text-anchor="{"start" if i == 0 else "end" if i == n - 1 else "middle"}" class="hz-axis">{esc(labels[i])}</text>')
    out.append("</svg>")
    return "".join(out)


def hbar_chart(labels, series, names=None, colors=(GOLD, TEAL), w=560, row=34, fmt=n0, title=""):
    """Horizontal bars, value at each tip, 4px rounded ends, 2px gap between paired bars."""
    pad_l, pad_r = 178, 60
    k = len(series)
    band = row * (1 if k == 1 else 1.45)
    h = len(labels) * band + 8
    vmax = max(max(s) for s in series) or 1
    plot_w = w - pad_l - pad_r
    bh = 11 if k == 2 else 14
    out = [f'<svg viewBox="0 0 {w} {h:.0f}" role="img" aria-label="{esc(title)}">']
    for i, lab in enumerate(labels):
        y0 = 4 + i * band
        block = k * bh + (k - 1) * 2
        top = y0 + (band - block) / 2
        out.append(f'<text x="{pad_l - 14}" y="{top + block / 2 + 4:.1f}" class="lab" text-anchor="end">{esc(lab)}</text>')
        for j, s in enumerate(series):
            v = s[i]
            bw = max(3, v / vmax * plot_w)
            y = top + j * (bh + 2)
            r = min(4, bw / 2)
            path = (f"M{pad_l},{y:.1f} H{pad_l + bw - r:.1f} Q{pad_l + bw:.1f},{y:.1f} {pad_l + bw:.1f},{y + r:.1f} "
                    f"V{y + bh - r:.1f} Q{pad_l + bw:.1f},{y + bh:.1f} {pad_l + bw - r:.1f},{y + bh:.1f} H{pad_l} Z")
            nm = f"{names[j]}: " if names else ""
            out.append(f'<g class="hit"><title>{esc(lab)}, {esc(nm)}{fmt(v)}</title><path d="{path}" fill="{colors[j]}"/>'
                       f'<text x="{pad_l + bw + 7:.1f}" y="{y + bh - 1.5:.1f}" class="val">{fmt(v)}</text></g>')
    out.append("</svg>")
    return "".join(out)


def legend(items):
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{c}"></i>{esc(n)}</span>' for n, c in items) + "</div>"


def table(headers, rows, num=(), cls=""):
    th = "".join(f'<th class="{"num" if i in num else ""}">{esc(h)}</th>' for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(f'<td class="{"num" if i in num else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
                   for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def delta(change, kind="pct", good_when_up=True):
    """▲/▼ plus the figure; colour is never the only signal."""
    if change is None or (isinstance(change, float) and pd.isna(change)):
        return '<span class="d">—</span>'
    up = change > 0
    txt = f"{change:+.1f} pts" if kind == "points" else f"{change * 100:+.1f}%"
    txt = txt.replace("-", "−")
    tone = "up" if (up == good_when_up) else "down"
    if change == 0:
        tone = ""
    arrow = "▲" if up else ("▼" if change < 0 else "")
    return f'<span class="d {tone}"><b aria-hidden="true">{arrow}</b> {txt}</span>'


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
        out.append('<div class="tw"><table class="perf"><thead><tr>' + "".join(cell(c, "th", i) for i, c in enumerate(head))
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




# ------------------------------------------------------------------ month performance rows (shared with the brief's table)
def scorecard_rows(R):
    """(label, value, comparison, change, change_type) in Spanish, from R['scorecard']."""
    S = R["S"]
    rm, ly = S["report_month"], S["report_month"] - 12
    m_ly = mes(ly, True)
    mes_nombre = MESES[rm.month - 1]
    rows = {r["metric"]: r for r in R["scorecard"]}

    def num(v, kind):
        if v is None:
            return "—"
        return f"{v * 100:.1f}%" if kind == "rate" else (f"{v:.1f}%" if kind == "pct_level" else f"{v:,.0f}")

    spec = [
        ("group_room_nights_month", f"Noches de grupo del mes ({rows['group_room_nights_month']['note']})", "int", m_ly),
        ("group_room_nights_ytd", f"Noches de grupo, enero a {mes_nombre}", "int", str(ly.year)),
        ("group_room_nights_12m", "Noches de grupo, últimos 12 meses", "int", "12 meses anteriores"),
        ("hotel_occupancy_month", "Ocupación hotelera del destino", "pct_level", m_ly),
        ("air_seats_month", "Asientos aéreos programados (llegadas)", "int", m_ly),
        ("leads_received_month", "Oportunidades recibidas en el mes", "int", m_ly),
        ("leads_received_ytd", f"Oportunidades recibidas, enero a {mes_nombre}", "int", str(ly.year)),
        ("win_rate_target_vs_other", "Tasa de éxito 12 meses: sectores meta contra el resto", "rate", "resto"),
    ]
    out = []
    for key, label, kind, cmp_label in spec:
        r = rows[key]
        out.append((label, num(r["value"], kind), f"{num(r['comparison'], kind)} ({cmp_label})", r["change"], r["change_type"]))
    return out


# ------------------------------------------------------------------ page
def render(R, brief_text, check_df, meta):
    S, t, tot, f = R["S"], R["trend"], R["tot"], R["fit"]
    rm = S["report_month"]
    ly = rm - 12
    seg = t["segment"].set_index("Segment")
    prio = f[f.Priority == "Yes"]
    now = datetime.now(ZoneInfo("America/Mexico_City"))
    held = brief_text is None
    n_ok = int((check_df["Found in results"] == "Yes").sum()) if len(check_df) else 0

    # ---- hero
    mon = t["monthly"]
    labels = [mes(m, True) for m in mon["Month"]]
    vals = mon.iloc[:, 1].tolist()
    marks = [(len(vals) - 13, "ly"), (len(vals) - 1, "now")] if len(vals) >= 13 else [(len(vals) - 1, "now")]
    change = seg.loc["Total", "Change"]
    verdict = (f"{n0(seg.loc['Total', str(rm)])} noches de grupo en {MESES[rm.month - 1]}, "
               f"{pct(abs(change))} {'menos' if change < 0 else 'más'} que hace un año.")
    hero = f"""
<header class="hero">
  <div class="wrap">
    <p class="kicker">Eventos de negocios, {esc(mes(rm))}</p>
    <h1>Ixtapa-Zihuatanejo</h1>
    <p class="verdict">{esc(verdict)}</p>
    <figure class="hz-fig">{horizon(labels, vals, marks)}
      <figcaption>Noches de grupo por mes en los mismos {t['comparable_hotels']} hoteles. Dorado: {esc(mes(rm))}. Claro: {esc(mes(ly))}.</figcaption>
    </figure>
    <p class="runmeta">Corrida del {now.day} de {MESES[now.month - 1]} de {now.year}, {now:%H:%M} (hora del centro de México). Versión de reglas {esc(meta['version'])}. Datos: {esc(meta['data_source'])}.</p>
  </div>
</header>"""

    # ---- Corrida
    chk = R["check"]
    n_alert = int((chk.Status == "CHECK").sum())
    steps = [
        ("Leer los archivos", tr_check(chk.loc[chk.Check == "Rows read", "Result"].iloc[0]), "ok"),
        ("Revisar la estructura", "Todas las pestañas y columnas coinciden con el esquema. Si algo cambia, la corrida se detiene.", "ok"),
        ("Revisar los datos", f"{n_alert} alertas para el equipo. No detienen la corrida.", "warn" if n_alert else "ok"),
        ("Correr las 6 consultas fijas", "Temporadas de necesidad, ajuste de prospectos, motivos de pérdida, capacidad, tendencia de noches de grupo y resultados de propuestas.", "ok"),
        ("Redactar el informe", meta["brief_source"] + ".", "ok"),
        ("Verificar cada cifra del informe",
         ("Informe retenido: cifras no encontradas en los resultados (" + ", ".join(check_df["Number in brief"].astype(str)) + ")."
          if len(check_df) else "Informe retenido: la API de Claude no respondió.") if held
         else f"{n_ok} de {len(check_df)} cifras encontradas en los resultados.", "warn" if held else "ok"),
        ("Publicar los resultados", f"Esta página y el libro de resultados de {mes(rm)}, con fecha y sin sobrescribir.", "ok"),
    ]
    step_html = "".join(f'<li class="{st}"><span class="dot" aria-hidden="true">{"✓" if st == "ok" else "!"}</span>'
                        f'<div><b>{esc(a)}</b><p>{esc(b)}</p></div></li>' for a, b, st in steps)
    chk_rows = [[esc(CHECK.get(r.Check, r.Check)), esc(tr_check(r.Result)),
                 '<span class="tag ok">Correcto</span>' if r.Status == "OK" else '<span class="tag warn">Revisar</span>']
                for r in chk.itertuples()]
    corrida = f"""
<section id="corrida" class="tab" aria-labelledby="t-corrida">
  <div class="lead-in"><h2>Cómo se hizo esta página</h2>
  <p>Un script fijo y probado lee los archivos del destino, calcula cada número y publica los resultados. Nadie escribe cifras a mano. Claude solo redacta el informe, a partir de los resultados.</p></div>
  <div class="split">
    <div><h3>Paso a paso</h3><ol class="steps">{step_html}</ol></div>
    <div>
      <h3>Lo que leyó</h3>
      <dl class="files">
        <dt>Data</dt><dd>Oportunidades, activos, datos públicos, listas y parámetros, en Google Sheets.</dd>
        <dt>Respuestas de hoteles</dt><dd>El formulario mensual de {len(R['hotels'])} hoteles, en Google Forms.</dd>
        <dt>Importaciones</dt><dd>Una lista de prospectos exportada de Cvent.</dd>
      </dl>
      <h3>Revisión de datos</h3>
      {table(["Revisión", "Resultado", "Estado"], chk_rows)}
    </div>
  </div>
</section>"""

    # ---- Tablero
    score_html = "".join(
        f'<div class="sc-row"><div class="sc-l"><span>{esc(label)}</span><small>contra {esc(cmp_)}</small></div>'
        f'<div class="sc-v">{esc(val)}</div><div class="sc-d">{delta(chg, kind)}</div></div>'
        for label, val, cmp_, chg, kind in scorecard_rows(R))
    segs = [s for s in seg.index if s != "Total"]
    seg_chart = hbar_chart([SEG[s] for s in segs], [[seg.loc[s, str(rm)] for s in segs], [seg.loc[s, str(ly)] for s in segs]],
                           names=[mes(rm), mes(ly)], title="Noches de grupo por segmento")
    seg_rows = [[esc(SEG[s]), n0(seg.loc[s, str(rm)]), n0(seg.loc[s, str(ly)]), delta(seg.loc[s, "Change"])] for s in seg.index]
    ori = t["origin"].set_index("Origin")
    ori_rows = [[esc(ORI[o]), n0(ori.loc[o, str(rm)]), n0(ori.loc[o, str(ly)]), delta(ori.loc[o, "Change"])] for o in ori.index]
    loss = R["loss"]
    ins = R["insights"]
    rn_by_reason = {r["Loss reason"]: r["room_nights_lost"] for r in ins["lost_last_12_months"]["by_reason"]}
    loss_chart = hbar_chart([LOSS.get(x, x) for x in loss["Loss reason"]], [loss["Leads lost"].tolist()], colors=(TEAL,),
                            title="Motivos de pérdida")
    loss_rows = [[esc(LOSS.get(r["Loss reason"], r["Loss reason"])), n0(r["Leads lost"]), n0(rn_by_reason.get(r["Loss reason"], 0))]
                 for _, r in loss.iterrows()]
    need = R["need"]
    need_rows = [[f'<span class="nw">{esc(mes(r["Month"]))}</span>', n0(r["Group room nights, same month last year"]),
                  f'{r["Index vs 12-month average"]:.2f}', "Sí" if r["Need period (Settings)"] == "Yes" else "No",
                  n0(r["Groups won for the month"]), n0(r["Peak rooms won"]), n0(r["Open leads for the month"])]
                 for _, r in need.iterrows()]
    lost_rows = [[esc("Otro" if r["Lost to"] == "Other" else r["Lost to"]), n0(r["Leads lost"])] for _, r in R["lost_to"].iterrows()]
    cap_rows = [[esc(r["Name"]), esc(ASSET.get(r["Type"], r["Type"])), n0(r["Max capacity"]),
                 n0(r["Rooms"]) if r["Rooms"] else "—"] for _, r in R["cap"].iterrows()]
    box_rows = [[esc(SECTOR.get(r["Sector"], r["Sector"])), n0(r["Decided"]), n0(r["Won"]), n0(r["Lost"]),
                 '<span class="muted">Datos insuficientes</span>' if isinstance(r["Win rate"], str) else pct(r["Win rate"]),
                 n0(r["Room nights won"])] for _, r in R["box"].iterrows()]
    src_rows = [[esc({"Hotel referral": "Referencia de hoteles", "Trade show": "Ferias", "Referral": "Recomendación",
                      "Direct": "Contacto directo", "RFP (Cvent)": "Solicitudes por Cvent"}.get(r["source"], r["source"])),
                 n0(r["decided"]), n0(r["won"]),
                 '<span class="muted">Datos insuficientes</span>' if isinstance(r["win_rate"], str) else pct(r["win_rate"])]
                for r in ins["win_rate_by_source_last_12_months"]]
    excl = ", ".join(t["excluded_hotels"])
    tablero = f"""
<section id="tablero" class="tab" aria-labelledby="t-tablero">
  <div class="block">
    <h2>Cómo nos fue en {esc(MESES[rm.month - 1])}</h2>
    <div class="scorecard">{score_html}</div>
    <p class="note">Noches de grupo: los mismos {t['comparable_hotels']} hoteles en ambos periodos.{f' Fuera de la comparación: {esc(excl)}, que no envió los dos meses.' if excl else ''} Ocupación y asientos aéreos: datos públicos de todo el destino.</p>
  </div>

  <div class="block two">
    <div>
      <h2>Por segmento</h2>
      {legend([(mes(rm), GOLD), (mes(ly), TEAL)])}
      <div class="chart">{seg_chart}</div>
      {table(["Segmento", mes(rm), mes(ly), "Cambio"], seg_rows, num=(1, 2, 3), cls="compact")}
    </div>
    <div>
      <h2>Por qué perdimos</h2>
      <p class="sub">Grupos perdidos en los últimos 12 meses, {tot['lost']} en total.</p>
      <div class="chart">{loss_chart}</div>
      {table(["Motivo", "Grupos", "Noches estimadas"], loss_rows, num=(1, 2), cls="compact")}
    </div>
  </div>

  <div class="block">
    <h2>Temporadas de necesidad, próximos 6 meses</h2>
    {table(["Mes", "Noches de grupo hace un año", "Índice", "Necesidad", "Grupos ganados", "Hab. pico ganadas", "Oportunidades abiertas"], need_rows, num=(1, 2, 4, 5, 6))}
    <p class="note">Índice: noches de grupo del mismo mes del año pasado contra el promedio mensual de los últimos 12 meses. Necesidad: meses marcados en los parámetros del destino.</p>
  </div>

  <div class="block two">
    <div>
      <h2>Resultados por sector</h2>
      <p class="sub">Propuestas decididas en los últimos 12 meses.</p>
      {table(["Sector", "Decididas", "Ganadas", "Perdidas", "Tasa de éxito", "Noches ganadas"], box_rows, num=(1, 2, 3, 4, 5), cls="compact")}
    </div>
    <div>
      <h2>Resultados por canal</h2>
      <p class="sub">Cómo llegó cada oportunidad decidida.</p>
      {table(["Canal", "Decididas", "Ganadas", "Tasa de éxito"], src_rows, num=(1, 2, 3), cls="compact")}
      <h3 class="gap">Destinos que nos ganaron</h3>
      {table(["Destino", "Grupos"], lost_rows, num=(1,), cls="compact")}
    </div>
  </div>

  <div class="block two">
    <div><h2>Origen de las noches de grupo</h2>{table(["Origen", mes(rm), mes(ly), "Cambio"], ori_rows, num=(1, 2, 3), cls="compact")}</div>
    <div><h2>Sedes para {S['cap_group']} asistentes o más</h2>{table(["Sede", "Tipo", "Capacidad", "Habitaciones"], cap_rows, num=(2, 3), cls="compact")}</div>
  </div>
</section>"""

    # ---- Prospección
    def razon(r):
        sec = "Sector meta del plan" if r["Sector pts"] >= S["w_sector"] else (
            "Sector secundario" if r["Sector pts"] > 0 else "Fuera de los sectores meta")
        o = r["Occupancy last year"]
        d = pd.Timestamp(r["Start date"])
        need = f"{MESES[d.month - 1]} al {o:.0f}% de ocupación" if pd.notna(o) else ""
        cap = ("cabe con holgura" if r["Capacity pts"] >= S["w_capacity"] else
               "cabe justo" if r["Capacity pts"] > 0 else "demasiado grande")
        return ", ".join(x for x in [sec, need, cap] if x) + "."

    def score_cell(r):
        parts = [(r["Sector pts"], TEAL, "Sector"), (r["Need period pts"], GOLD, "Temporada"), (r["Capacity pts"], INDIGO, "Capacidad")]
        bars = "".join(f'<i style="width:{v}%;background:{c}" title="{n}: {int(v)}"></i>' for v, c, n in parts if v > 0)
        return (f'<div class="score"><b>{int(r["Score"])}</b><span class="stack" aria-hidden="true">{bars}</span>'
                f'<small>{int(r["Sector pts"])} + {int(r["Need period pts"])} + {int(r["Capacity pts"])}</small></div>')

    def lead_rows(df):
        return [[str(int(r["Rank"])),
                 f'<b>{esc(r["Organizer"])}</b><small class="row-sub">{esc(TIPO.get(r["Type"], r["Type"]))}, {esc(SECTOR.get(r["Sector"], r["Sector"]).lower())}</small>',
                 f'<span class="nw">{esc(fecha(r["Start date"]))}</span>', n0(r["Attendees"]), n0(r["Peak rooms"]),
                 n0(r["Est. room nights"]), score_cell(r), f'<span class="why">{esc(razon(r))}</span>'] for _, r in df.iterrows()]
    hdr = ["", "Organización", "Llegada", "Asistentes", "Hab. pico", "Noches est.", "Puntaje", "Por qué"]
    rest = f[f.Priority != "Yes"]
    pp = ins["priority_pipeline"]
    prospeccion = f"""
<section id="prospeccion" class="tab" aria-labelledby="t-prospeccion">
  <div class="lead-in"><h2>{len(prio)} prospectos prioritarios, {n0(pp['est_room_nights'])} noches estimadas</h2>
  <p>Oportunidades abiertas y prospectos importados, ordenados por qué tan bien encajan en el destino. Prioritario: puntaje de {S['threshold']} o más, sobre 100.</p></div>
  <div class="rule">
    <div><span class="sw" style="background:{TEAL}"></span><b>Sector, hasta {S['w_sector']}.</b> Sector meta del plan: {S['w_sector']}. Secundario: {S['w_sector'] // 2}.</div>
    <div><span class="sw" style="background:{GOLD}"></span><b>Temporada, hasta {S['w_need']}.</b> Según la ocupación hotelera del mes del evento en los últimos 12 meses. El mes más flojo recibe {S['w_need']}; el más lleno, 0.</div>
    <div><span class="sw" style="background:{INDIGO}"></span><b>Capacidad, hasta {S['w_capacity']}.</b> Completo hasta {n0(S['comfort_rooms'])} habitaciones pico y {n0(S['comfort_att'])} asistentes. Baja a 0 en {n0(S['max_peak'])} habitaciones o en la capacidad de la sede más grande.</div>
  </div>
  {table(hdr, lead_rows(prio), num=(0, 3, 4, 5), cls="leads")}
  <details><summary>Ver los otros {len(rest)} candidatos</summary>{table(hdr, lead_rows(rest), num=(0, 3, 4, 5), cls="leads")}</details>
</section>"""

    # ---- Informe
    if held:
        informe = f"""
<section id="informe" class="tab" aria-labelledby="t-informe">
  <article class="letter"><h2>Informe retenido</h2>
    <p>{(f'El borrador de este mes usó cifras que no aparecen en los resultados ({esc(", ".join(check_df["Number in brief"].astype(str)))}), así que no se publica.') if len(check_df) else 'La API de Claude no respondió durante la corrida.'} El operador lo revisa. El tablero y la prospección sí se publican.</p></article>
</section>"""
    else:
        chk_tbl = table(["Cifra en el informe", "¿Está en los resultados?"],
                        [[esc(r["Number in brief"]), "Sí" if r["Found in results"] == "Yes" else "<b>No</b>"] for _, r in check_df.iterrows()],
                        cls="compact")
        informe = f"""
<section id="informe" class="tab" aria-labelledby="t-informe">
  <article class="letter">{md(brief_text)}</article>
  <aside class="verify">
    <p><span class="tag ok">{n_ok} de {len(check_df)} cifras verificadas</span></p>
    <p>{esc(meta['brief_source'])}. Claude recibe solo los resultados de las consultas, nunca los datos crudos ni datos personales. Antes de publicar, el script busca cada cifra del informe en los resultados; si alguna no aparece, el informe se retiene.</p>
    <details><summary>Ver la verificación cifra por cifra</summary>{chk_tbl}</details>
  </aside>
</section>"""

    html_out = PAGE
    for k, v in {"%%TITLE%%": esc(f"Ixtapa-Zihuatanejo, eventos de negocios, {mes(rm)} (datos sintéticos)"),
                 "%%HERO%%": hero, "%%CORRIDA%%": corrida, "%%TABLERO%%": tablero,
                 "%%PROSPECCION%%": prospeccion, "%%INFORME%%": informe}.items():
        html_out = html_out.replace(k, v)
    return html_out


PAGE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>%%TITLE%%</title>
<style>
@font-face { font-family: "Cormorant Garamond"; font-weight: 500; font-display: swap; src: url("fonts/cormorant-garamond-latin-500-normal.woff2") format("woff2"); }
@font-face { font-family: "Cormorant Garamond"; font-weight: 600; font-display: swap; src: url("fonts/cormorant-garamond-latin-600-normal.woff2") format("woff2"); }
@font-face { font-family: "Hanken Grotesk"; font-weight: 400; font-display: swap; src: url("fonts/hanken-grotesk-latin-400-normal.woff2") format("woff2"); }
@font-face { font-family: "Hanken Grotesk"; font-weight: 500; font-display: swap; src: url("fonts/hanken-grotesk-latin-500-normal.woff2") format("woff2"); }
@font-face { font-family: "Hanken Grotesk"; font-weight: 600; font-display: swap; src: url("fonts/hanken-grotesk-latin-600-normal.woff2") format("woff2"); }
@font-face { font-family: "Hanken Grotesk"; font-weight: 700; font-display: swap; src: url("fonts/hanken-grotesk-latin-700-normal.woff2") format("woff2"); }
:root {
  --ocean: #0e2a33; --ocean-2: #133843; --teal: #00839b; --gold: #c9801a; --horizon: #e8a63c;
  --mist: #f3f6f5; --white: #ffffff; --ink: #14262c; --slate: #5d7178; --line: #dfe6e6; --line-soft: #edf1f1;
  --up: #0a7b5c; --down: #b23a2b; --warn: #a15c07; --warn-bg: #fdf3e2; --ok-bg: #e6f3ee;
  --serif: "Cormorant Garamond", "Iowan Old Style", Georgia, serif;
  --sans: "Hanken Grotesk", "Helvetica Neue", Arial, sans-serif;
  color-scheme: light;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--mist); color: var(--ink); font: 400 15.5px/1.55 var(--sans); font-feature-settings: "tnum" 1, "lnum" 1; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 0 28px; }
.notice { background: #8f2a1f; color: #fff; font-size: 13px; text-align: center; padding: 7px 16px; letter-spacing: .01em; }
.notice b { font-weight: 600; }

/* hero */
.hero { background: radial-gradient(120% 140% at 85% 0%, var(--ocean-2) 0%, var(--ocean) 55%); color: #e9f0f1; padding: 54px 0 26px; }
.kicker { margin: 0 0 6px; font-size: 15px; color: #a9c3c8; }
.hero h1 { margin: 0; font: 600 clamp(48px, 8.2vw, 96px)/.95 var(--serif); letter-spacing: -.01em; color: #fff; }
.verdict { margin: 14px 0 0; font-size: clamp(17px, 2vw, 21px); color: #d6e4e6; max-width: 60ch; }
.hz-fig { margin: 30px 0 0; }
.horizon { width: 100%; height: auto; display: block; overflow: visible; }
.hz-v { fill: #fff; font: 600 15px var(--sans); }
.hz-l { fill: #a9c3c8; font: 500 12px var(--sans); }
.hz-axis { fill: #7f9ca2; font: 500 11.5px var(--sans); }
.hz:hover rect { fill: rgba(255,255,255,.04); }
.draw { stroke-dasharray: 1; stroke-dashoffset: 0; animation: draw 1.6s cubic-bezier(.3,.6,.2,1) both; }
@keyframes draw { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
@media (prefers-reduced-motion: reduce) { .draw { animation: none; } }
.hz-fig figcaption { margin-top: 6px; font-size: 12.5px; color: #8fabb1; }
.runmeta { margin: 22px 0 0; font-size: 12.5px; color: #7f9ca2; max-width: 100ch; }

/* tabs */
nav.tabs { position: sticky; top: 0; z-index: 5; background: rgba(255,255,255,.96); backdrop-filter: saturate(1.4) blur(6px); border-bottom: 1px solid var(--line); }
nav.tabs .wrap { display: flex; gap: 30px; overflow-x: auto; }
nav.tabs button { appearance: none; background: none; border: 0; padding: 17px 0 15px; font: 500 15px var(--sans); color: var(--slate); cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; }
nav.tabs button:hover { color: var(--ink); }
nav.tabs button[aria-selected="true"] { color: var(--ink); font-weight: 600; border-bottom-color: var(--teal); }
nav.tabs button:focus-visible, summary:focus-visible { outline: 2px solid var(--teal); outline-offset: 3px; border-radius: 2px; }

main { padding: 44px 0 64px; }
.tab { display: none; } .tab.on { display: block; }
.no-js .tab { display: block; }
h2 { font: 600 30px/1.15 var(--serif); margin: 0 0 14px; color: var(--ocean); letter-spacing: -.005em; }
h3 { font: 600 15px var(--sans); margin: 0 0 12px; color: var(--ink); }
h3.gap { margin-top: 30px; }
.sub { margin: -6px 0 14px; color: var(--slate); font-size: 14px; }
.note { margin: 14px 0 0; color: var(--slate); font-size: 13px; max-width: 95ch; }
.muted { color: var(--slate); }
.nw { white-space: nowrap; }

.block { background: var(--white); border-radius: 18px; padding: 34px 36px; margin-bottom: 22px; box-shadow: 0 1px 0 rgba(14,42,51,.04); }
.block.two { display: grid; grid-template-columns: 1fr 1fr; gap: 56px; }
@media (max-width: 920px) { .block.two { grid-template-columns: 1fr; gap: 40px; } .block { padding: 26px 22px; } }
.lead-in { max-width: 78ch; margin: 0 0 26px; }
.lead-in p { color: var(--slate); margin: 0; font-size: 16px; }

/* scorecard */
.scorecard { display: grid; grid-template-columns: 1fr 1fr; column-gap: 56px; }
@media (max-width: 920px) { .scorecard { grid-template-columns: 1fr; } }
.sc-row { display: grid; grid-template-columns: 1fr auto 104px; align-items: baseline; gap: 18px; padding: 15px 0; border-bottom: 1px solid var(--line-soft); }
.sc-l span { display: block; font-weight: 500; }
.sc-l small { color: var(--slate); font-size: 12.5px; }
.sc-v { font: 600 26px/1 var(--serif); color: var(--ocean); font-variant-numeric: lining-nums tabular-nums; }
.sc-d { text-align: right; }
@media (max-width: 560px) {
  .sc-row { grid-template-columns: 1fr auto; row-gap: 6px; }
  .sc-l { grid-column: 1 / -1; }
  .sc-v { font-size: 28px; }
  .hero { padding-top: 38px; }
  .wrap { padding: 0 18px; }
}
.d { font-weight: 600; font-size: 14px; white-space: nowrap; color: var(--slate); }
.d b { font-size: 10px; vertical-align: 1px; }
.d.up { color: var(--up); } .d.down { color: var(--down); }

/* charts */
.chart svg { width: 100%; height: auto; display: block; }
.lab { fill: var(--ink); font: 500 13px var(--sans); }
.val { fill: var(--ink); font: 600 12.5px var(--sans); }
.hit:hover path { filter: brightness(.9); }
.legend { display: flex; gap: 18px; font-size: 13px; color: var(--slate); margin: -4px 0 10px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 7px; vertical-align: -1px; }

/* tables */
.tw { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; font-weight: 500; font-size: 12.5px; color: var(--slate); padding: 0 10px 10px; border-bottom: 1px solid var(--line); vertical-align: bottom; }
td { padding: 11px 10px; border-bottom: 1px solid var(--line-soft); vertical-align: top; }
th:first-child, td:first-child { padding-left: 0; } th:last-child, td:last-child { padding-right: 0; }
.num { text-align: right; white-space: nowrap; }
table.compact td { padding-top: 9px; padding-bottom: 9px; }
.chart + .tw { margin-top: 18px; }

/* run */
.split { display: grid; grid-template-columns: 1fr 1.15fr; gap: 56px; background: var(--white); border-radius: 18px; padding: 34px 36px; }
@media (max-width: 920px) { .split { grid-template-columns: 1fr; padding: 26px 22px; } }
.steps { list-style: none; margin: 0; padding: 0; counter-reset: s; }
.steps li { display: grid; grid-template-columns: 34px 1fr; gap: 14px; padding: 13px 0; border-bottom: 1px solid var(--line-soft); }
.steps li:last-child { border-bottom: 0; }
.steps .dot { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; font-weight: 700; font-size: 13px; background: var(--ok-bg); color: var(--up); }
.steps li.warn .dot { background: var(--warn-bg); color: var(--warn); }
.steps b { font-weight: 600; }
.steps p { margin: 2px 0 0; color: var(--slate); font-size: 14px; }
.files { margin: 0 0 30px; display: grid; grid-template-columns: max-content 1fr; gap: 8px 18px; font-size: 14px; }
.files dt { font-weight: 600; } .files dd { margin: 0; color: var(--slate); }
.tag { display: inline-block; font-size: 12.5px; font-weight: 600; border-radius: 999px; padding: 2px 10px; white-space: nowrap; }
.tag.ok { background: var(--ok-bg); color: var(--up); } .tag.warn { background: var(--warn-bg); color: var(--warn); }

/* leads */
.rule { display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; margin: 0 0 22px; font-size: 14px; color: var(--slate); }
.rule b { color: var(--ink); font-weight: 600; }
@media (max-width: 920px) { .rule { grid-template-columns: 1fr; gap: 12px; } }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 8px; vertical-align: 0; }
#prospeccion > .tw, #prospeccion details { background: var(--white); border-radius: 18px; padding: 26px 30px; }
#prospeccion details { margin-top: 18px; }
table.leads td { padding-top: 13px; padding-bottom: 13px; }
.row-sub { display: block; color: var(--slate); font-size: 12.5px; margin-top: 2px; }
.score { display: flex; align-items: center; gap: 10px; white-space: nowrap; }
.score b { font: 600 22px/1 var(--serif); color: var(--ocean); min-width: 30px; text-align: right; font-variant-numeric: lining-nums; }
.stack { display: flex; gap: 2px; width: 96px; height: 8px; background: var(--line-soft); border-radius: 4px; overflow: hidden; }
.stack i { display: block; height: 100%; }
.score small { color: var(--slate); font-size: 12px; }
.why { color: var(--slate); font-size: 13.5px; }
summary { cursor: pointer; font-weight: 600; color: var(--teal); }
details[open] summary { margin-bottom: 14px; }

/* brief */
.letter { background: var(--white); border-radius: 18px; padding: 52px 64px; max-width: 900px; font-size: 16.5px; line-height: 1.68; }
@media (max-width: 920px) { .letter { padding: 30px 22px; } }
.letter h2 { font-size: 38px; line-height: 1.08; margin-bottom: 8px; }
.letter h2 + p { color: var(--slate); font-size: 13.5px; margin-top: 0; }
.letter h3 { font: 600 24px/1.2 var(--serif); color: var(--ocean); margin: 34px 0 10px; }
.letter p, .letter li { max-width: 70ch; }
.letter ol, .letter ul { padding-left: 22px; }
.letter li { margin-bottom: 12px; }
.letter li::marker { color: var(--teal); font-weight: 600; }
.letter strong { color: var(--ocean); font-weight: 600; }
.letter table.perf { font-size: 14.5px; margin: 8px 0 18px; }
.letter table.perf td:first-child { font-weight: 500; }
.letter .num.neg { color: var(--down); font-weight: 600; }
.verify { max-width: 900px; margin-top: 18px; padding: 22px 64px; font-size: 13.5px; color: var(--slate); }
@media (max-width: 920px) { .verify { padding: 18px 22px; } }

footer { padding: 0 0 40px; color: var(--slate); font-size: 12.5px; }
</style>
</head>
<body class="no-js">
<div class="notice"><b>Datos sintéticos para demostración.</b> Hoteles, grupos y cifras inventados, salvo las 6,800 habitaciones del destino (Datatur).</div>
%%HERO%%
<nav class="tabs" aria-label="Secciones"><div class="wrap" role="tablist">
  <button role="tab" id="t-corrida" data-t="corrida">La corrida</button>
  <button role="tab" id="t-tablero" data-t="tablero">Tablero</button>
  <button role="tab" id="t-prospeccion" data-t="prospeccion">Prospección</button>
  <button role="tab" id="t-informe" data-t="informe">Informe</button>
</div></nav>
<main><div class="wrap">
%%CORRIDA%%
%%TABLERO%%
%%PROSPECCION%%
%%INFORME%%
</div></main>
<footer><div class="wrap">Página generada por el script a partir de los resultados de la corrida. No se edita a mano.</div></footer>
<script>
document.body.classList.remove('no-js');
const tabs = [...document.querySelectorAll('nav.tabs button')];
function show(id, fromClick) {
  tabs.forEach(b => b.setAttribute('aria-selected', b.dataset.t === id));
  document.querySelectorAll('.tab').forEach(s => s.classList.toggle('on', s.id === id));
  if (!fromClick) return;
  try { history.replaceState(null, '', '#' + id); } catch (e) { /* sandboxed preview: the address can't change */ }
  const n = document.querySelector('nav.tabs');
  if (window.scrollY > n.offsetTop) { try { window.scrollTo({ top: n.offsetTop, behavior: 'smooth' }); } catch (e) {} }
}
tabs.forEach(b => b.addEventListener('click', () => show(b.dataset.t, true)));
function fromHash() { const h = location.hash.slice(1); show(tabs.some(b => b.dataset.t === h) ? h : 'tablero', false); }
window.addEventListener('hashchange', fromHash);
fromHash();
if (location.hash) { requestAnimationFrame(() => { try { window.scrollTo(0, 0); } catch (e) {} }); }
</script>
</body>
</html>
"""
