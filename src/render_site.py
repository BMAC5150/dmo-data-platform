"""Render the demo web page from the engine's results, in Spanish and English.

One self-contained HTML file with an ES | EN switch. Four tabs: La corrida / The run,
Tablero / Dashboard, Prospección / Prospects, Informe / Brief. Every number comes
from the results dict; nothing is typed by hand. Charts are inline SVG with hover
titles, and each chart has a table beside it.

Design: "Costa Grande". Ocean ink, lagoon teal, sea-mist ground, one sunset-gold
accent for the month being reported. Outfit for display, Hanken Grotesk for data
(both self-hosted, SIL OFL). The hero is a horizon line of 24 months of group
room nights.
"""
import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

TEAL, GOLD, INDIGO = "#00839b", "#c9801a", "#5b6fd6"   # validated: categorical, CVD-safe, 3:1 on white
HORIZON = "#e8a63c"                                     # hero line on the ocean background
LANGS = ("es", "en")

MONTHS = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}
MONTHS_SHORT = {
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
MESES = MONTHS["es"]  # kept for callers that import it

NAMES = {
    "es": {
        "seg": {"Association": "Asociaciones", "Corporate": "Corporativo", "Incentive": "Incentivos", "Government & other": "Gobierno y otros", "Total": "Total"},
        "ori": {"Domestic": "Nacional", "International": "Internacional", "Total": "Total"},
        "sector": {"Medical association": "Asociación médica", "Insurance & finance": "Seguros y finanzas", "Mexican corporate": "Corporativo mexicano",
                   "Government": "Gobierno", "Pharma": "Farmacéutico", "Education": "Educación", "Agriculture": "Agricultura", "Religious": "Religioso", "Sports": "Deportes"},
        "loss": {"Price": "Precio", "Air access": "Acceso aéreo", "Safety perception": "Percepción de seguridad", "Dates not available": "Fechas no disponibles",
                 "Venue too small": "Sede insuficiente", "Event cancelled": "Evento cancelado", "Destination profile": "Perfil del destino"},
        "tipo": {"Lead": "Oportunidad", "Prospect (import)": "Prospecto importado"},
        "asset": {"Hotel": "Hotel", "Venue": "Sede", "Supplier": "Proveedor"},
        "source": {"Hotel referral": "Referencia de hoteles", "Trade show": "Ferias", "Referral": "Recomendación", "Direct": "Contacto directo", "RFP (Cvent)": "Solicitudes por Cvent"},
        "check": {"Structure": "Estructura", "Rows read": "Filas leídas", "Hotel submissions": "Envíos de hoteles", "Resubmissions": "Reenvíos",
                  "Open leads with past dates": "Oportunidades abiertas con fecha pasada", "Lost leads without a reason": "Perdidas sin motivo",
                  "Imports": "Listas importadas", "Import files without a mapping": "Archivos sin mapeo", "Import sectors without a mapping": "Sectores sin mapeo"},
        "other": "Otro",
    },
    "en": {
        "seg": {"Association": "Association", "Corporate": "Corporate", "Incentive": "Incentive", "Government & other": "Government and other", "Total": "Total"},
        "ori": {"Domestic": "Domestic", "International": "International", "Total": "Total"},
        "sector": {"Medical association": "Medical association", "Insurance & finance": "Insurance and finance", "Mexican corporate": "Mexican corporate",
                   "Government": "Government", "Pharma": "Pharmaceutical", "Education": "Education", "Agriculture": "Agriculture", "Religious": "Religious", "Sports": "Sports"},
        "loss": {"Price": "Price", "Air access": "Air access", "Safety perception": "Safety perception", "Dates not available": "Dates not available",
                 "Venue too small": "Venue too small", "Event cancelled": "Event cancelled", "Destination profile": "Destination profile"},
        "tipo": {"Lead": "Lead", "Prospect (import)": "Imported prospect"},
        "asset": {"Hotel": "Hotel", "Venue": "Venue", "Supplier": "Supplier"},
        "source": {"Hotel referral": "Hotel referral", "Trade show": "Trade show", "Referral": "Referral", "Direct": "Direct contact", "RFP (Cvent)": "Cvent RFP"},
        "check": {"Structure": "Structure", "Rows read": "Rows read", "Hotel submissions": "Hotel submissions", "Resubmissions": "Resubmissions",
                  "Open leads with past dates": "Open leads with past dates", "Lost leads without a reason": "Lost leads without a reason",
                  "Imports": "Imported lists", "Import files without a mapping": "Files without a mapping", "Import sectors without a mapping": "Sectors without a mapping"},
        "other": "Other",
    },
}
CHECK = NAMES["es"]["check"]  # Spanish names, used by build_results for the run log


def esc(x):
    return html.escape(str(x))


def n0(x):
    return f"{int(round(float(x))):,}"


def pct(x, sign=False):
    v = float(x) * 100
    return (f"{v:+.1f}%" if sign else f"{v:.1f}%").replace("+-", "-")


def mes(period, corto=False, lang="es"):
    p = pd.Period(str(period), "M")
    return f"{(MONTHS_SHORT if corto else MONTHS)[lang][p.month - 1]} {p.year}"


def fecha(s, lang="es"):
    d = pd.Timestamp(s)
    if lang == "en":
        return f"{MONTHS_SHORT[lang][d.month - 1]} {d.day}, {d.year}"
    return f"{d.day} {MONTHS_SHORT[lang][d.month - 1]} {d.year}"


def tr_check(result, lang="es"):
    r = str(result)
    if lang == "en":
        r = re.sub(r"(\d+) of (\d+) hotels submitted for ([0-9-]+)", lambda m: f"{m[1]} of {m[2]} hotels submitted {mes(m[3], lang='en')}", r)
        r = r.replace("All tabs and columns match the schema", "Every tab and column matches the schema")
        r = re.sub(r"(\d+) earlier submission\(s\) replaced by the hotel's latest", lambda m: f"{m[1]} earlier submission replaced by the hotel's latest", r)
        r = re.sub(r"(\d+) prospects added; (\d+) already in Leads, dropped", lambda m: f"{m[1]} prospects added; {m[2]} were already leads and were dropped", r)
        return r
    r = r.replace("All tabs and columns match the schema", "Todas las pestañas y columnas coinciden con el esquema")
    r = re.sub(r"(\d+) of (\d+) hotels submitted for ([0-9-]+)", lambda m: f"{m[1]} de {m[2]} hoteles enviaron {mes(m[3])}", r)
    r = r.replace("; missing: ", "; falta: ")
    r = re.sub(r"(\d+) earlier submission\(s\) replaced by the hotel's latest",
               lambda m: f"{m[1]} envío anterior reemplazado por el más reciente del hotel", r)
    r = re.sub(r"(\d+) prospects added; (\d+) already in Leads, dropped",
               lambda m: f"{m[1]} prospectos añadidos; {m[2]} ya eran oportunidades y se descartaron", r)
    r = r.replace("Leads", "Oportunidades").replace("Assets", "Activos").replace("Hotel responses", "Respuestas de hoteles").replace("Imports", "Importaciones")
    return "Ninguno" if r == "None" else r


# ------------------------------------------------------------------ charts
def horizon(labels, values, marks, uid, aria, w=1180, h=230):
    """The hero: 24 months of group room nights drawn as one line across the ocean."""
    pad_x, pad_t, pad_b = 8, 34, 30
    vmin, vmax = min(values) * 0.85, max(values) * 1.04
    n = len(values)
    xs = [pad_x + i * (w - 2 * pad_x) / (n - 1) for i in range(n)]
    ys = [pad_t + (1 - (v - vmin) / (vmax - vmin)) * (h - pad_t - pad_b) for v in values]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"M{xs[0]:.1f},{h - pad_b} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys)) + f" L{xs[-1]:.1f},{h - pad_b} Z"
    out = [f'<svg viewBox="0 0 {w} {h}" class="horizon" role="img" aria-label="{esc(aria)}">',
           f'<defs><linearGradient id="hzg-{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{HORIZON}" stop-opacity=".22"/>'
           f'<stop offset="1" stop-color="{HORIZON}" stop-opacity="0"/></linearGradient></defs>',
           f'<path d="{area}" fill="url(#hzg-{uid})"/>',
           f'<polyline points="{pts}" fill="none" stroke="{HORIZON}" stroke-width="2.25" stroke-linejoin="round" stroke-linecap="round" class="draw" pathLength="1"/>']
    for i, (x, v) in enumerate(zip(xs, values)):
        out.append(f'<g class="hz"><title>{esc(labels[i])}: {n0(v)}</title>'
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
        if labels[i].lower().startswith(("ene", "jan")) or i in (0, n - 1):
            anchor = "start" if i == 0 else "end" if i == n - 1 else "middle"
            out.append(f'<text x="{xs[i]:.1f}" y="{h - 8}" text-anchor="{anchor}" class="hz-axis">{esc(labels[i])}</text>')
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
    return '<div class="legend">' + "".join(f'<span><i style="background:{c}"></i>{esc(n)}</span>' for n, c in items) + "</div>"


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
    txt = (f"{change:+.1f} pts" if kind == "points" else f"{change * 100:+.1f}%").replace("-", "−")
    tone = "" if change == 0 else ("up" if (up == good_when_up) else "down")
    arrow = "▲" if up else ("▼" if change < 0 else "")
    return f'<span class="d {tone}"><b aria-hidden="true">{arrow}</b> {txt}</span>'


# ------------------------------------------------------------------ brief markdown
def md(text):
    out, in_ol, in_ul, rows = [], False, False, []

    def inline(s):
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))

    def close():
        nonlocal in_ol, in_ul
        if in_ol:
            out.append("</ol>"); in_ol = False
        if in_ul:
            out.append("</ul>"); in_ul = False

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
            if not in_ol:
                close(); out.append("<ol>"); in_ol = True
            out.append(f"<li>{inline(re.sub(r'^\d+\.\s', '', s))}</li>")
        elif s.startswith("- "):
            if not in_ul:
                close(); out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline(s[2:])}</li>")
        else:
            close(); out.append(f"<p>{inline(s)}</p>")
    flush_table()
    close()
    return "\n".join(out)


# ------------------------------------------------------------------ month performance rows (shared with the brief's table)
def scorecard_rows(R, lang="es"):
    """(label, value, comparison, change, change_type), from R['scorecard']."""
    S = R["S"]
    rm, ly = S["report_month"], S["report_month"] - 12
    m_ly = mes(ly, True, lang)
    month = MONTHS[lang][rm.month - 1]
    rows = {r["metric"]: r for r in R["scorecard"]}
    comp = R["trend"]["comparable_hotels"]

    def num(v, kind):
        if v is None:
            return "—"
        return f"{v * 100:.1f}%" if kind == "rate" else (f"{v:.1f}%" if kind == "pct_level" else f"{v:,.0f}")

    if lang == "en":
        spec = [
            ("group_room_nights_month", f"Group room nights this month ({comp} comparable hotels)", "int", m_ly),
            ("group_room_nights_ytd", f"Group room nights, January to {month}", "int", str(ly.year)),
            ("group_room_nights_12m", "Group room nights, last 12 months", "int", "prior 12 months"),
            ("hotel_occupancy_month", "Destination hotel occupancy", "pct_level", m_ly),
            ("air_seats_month", "Scheduled air seats (arrivals)", "int", m_ly),
            ("leads_received_month", "Leads received this month", "int", m_ly),
            ("leads_received_ytd", f"Leads received, January to {month}", "int", str(ly.year)),
            ("win_rate_target_vs_other", "12-month win rate: plan target sectors vs the rest", "rate", "the rest"),
        ]
    else:
        spec = [
            ("group_room_nights_month", f"Noches de grupo del mes ({comp} hoteles comparables)", "int", m_ly),
            ("group_room_nights_ytd", f"Noches de grupo, enero a {month}", "int", str(ly.year)),
            ("group_room_nights_12m", "Noches de grupo, últimos 12 meses", "int", "12 meses anteriores"),
            ("hotel_occupancy_month", "Ocupación hotelera del destino", "pct_level", m_ly),
            ("air_seats_month", "Asientos aéreos programados (llegadas)", "int", m_ly),
            ("leads_received_month", "Oportunidades recibidas en el mes", "int", m_ly),
            ("leads_received_ytd", f"Oportunidades recibidas, enero a {month}", "int", str(ly.year)),
            ("win_rate_target_vs_other", "Tasa de éxito 12 meses: sectores meta contra el resto", "rate", "resto"),
        ]
    out = []
    for key, label, kind, cmp_label in spec:
        r = rows[key]
        out.append((label, num(r["value"], kind), f"{num(r['comparison'], kind)} ({cmp_label})", r["change"], r["change_type"]))
    return out


# ------------------------------------------------------------------ interface text
T = {
    "es": {
        "kicker": "Eventos de negocios, {m}", "verdict": "{n} noches de grupo en {month}, {p} {dir} que hace un año.", "less": "menos", "more": "más",
        "hz_aria": "Noches de grupo por mes, últimos 24 meses",
        "hz_caption": "Noches de grupo por mes en los mismos {c} hoteles. Dorado: {m}. Claro: {ly}.",
        "runmeta": "Corrida del {d} de {month} de {y}, {hm} (hora del centro de México). Versión de reglas {v}. Datos: {src}.",
        "src_repo": "copias de los archivos del destino guardadas en el repositorio",
        "brief_api": "Redactado por la API de Claude ({model}) a partir de los resultados de las consultas",
        "brief_file": "Redactado por Claude a partir de los resultados de las consultas",
        "tabs": ["La corrida", "Tablero", "Prospección", "Informe"],
        "run_h": "Cómo se hizo esta página",
        "run_p": "Un script fijo y probado lee los archivos del destino, calcula cada número y publica los resultados. Nadie escribe cifras a mano. Claude solo redacta el informe, a partir de los resultados.",
        "steps_h": "Paso a paso", "read_h": "Lo que leyó", "check_h": "Revisión de datos",
        "steps": ["Leer los archivos", "Revisar la estructura", "Revisar los datos", "Correr las 6 consultas fijas", "Redactar el informe", "Verificar cada cifra del informe", "Publicar los resultados"],
        "step_struct": "Todas las pestañas y columnas coinciden con el esquema. Si algo cambia, la corrida se detiene.",
        "step_alerts": "{n} alertas para el equipo. No detienen la corrida.",
        "step_queries": "Temporadas de necesidad, ajuste de prospectos, motivos de pérdida, capacidad, tendencia de noches de grupo y resultados de propuestas.",
        "step_check_ok": "{a} de {b} cifras encontradas en los resultados.",
        "step_check_held": "Informe retenido: {why}.", "held_numbers": "cifras no encontradas en los resultados ({nums})", "held_api": "la API de Claude no respondió",
        "step_publish": "Esta página y el libro de resultados de {m}, con fecha y sin sobrescribir.",
        "files": [("Data", "Oportunidades, activos, datos públicos, listas y parámetros, en Google Sheets."),
                  ("Respuestas de hoteles", "El formulario mensual de {h} hoteles, en Google Forms."),
                  ("Importaciones", "Una lista de prospectos exportada de Cvent.")],
        "check_cols": ["Revisión", "Resultado", "Estado"], "ok": "Correcto", "review": "Revisar",
        "how_h": "Cómo nos fue en {month}", "vs": "contra",
        "how_note": "Noches de grupo: los mismos {c} hoteles en ambos periodos.{excl} Ocupación y asientos aéreos: datos públicos de todo el destino.",
        "excl": " Fuera de la comparación: {h}, que no envió los dos meses.",
        "seg_h": "Por segmento", "seg_cols": ["Segmento", "{m}", "{ly}", "Cambio"],
        "loss_h": "Por qué perdimos", "loss_sub": "Grupos perdidos en los últimos 12 meses, {n} en total.", "loss_cols": ["Motivo", "Grupos", "Noches estimadas"],
        "need_h": "Temporadas de necesidad, próximos 6 meses",
        "need_cols": ["Mes", "Noches de grupo hace un año", "Índice", "Necesidad", "Grupos ganados", "Hab. pico ganadas", "Oportunidades abiertas"],
        "need_note": "Índice: noches de grupo del mismo mes del año pasado contra el promedio mensual de los últimos 12 meses. Necesidad: meses marcados en los parámetros del destino.",
        "yes": "Sí", "no": "No",
        "sector_h": "Resultados por sector", "sector_sub": "Propuestas decididas en los últimos 12 meses.",
        "sector_cols": ["Sector", "Decididas", "Ganadas", "Perdidas", "Tasa de éxito", "Noches ganadas"], "insufficient": "Datos insuficientes",
        "channel_h": "Resultados por canal", "channel_sub": "Cómo llegó cada oportunidad decidida.", "channel_cols": ["Canal", "Decididas", "Ganadas", "Tasa de éxito"],
        "lostto_h": "Destinos que nos ganaron", "lostto_cols": ["Destino", "Grupos"],
        "origin_h": "Origen de las noches de grupo", "origin_cols": ["Origen", "{m}", "{ly}", "Cambio"],
        "venues_h": "Sedes para {n} asistentes o más", "venues_cols": ["Sede", "Tipo", "Capacidad", "Habitaciones"],
        "pros_h": "{n} prospectos prioritarios, {rn} noches estimadas",
        "pros_p": "Oportunidades abiertas y prospectos importados, ordenados por qué tan bien encajan en el destino. Prioritario: puntaje de {t} o más, sobre 100.",
        "rule_sector": "<b>Sector, hasta {w}.</b> Sector meta del plan: {w}. Secundario: {h}.",
        "rule_need": "<b>Temporada, hasta {w}.</b> Según la ocupación hotelera del mes del evento en los últimos 12 meses. El mes más flojo recibe {w}; el más lleno, 0.",
        "rule_cap": "<b>Capacidad, hasta {w}.</b> Completo hasta {r} habitaciones pico y {a} asistentes. Baja a 0 en {m} habitaciones o en la capacidad de la sede más grande.",
        "lead_cols": ["", "Organización", "Llegada", "Asistentes", "Hab. pico", "Noches est.", "Puntaje", "Por qué"],
        "why_target": "Sector meta del plan", "why_secondary": "Sector secundario", "why_other": "Fuera de los sectores meta",
        "why_occ": "{month} al {o}% de ocupación", "why_fit": "cabe con holgura", "why_tight": "cabe justo", "why_big": "demasiado grande",
        "more_leads": "Ver los otros {n} candidatos",
        "held_h": "Informe retenido", "held_p_nums": "El borrador de este mes usó cifras que no aparecen en los resultados ({nums}), así que no se publica.",
        "held_p_api": "La API de Claude no respondió durante la corrida.", "held_tail": "El operador lo revisa. El tablero y la prospección sí se publican.",
        "verified": "{a} de {b} cifras verificadas",
        "verify_p": "{src}. Claude recibe solo los resultados de las consultas, nunca los datos crudos ni datos personales. Antes de publicar, el script busca cada cifra del informe en los resultados; si alguna no aparece, el informe se retiene.",
        "verify_more": "Ver la verificación cifra por cifra", "verify_cols": ["Cifra en el informe", "¿Está en los resultados?"],
        "notice": "<b>Datos sintéticos para demostración.</b> Hoteles, grupos y cifras inventados, salvo las 6,800 habitaciones del destino (Datatur).",
        "footer": "Página generada por el script a partir de los resultados de la corrida. No se edita a mano.",
        "nav_aria": "Secciones", "title": "Ixtapa-Zihuatanejo, eventos de negocios, {m} (datos sintéticos)",
    },
    "en": {
        "kicker": "Business events, {m}", "verdict": "{n} group room nights in {month}, {p} {dir} than a year ago.", "less": "fewer", "more": "more",
        "hz_aria": "Group room nights by month, last 24 months",
        "hz_caption": "Group room nights by month at the same {c} hotels. Gold: {m}. Light: {ly}.",
        "runmeta": "Run on {month} {d}, {y}, {hm} (Mexico City time). Rules version {v}. Data: {src}.",
        "src_repo": "copies of the destination's files kept in the repository",
        "brief_api": "Written by the Claude API ({model}) from the query results only",
        "brief_file": "Written by Claude from the query results only",
        "tabs": ["The run", "Dashboard", "Prospects", "Brief"],
        "run_h": "How this page was made",
        "run_p": "A fixed, tested script reads the destination's files, calculates every number and publishes the results. Nobody types a figure by hand. Claude only writes the brief, from the results.",
        "steps_h": "Step by step", "read_h": "What it read", "check_h": "Data check",
        "steps": ["Read the files", "Check the structure", "Check the data", "Run the 6 fixed queries", "Write the brief", "Check every number in the brief", "Publish the results"],
        "step_struct": "Every tab and column matches the schema. If anything changes, the run stops.",
        "step_alerts": "{n} alerts for the team. They don't stop the run.",
        "step_queries": "Need periods, prospect fit, loss reasons, capacity, group room night trend and bid results.",
        "step_check_ok": "{a} of {b} numbers found in the results.",
        "step_check_held": "Brief held: {why}.", "held_numbers": "numbers not found in the results ({nums})", "held_api": "the Claude API did not respond",
        "step_publish": "This page and the {m} results workbook, dated and never overwritten.",
        "files": [("Data", "Leads, assets, public data, lists and settings, in Google Sheets."),
                  ("Hotel responses", "The monthly form from {h} hotels, in Google Forms."),
                  ("Imports", "A prospect list exported from Cvent.")],
        "check_cols": ["Check", "Result", "Status"], "ok": "OK", "review": "Review",
        "how_h": "How {month} went", "vs": "vs",
        "how_note": "Group room nights: the same {c} hotels in both periods.{excl} Occupancy and air seats: public data for the whole destination.",
        "excl": " Left out of the comparison: {h}, which did not report both months.",
        "seg_h": "By segment", "seg_cols": ["Segment", "{m}", "{ly}", "Change"],
        "loss_h": "Why we lost", "loss_sub": "Groups lost in the last 12 months, {n} in total.", "loss_cols": ["Reason", "Groups", "Estimated room nights"],
        "need_h": "Need periods, next 6 months",
        "need_cols": ["Month", "Group room nights a year ago", "Index", "Need period", "Groups won", "Peak rooms won", "Open leads"],
        "need_note": "Index: group room nights in the same month last year against the monthly average of the last 12 months. Need period: months flagged in the destination's settings.",
        "yes": "Yes", "no": "No",
        "sector_h": "Results by sector", "sector_sub": "Bids decided in the last 12 months.",
        "sector_cols": ["Sector", "Decided", "Won", "Lost", "Win rate", "Room nights won"], "insufficient": "Not enough data",
        "channel_h": "Results by channel", "channel_sub": "How each decided lead came in.", "channel_cols": ["Channel", "Decided", "Won", "Win rate"],
        "lostto_h": "Destinations that beat us", "lostto_cols": ["Destination", "Groups"],
        "origin_h": "Where group room nights came from", "origin_cols": ["Origin", "{m}", "{ly}", "Change"],
        "venues_h": "Venues for {n} attendees or more", "venues_cols": ["Venue", "Type", "Capacity", "Rooms"],
        "pros_h": "{n} priority prospects, {rn} estimated room nights",
        "pros_p": "Open leads and imported prospects, ranked by how well they fit the destination. Priority: a score of {t} or more, out of 100.",
        "rule_sector": "<b>Sector, up to {w}.</b> Plan target sector: {w}. Secondary: {h}.",
        "rule_need": "<b>Season, up to {w}.</b> Based on hotel occupancy in the event's month over the last 12 months. The quietest month gets {w}; the busiest, 0.",
        "rule_cap": "<b>Capacity, up to {w}.</b> Full points up to {r} peak rooms and {a} attendees, falling to 0 at {m} rooms or the largest venue's capacity.",
        "lead_cols": ["", "Organization", "Arrival", "Attendees", "Peak rooms", "Est. room nights", "Score", "Why"],
        "why_target": "Plan target sector", "why_secondary": "Secondary sector", "why_other": "Not a target sector",
        "why_occ": "{month} at {o}% occupancy", "why_fit": "fits comfortably", "why_tight": "tight fit", "why_big": "too big",
        "more_leads": "Show the other {n} candidates",
        "held_h": "Brief held", "held_p_nums": "This month's draft used numbers that are not in the results ({nums}), so it is not published.",
        "held_p_api": "The Claude API did not respond during the run.", "held_tail": "The operator reviews it. The dashboard and prospects are still published.",
        "verified": "{a} of {b} numbers verified",
        "verify_p": "{src}. Claude receives only the query results, never the raw data or personal data. Before publishing, the script looks for every number in the brief in the results; if any is missing, the brief is held.",
        "verify_more": "Show the number-by-number check", "verify_cols": ["Number in the brief", "In the results?"],
        "notice": "<b>Synthetic data for demonstration.</b> Hotels, groups and figures are invented, except the destination's 6,800 hotel rooms (Datatur).",
        "footer": "Page generated by the script from the run's results. Not edited by hand.",
        "nav_aria": "Sections", "title": "Ixtapa-Zihuatanejo, business events, {m} (synthetic data)",
    },
}


# ------------------------------------------------------------------ one language
def render_lang(lang, R, brief_text, check_df, meta, now):
    L, N = T[lang], NAMES[lang]
    S, t, tot, f = R["S"], R["trend"], R["tot"], R["fit"]
    rm = S["report_month"]
    ly = rm - 12
    M, MLY = mes(rm, lang=lang), mes(ly, lang=lang)
    month = MONTHS[lang][rm.month - 1]
    seg = t["segment"].set_index("Segment")
    prio = f[f.Priority == "Yes"]
    held = brief_text is None
    n_ok = int((check_df["Found in results"] == "Yes").sum()) if len(check_df) else 0
    ins = R["insights"]
    src_brief = L["brief_api"].format(model=meta.get("model")) if meta.get("mode") == "api" else L["brief_file"]
    nums_held = ", ".join(check_df["Number in brief"].astype(str)) if len(check_df) else ""

    # hero
    mon = t["monthly"]
    labels = [mes(m, True, lang) for m in mon["Month"]]
    vals = mon.iloc[:, 1].tolist()
    marks = [(len(vals) - 13, "ly"), (len(vals) - 1, "now")] if len(vals) >= 13 else [(len(vals) - 1, "now")]
    change = seg.loc["Total", "Change"]
    verdict = L["verdict"].format(n=n0(seg.loc["Total", str(rm)]), month=month, p=pct(abs(change)), dir=L["less"] if change < 0 else L["more"])
    runmeta = L["runmeta"].format(d=now.day, month=MONTHS[lang][now.month - 1], y=now.year, hm=now.strftime("%H:%M"), v=meta["version"], src=L["src_repo"])
    hero = f"""
<header class="hero"><div class="wrap">
  <p class="kicker">{esc(L['kicker'].format(m=M))}</p>
  <h1>Ixtapa-Zihuatanejo</h1>
  <p class="verdict">{esc(verdict)}</p>
  <figure class="hz-fig">{horizon(labels, vals, marks, lang, L['hz_aria'])}
    <figcaption>{esc(L['hz_caption'].format(c=t['comparable_hotels'], m=M, ly=MLY))}</figcaption></figure>
  <p class="runmeta">{esc(runmeta)}</p>
</div></header>"""

    # the run
    chk = R["check"]
    n_alert = int((chk.Status == "CHECK").sum())
    why_held = L["held_numbers"].format(nums=nums_held) if nums_held else L["held_api"]
    texts = [tr_check(chk.loc[chk.Check == "Rows read", "Result"].iloc[0], lang), L["step_struct"], L["step_alerts"].format(n=n_alert),
             L["step_queries"], src_brief + ".",
             L["step_check_held"].format(why=why_held) if held else L["step_check_ok"].format(a=n_ok, b=len(check_df)),
             L["step_publish"].format(m=M)]
    states = ["ok", "ok", "warn" if n_alert else "ok", "ok", "ok", "warn" if held else "ok", "ok"]
    step_html = "".join(f'<li class="{st}"><span class="dot" aria-hidden="true">{"✓" if st == "ok" else "!"}</span>'
                        f'<div><b>{esc(a)}</b><p>{esc(b)}</p></div></li>' for a, b, st in zip(L["steps"], texts, states))
    files = "".join(f"<dt>{esc(a)}</dt><dd>{esc(b.format(h=len(R['hotels'])))}</dd>" for a, b in L["files"])
    chk_rows = [[esc(N["check"].get(r.Check, r.Check)), esc(tr_check(r.Result, lang)),
                 f'<span class="tag ok">{L["ok"]}</span>' if r.Status == "OK" else f'<span class="tag warn">{L["review"]}</span>']
                for r in chk.itertuples()]
    corrida = f"""
<section class="tab" data-tab="corrida">
  <div class="lead-in"><h2>{esc(L['run_h'])}</h2><p>{esc(L['run_p'])}</p></div>
  <div class="split">
    <div><h3>{esc(L['steps_h'])}</h3><ol class="steps">{step_html}</ol></div>
    <div><h3>{esc(L['read_h'])}</h3><dl class="files">{files}</dl>
      <h3>{esc(L['check_h'])}</h3>{table(L['check_cols'], chk_rows)}</div>
  </div>
</section>"""

    # dashboard
    score_html = "".join(
        f'<div class="sc-row"><div class="sc-l"><span>{esc(label)}</span><small>{esc(L["vs"])} {esc(cmp_)}</small></div>'
        f'<div class="sc-v">{esc(val)}</div><div class="sc-d">{delta(chg, kind)}</div></div>'
        for label, val, cmp_, chg, kind in scorecard_rows(R, lang))
    segs = [s for s in seg.index if s != "Total"]
    seg_chart = hbar_chart([N["seg"][s] for s in segs], [[seg.loc[s, str(rm)] for s in segs], [seg.loc[s, str(ly)] for s in segs]],
                           names=[M, MLY], title=L["seg_h"])

    def cols(c):
        return [x.format(m=M, ly=MLY) for x in c]
    seg_rows = [[esc(N["seg"][s]), n0(seg.loc[s, str(rm)]), n0(seg.loc[s, str(ly)]), delta(seg.loc[s, "Change"])] for s in seg.index]
    ori = t["origin"].set_index("Origin")
    ori_rows = [[esc(N["ori"][o]), n0(ori.loc[o, str(rm)]), n0(ori.loc[o, str(ly)]), delta(ori.loc[o, "Change"])] for o in ori.index]
    loss = R["loss"]
    rn_by_reason = {r["Loss reason"]: r["room_nights_lost"] for r in ins["lost_last_12_months"]["by_reason"]}
    loss_chart = hbar_chart([N["loss"].get(x, x) for x in loss["Loss reason"]], [loss["Leads lost"].tolist()], colors=(TEAL,), title=L["loss_h"])
    loss_rows = [[esc(N["loss"].get(r["Loss reason"], r["Loss reason"])), n0(r["Leads lost"]), n0(rn_by_reason.get(r["Loss reason"], 0))]
                 for _, r in loss.iterrows()]
    need_rows = [[f'<span class="nw">{esc(mes(r["Month"], lang=lang))}</span>', n0(r["Group room nights, same month last year"]),
                  f'{r["Index vs 12-month average"]:.2f}', L["yes"] if r["Need period (Settings)"] == "Yes" else L["no"],
                  n0(r["Groups won for the month"]), n0(r["Peak rooms won"]), n0(r["Open leads for the month"])]
                 for _, r in R["need"].iterrows()]
    lost_rows = [[esc(N["other"] if r["Lost to"] == "Other" else r["Lost to"]), n0(r["Leads lost"])] for _, r in R["lost_to"].iterrows()]
    cap_rows = [[esc(r["Name"]), esc(N["asset"].get(r["Type"], r["Type"])), n0(r["Max capacity"]),
                 n0(r["Rooms"]) if r["Rooms"] else "—"] for _, r in R["cap"].iterrows()]
    insuff = f'<span class="muted">{esc(L["insufficient"])}</span>'
    box_rows = [[esc(N["sector"].get(r["Sector"], r["Sector"])), n0(r["Decided"]), n0(r["Won"]), n0(r["Lost"]),
                 insuff if isinstance(r["Win rate"], str) else pct(r["Win rate"]), n0(r["Room nights won"])] for _, r in R["box"].iterrows()]
    src_rows = [[esc(N["source"].get(r["source"], r["source"])), n0(r["decided"]), n0(r["won"]),
                 insuff if isinstance(r["win_rate"], str) else pct(r["win_rate"])] for r in ins["win_rate_by_source_last_12_months"]]
    excl = L["excl"].format(h=", ".join(t["excluded_hotels"])) if t["excluded_hotels"] else ""
    tablero = f"""
<section class="tab" data-tab="tablero">
  <div class="block"><h2>{esc(L['how_h'].format(month=month))}</h2><div class="scorecard">{score_html}</div>
    <p class="note">{esc(L['how_note'].format(c=t['comparable_hotels'], excl=excl))}</p></div>
  <div class="block two">
    <div><h2>{esc(L['seg_h'])}</h2>{legend([(M, GOLD), (MLY, TEAL)])}<div class="chart">{seg_chart}</div>
      {table(cols(L['seg_cols']), seg_rows, num=(1, 2, 3), cls="compact")}</div>
    <div><h2>{esc(L['loss_h'])}</h2><p class="sub">{esc(L['loss_sub'].format(n=tot['lost']))}</p><div class="chart">{loss_chart}</div>
      {table(L['loss_cols'], loss_rows, num=(1, 2), cls="compact")}</div>
  </div>
  <div class="block"><h2>{esc(L['need_h'])}</h2>{table(L['need_cols'], need_rows, num=(1, 2, 4, 5, 6))}
    <p class="note">{esc(L['need_note'])}</p></div>
  <div class="block two">
    <div><h2>{esc(L['sector_h'])}</h2><p class="sub">{esc(L['sector_sub'])}</p>{table(L['sector_cols'], box_rows, num=(1, 2, 3, 4, 5), cls="compact")}</div>
    <div><h2>{esc(L['channel_h'])}</h2><p class="sub">{esc(L['channel_sub'])}</p>{table(L['channel_cols'], src_rows, num=(1, 2, 3), cls="compact")}
      <h3 class="gap">{esc(L['lostto_h'])}</h3>{table(L['lostto_cols'], lost_rows, num=(1,), cls="compact")}</div>
  </div>
  <div class="block two">
    <div><h2>{esc(L['origin_h'])}</h2>{table(cols(L['origin_cols']), ori_rows, num=(1, 2, 3), cls="compact")}</div>
    <div><h2>{esc(L['venues_h'].format(n=S['cap_group']))}</h2>{table(L['venues_cols'], cap_rows, num=(2, 3), cls="compact")}</div>
  </div>
</section>"""

    # prospects
    def razon(r):
        sec = L["why_target"] if r["Sector pts"] >= S["w_sector"] else (L["why_secondary"] if r["Sector pts"] > 0 else L["why_other"])
        o = r["Occupancy last year"]
        d = pd.Timestamp(r["Start date"])
        need = L["why_occ"].format(month=MONTHS[lang][d.month - 1], o=f"{o:.0f}") if pd.notna(o) else ""
        cap = L["why_fit"] if r["Capacity pts"] >= S["w_capacity"] else (L["why_tight"] if r["Capacity pts"] > 0 else L["why_big"])
        return ", ".join(x for x in [sec, need, cap] if x) + "."

    def score_cell(r):
        parts = [(r["Sector pts"], TEAL), (r["Need period pts"], GOLD), (r["Capacity pts"], INDIGO)]
        bars = "".join(f'<i style="width:{v}%;background:{c}"></i>' for v, c in parts if v > 0)
        return (f'<div class="score"><b>{int(r["Score"])}</b><span class="stack" aria-hidden="true">{bars}</span>'
                f'<small>{int(r["Sector pts"])} + {int(r["Need period pts"])} + {int(r["Capacity pts"])}</small></div>')

    def lead_rows(df):
        return [[str(int(r["Rank"])),
                 f'<b>{esc(r["Organizer"])}</b><small class="row-sub">{esc(N["tipo"].get(r["Type"], r["Type"]))}, {esc(N["sector"].get(r["Sector"], r["Sector"]).lower() if lang == "es" else N["sector"].get(r["Sector"], r["Sector"]))}</small>',
                 f'<span class="nw">{esc(fecha(r["Start date"], lang))}</span>', n0(r["Attendees"]), n0(r["Peak rooms"]),
                 n0(r["Est. room nights"]), score_cell(r), f'<span class="why">{esc(razon(r))}</span>'] for _, r in df.iterrows()]
    rest = f[f.Priority != "Yes"]
    pp = ins["priority_pipeline"]
    rule_cap = L["rule_cap"].format(w=S["w_capacity"], r=n0(S["comfort_rooms"]), a=n0(S["comfort_att"]), m=n0(S["max_peak"]))
    prospeccion = f"""
<section class="tab" data-tab="prospeccion">
  <div class="lead-in"><h2>{esc(L['pros_h'].format(n=len(prio), rn=n0(pp['est_room_nights'])))}</h2><p>{esc(L['pros_p'].format(t=S['threshold']))}</p></div>
  <div class="rule">
    <div><span class="sw" style="background:{TEAL}"></span>{L['rule_sector'].format(w=S['w_sector'], h=S['w_sector'] // 2)}</div>
    <div><span class="sw" style="background:{GOLD}"></span>{L['rule_need'].format(w=S['w_need'])}</div>
    <div><span class="sw" style="background:{INDIGO}"></span>{rule_cap}</div>
  </div>
  {table(L['lead_cols'], lead_rows(prio), num=(0, 3, 4, 5), cls="leads")}
  <details><summary>{esc(L['more_leads'].format(n=len(rest)))}</summary>{table(L['lead_cols'], lead_rows(rest), num=(0, 3, 4, 5), cls="leads")}</details>
</section>"""

    # brief
    if held:
        body = L["held_p_nums"].format(nums=esc(nums_held)) if nums_held else L["held_p_api"]
        informe = f"""
<section class="tab" data-tab="informe">
  <article class="letter"><h2>{esc(L['held_h'])}</h2><p>{body} {esc(L['held_tail'])}</p></article>
</section>"""
    else:
        chk_tbl = table(L["verify_cols"], [[esc(r["Number in brief"]), L["yes"] if r["Found in results"] == "Yes" else f'<b>{L["no"]}</b>']
                                           for _, r in check_df.iterrows()], cls="compact")
        informe = f"""
<section class="tab" data-tab="informe">
  <article class="letter">{md(brief_text)}</article>
  <aside class="verify"><p><span class="tag ok">{esc(L['verified'].format(a=n_ok, b=len(check_df)))}</span></p>
    <p>{esc(L['verify_p'].format(src=src_brief))}</p>
    <details><summary>{esc(L['verify_more'])}</summary>{chk_tbl}</details></aside>
</section>"""

    tabs = "".join(f'<button role="tab" data-t="{k}">{esc(lbl)}</button>'
                   for k, lbl in zip(["corrida", "tablero", "prospeccion", "informe"], L["tabs"]))
    return f"""
<div class="lang" data-lang="{lang}" lang="{lang}">
<div class="notice">{L['notice']}</div>
{hero}
<nav class="tabs" aria-label="{esc(L['nav_aria'])}"><div class="wrap">
  <div class="tablist" role="tablist">{tabs}</div>
  <div class="langs" role="group" aria-label="Idioma / Language">
    <button data-setlang="es" aria-pressed="{str(lang == 'es').lower()}">ES</button><button data-setlang="en" aria-pressed="{str(lang == 'en').lower()}">EN</button>
  </div>
</div></nav>
<main><div class="wrap">{corrida}{tablero}{prospeccion}{informe}</div></main>
<footer><div class="wrap">{esc(L['footer'])}</div></footer>
</div>"""


# ------------------------------------------------------------------ page
def render(R, briefs, checks, meta):
    """briefs, checks: dicts keyed by language ('es', 'en'). A brief of None means it was held."""
    now = datetime.now(ZoneInfo("America/Mexico_City"))
    empty = pd.DataFrame(columns=["Number in brief", "Found in results"])
    body = "".join(render_lang(lang, R, briefs.get(lang), checks.get(lang, empty), meta, now) for lang in LANGS)
    return PAGE.replace("%%TITLE%%", esc(T["es"]["title"].format(m=mes(R["S"]["report_month"])))).replace("%%BODY%%", body)


PAGE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>%%TITLE%%</title>
<style>
@font-face { font-family: "Outfit"; font-weight: 300; font-display: swap; src: url("fonts/outfit-latin-300-normal.woff2") format("woff2"); }
@font-face { font-family: "Outfit"; font-weight: 400; font-display: swap; src: url("fonts/outfit-latin-400-normal.woff2") format("woff2"); }
@font-face { font-family: "Outfit"; font-weight: 500; font-display: swap; src: url("fonts/outfit-latin-500-normal.woff2") format("woff2"); }
@font-face { font-family: "Hanken Grotesk"; font-weight: 400; font-display: swap; src: url("fonts/hanken-grotesk-latin-400-normal.woff2") format("woff2"); }
@font-face { font-family: "Hanken Grotesk"; font-weight: 500; font-display: swap; src: url("fonts/hanken-grotesk-latin-500-normal.woff2") format("woff2"); }
@font-face { font-family: "Hanken Grotesk"; font-weight: 600; font-display: swap; src: url("fonts/hanken-grotesk-latin-600-normal.woff2") format("woff2"); }
@font-face { font-family: "Hanken Grotesk"; font-weight: 700; font-display: swap; src: url("fonts/hanken-grotesk-latin-700-normal.woff2") format("woff2"); }
:root {
  --ocean: #0e2a33; --ocean-2: #133843; --teal: #00839b; --gold: #c9801a; --horizon: #e8a63c;
  --mist: #f3f6f5; --white: #ffffff; --ink: #14262c; --slate: #5d7178; --line: #dfe6e6; --line-soft: #edf1f1;
  --up: #0a7b5c; --down: #b23a2b; --warn: #a15c07; --warn-bg: #fdf3e2; --ok-bg: #e6f3ee;
  --display: "Outfit", "Avenir Next", "Segoe UI", sans-serif;
  --sans: "Hanken Grotesk", "Helvetica Neue", Arial, sans-serif;
  color-scheme: light;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--mist); color: var(--ink); font: 400 15.5px/1.55 var(--sans); font-feature-settings: "tnum" 1, "lnum" 1; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 0 28px; }
.lang { display: none; } .lang.on { display: block; }
.no-js .lang[data-lang="es"] { display: block; }
.notice { background: #8f2a1f; color: #fff; font-size: 13px; text-align: center; padding: 7px 16px; letter-spacing: .01em; }
.notice b { font-weight: 600; }

/* hero */
.hero { background: radial-gradient(120% 140% at 85% 0%, var(--ocean-2) 0%, var(--ocean) 55%); color: #e9f0f1; padding: 54px 0 26px; }
.kicker { margin: 0 0 10px; font-size: 15px; color: #a9c3c8; }
.hero h1 { margin: 0; font: 300 clamp(46px, 7.6vw, 92px)/1 var(--display); letter-spacing: -.025em; color: #fff; }
.verdict { margin: 16px 0 0; font-size: clamp(17px, 2vw, 21px); color: #d6e4e6; max-width: 60ch; }
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

/* tabs and language switch */
nav.tabs { position: sticky; top: 0; z-index: 5; background: rgba(255,255,255,.96); backdrop-filter: saturate(1.4) blur(6px); border-bottom: 1px solid var(--line); }
nav.tabs .wrap { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.tablist { display: flex; gap: 30px; overflow-x: auto; }
.tablist button { appearance: none; background: none; border: 0; padding: 17px 0 15px; font: 500 15px var(--sans); color: var(--slate); cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; }
.tablist button:hover { color: var(--ink); }
.tablist button[aria-selected="true"] { color: var(--ink); font-weight: 600; border-bottom-color: var(--teal); }
.langs { display: flex; border: 1px solid var(--line); border-radius: 999px; padding: 3px; flex: none; }
.langs button { appearance: none; border: 0; background: none; font: 600 12.5px var(--sans); color: var(--slate); padding: 5px 11px; border-radius: 999px; cursor: pointer; letter-spacing: .03em; }
.langs button[aria-pressed="true"] { background: var(--ocean); color: #fff; }
nav.tabs button:focus-visible, summary:focus-visible { outline: 2px solid var(--teal); outline-offset: 3px; }

main { padding: 44px 0 64px; }
.tab { display: none; } .tab.on { display: block; }
.no-js .tab { display: block; }
h2 { font: 400 28px/1.2 var(--display); margin: 0 0 16px; color: var(--ocean); letter-spacing: -.015em; }
h3 { font: 600 15px var(--sans); margin: 0 0 12px; color: var(--ink); }
h3.gap { margin-top: 30px; }
.sub { margin: -8px 0 14px; color: var(--slate); font-size: 14px; }
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
.sc-v { font: 300 30px/1 var(--display); color: var(--ocean); letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.sc-d { text-align: right; }
.d { font-weight: 600; font-size: 14px; white-space: nowrap; color: var(--slate); }
.d b { font-size: 10px; vertical-align: 1px; }
.d.up { color: var(--up); } .d.down { color: var(--down); }
@media (max-width: 560px) {
  .sc-row { grid-template-columns: 1fr auto; row-gap: 6px; }
  .sc-l { grid-column: 1 / -1; }
  .hero { padding-top: 38px; }
  .wrap { padding: 0 18px; }
  nav.tabs .wrap { flex-wrap: wrap; row-gap: 0; }
  .langs { order: -1; margin: 10px 0 2px auto; }
  .tablist { width: 100%; gap: 18px; }
  .tablist button { padding: 12px 0 12px; font-size: 14.5px; }
}

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
.steps { list-style: none; margin: 0; padding: 0; }
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

/* prospects */
.rule { display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; margin: 0 0 22px; font-size: 14px; color: var(--slate); }
.rule b { color: var(--ink); font-weight: 600; }
@media (max-width: 920px) { .rule { grid-template-columns: 1fr; gap: 12px; } }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 8px; vertical-align: 0; }
[data-tab="prospeccion"] > .tw, [data-tab="prospeccion"] details { background: var(--white); border-radius: 18px; padding: 26px 30px; }
[data-tab="prospeccion"] details { margin-top: 18px; }
table.leads td { padding-top: 13px; padding-bottom: 13px; }
.row-sub { display: block; color: var(--slate); font-size: 12.5px; margin-top: 2px; }
.score { display: flex; align-items: center; gap: 10px; white-space: nowrap; }
.score b { font: 400 22px/1 var(--display); color: var(--ocean); min-width: 30px; text-align: right; }
.stack { display: flex; gap: 2px; width: 96px; height: 8px; background: var(--line-soft); border-radius: 4px; overflow: hidden; }
.stack i { display: block; height: 100%; }
.score small { color: var(--slate); font-size: 12px; }
.why { color: var(--slate); font-size: 13.5px; }
summary { cursor: pointer; font-weight: 600; color: var(--teal); }
details[open] summary { margin-bottom: 14px; }

/* brief */
.letter { background: var(--white); border-radius: 18px; padding: 52px 64px; max-width: 900px; font-size: 16.5px; line-height: 1.68; }
@media (max-width: 920px) { .letter { padding: 30px 22px; } }
.letter h2 { font-size: 34px; line-height: 1.12; margin-bottom: 8px; font-weight: 300; }
.letter h2 + p { color: var(--slate); font-size: 13.5px; margin-top: 0; }
.letter h3 { font: 400 22px/1.25 var(--display); color: var(--ocean); margin: 34px 0 10px; letter-spacing: -.01em; }
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
%%BODY%%
<script>
(function () {
  document.body.classList.remove('no-js');
  var TABS = ['corrida', 'tablero', 'prospeccion', 'informe'];
  var lang = 'es', tab = 'tablero';
  try { var saved = localStorage.getItem('dmo-lang'); if (saved === 'en' || saved === 'es') lang = saved; } catch (e) {}
  var h = location.hash.slice(1).split('-');
  if (TABS.indexOf(h[0]) >= 0) tab = h[0];
  if (h[1] === 'en' || h[1] === 'es') lang = h[1];

  function apply(push) {
    document.documentElement.lang = lang;
    document.querySelectorAll('.lang').forEach(function (d) { d.classList.toggle('on', d.dataset.lang === lang); });
    document.querySelectorAll('.tablist button').forEach(function (b) { b.setAttribute('aria-selected', b.dataset.t === tab); });
    document.querySelectorAll('.tab').forEach(function (s) { s.classList.toggle('on', s.dataset.tab === tab); });
    document.querySelectorAll('.langs button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.setlang === lang); });
    if (push) { try { history.replaceState(null, '', '#' + tab + '-' + lang); } catch (e) { /* sandboxed preview */ } }
  }
  document.querySelectorAll('.tablist button').forEach(function (b) {
    b.addEventListener('click', function () {
      tab = b.dataset.t; apply(true);
      var n = document.querySelector('.lang.on nav.tabs');
      if (n && window.scrollY > n.offsetTop) { try { window.scrollTo({ top: n.offsetTop, behavior: 'smooth' }); } catch (e) {} }
    });
  });
  document.querySelectorAll('.langs button').forEach(function (b) {
    b.addEventListener('click', function () {
      var y = window.scrollY;
      lang = b.dataset.setlang; apply(true);
      try { localStorage.setItem('dmo-lang', lang); } catch (e) {}
      try { window.scrollTo(0, y); } catch (e) {}
    });
  });
  window.addEventListener('hashchange', function () {
    var p = location.hash.slice(1).split('-');
    if (TABS.indexOf(p[0]) >= 0) tab = p[0];
    if (p[1] === 'en' || p[1] === 'es') lang = p[1];
    apply(false);
  });
  apply(false);
  if (location.hash) { requestAnimationFrame(function () { try { window.scrollTo(0, 0); } catch (e) {} }); }
})();
</script>
</body>
</html>
"""
