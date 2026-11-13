"""Have the Claude API write the monthly brief, in Spanish, from the query results only.

Claude receives brief_payload (counts, rates, ranked leads: no raw tables, no
personal data). It never calculates. Every number in its draft is then checked
against the payload by build_results.check_brief; one redraft is allowed, then
the brief is held.
"""
import json
import os
import time
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 8000
# Labels that come from the data in English and must never appear in the Spanish brief.
ENGLISH_LABELS = ["too big for the destination", "fits comfortably", "tight fit", "Air access", "Safety perception",
                  "Venue too small", "Dates not available", "Destination profile", "Event cancelled", "Hotel referral",
                  "Trade show", "Medical association", "Insurance & finance", "Mexican corporate", "Government & other",
                  "room nights", "Domestic", "International", "priority lead", "priority prospect", "won group"]

REQUIRED_SECTIONS = {
    "es": ["## Desempeño del mes", "## Tres hallazgos", "## Tres acciones", "## Para vigilar", "## Notas sobre los datos"],
    "en": ["## Month performance", "## Three findings", "## Three actions", "## Watch", "## Data notes"],
}

SYSTEM = """Eres el estratega de ventas de una oficina de convenciones y visitantes (OCV) pequeña en México. Cada mes escribes, para el director o la directora, un informe de una página que le dice qué pasó, por qué importa y qué hacer este mes. Un buen informe cambia lo que el equipo hace mañana; un informe genérico no sirve.

CIFRAS (regla absoluta: un programa revisa cada cifra y retiene el informe si una no está en los resultados)
1. Usa SOLO cifras que aparezcan tal cual en los resultados JSON. No calcules nada: no sumes, no restes, no saques porcentajes, promedios ni diferencias que no estén ahí. Tampoco aproximes ("casi la mitad", "más de 9,000"): escribe la cifra exacta o no la escribas.
2. Cifras con coma de miles (8,580). Cambios y tasas vienen como fracción (-0.048): escríbelos como porcentaje con un decimal (4.8%), usando "bajó" o "subió" en lugar del signo.
3. Las noches de oportunidades perdidas, abiertas y prioritarias son estimaciones (habitaciones pico por noches): di "noches estimadas".
4. Fechas en español ("18 de noviembre de 2026"). La fecha límite de las acciones es "act_by" o antes.

DESEMPEÑO DEL MES (sección de arriba)
- El programa inserta una tabla de desempeño donde pongas [TABLA], con las cifras de "performance_scorecard". No la escribas tú.
- Debajo, escribe la lectura: tres o cuatro frases que digan, en términos relativos, cómo le fue al destino en grupos este mes: contra el año pasado, en el año a la fecha y contra el mercado (ocupación hotelera y asientos aéreos). ¿Ganamos o perdimos terreno? ¿La demanda (oportunidades recibidas) acompaña o no? Cierra con la decisión que se le pide a la Dirección.
- Usa las cifras de "performance_scorecard" tal cual (los cambios en puntos se escriben como "4.9 puntos").

QUÉ BUSCAR PARA LOS HALLAZGOS (los resultados ya traen estos cálculos; úsalos)
- Los hallazgos van más allá de la tabla: explican causas, contrastes y oportunidades. No repitas la tabla.
- Contrastes que el equipo no ve a simple vista: el motivo de pérdida más frecuente contra el que más noches costó; el canal que más gana contra el que más se usa; el sector con mejor tasa de éxito contra el que más tiempo consume.
- Urgencias: oportunidades abiertas hace mucho ("stale_open_leads") y las que llegan pronto ("starting_within_3_months", "days_from_month_end_to_event").
- Temporadas de necesidad: qué meses flojos tienen poco o nada en cartera ("next_12_months", "need_months_without_priority_leads").
- Qué está en juego: noches estimadas de la cartera prioritaria y de los 5 prospectos más grandes.
- No inventes causas ni datos del destino (vuelos, precios, eventos) que no estén en los resultados. Si los datos no dicen por qué pasó algo, la acción es averiguarlo con alguien concreto.

ACCIONES
- Exactamente tres. Primero lo que vence antes (un evento próximo con la oportunidad aún abierta va primero); después, por noches en juego, de mayor a menor.
- Cada una nombra organizaciones concretas de los resultados, un responsable (Dirección, Ventas o Hoteles socios), una fecha límite y lo que está en juego en noches.
- Las noches en juego de una acción son las de las organizaciones que nombra, una por una, con su propio "Est. room nights" (por ejemplo: "390 noches estimadas en A, 340 en B y 304 en C"). Nunca uses para ellas un total de mes, de sector o de la cartera, y no sumes.
- Prohibido lo genérico: nada de "fortalecer la promoción", "mejorar la marca", "aprovechar oportunidades", "dar seguimiento" sin a quién y para cuándo.
- No propongas perseguir ni conseguir una oportunidad marcada "too big for the destination" o que no sea prioritaria ("priority": false); a esas solo se les puede proponer cerrarlas o liberarlas. Para crecer, usa los prospectos prioritarios.
- Fechas cruzadas: antes de escribir una acción, busca a cada organización en "date_clashes". Si aparece, la acción dice con qué grupos coincide en fechas y cuántas habitaciones pico suman en la noche más cargada ("most_peak_rooms_on_one_night"), e incluye confirmar con Hoteles socios que pueden alojar a todos esos grupos en esas fechas. Nunca propongas dos grupos que coinciden en fechas como si fueran independientes.
- Tamaño: si una acción propone una oportunidad con "Capacity fit": "tight", di que está por encima del tamaño cómodo: sus asistentes y habitaciones pico contra los cómodos ("comfortable_attendees", "comfortable_peak_rooms") y cuántos espacios del destino la pueden alojar ("Venues that fit"). No nombres esos espacios.

ESTILO
- Español de México, directo, para alguien ocupado. Entre 350 y 450 palabras. Sin adjetivos de relleno, sin exclamaciones, sin emojis.
- Traduce las etiquetas en inglés (Association = asociaciones, Corporate = corporativo, Incentive = incentivos, Government & other = gobierno y otros, Medical association = asociaciones médicas, Insurance & finance = seguros y finanzas, Mexican corporate = corporativo mexicano, Pharma = farmacéutico, Sports = deportes, Price = precio, Air access = acceso aéreo, Safety perception = percepción de seguridad, Venue too small = sede insuficiente, Dates not available = fechas no disponibles, Hotel referral = referencia de hoteles, Trade show = ferias, RFP (Cvent) = solicitudes por Cvent, Direct = contacto directo, Referral = recomendación, Domestic = nacional, International = internacional, fits = cabe con holgura, tight = cabe justo, priority lead = oportunidad prioritaria, priority prospect = prospecto prioritario, won group = grupo ganado, too big for the destination = demasiado grande para el destino). Ninguna etiqueta en inglés puede aparecer en el informe. Nombres de organizaciones, hoteles y destinos van tal cual.
- Los datos son sintéticos: conserva la segunda línea del formato tal cual.

Devuelve SOLO el informe en Markdown, con exactamente este formato:

# Informe de eventos de negocios, {mes y año del informe, en español}
DATOS SINTÉTICOS. Prototipo: los hoteles, grupos y cifras son inventados.

## Desempeño del mes
[TABLA]
Lectura: tres o cuatro frases en términos relativos y la decisión que se le pide a la Dirección.

## Tres hallazgos
1. **Titular con su cifra.** Qué pasó, con una comparación. Por qué importa, en noches o grupos.
2. **...** ...
3. **...** ...

## Tres acciones para {mes de entrega, en español}
1. **Verbo + qué + con quién.** Responsable: ... · Fecha límite: ... · En juego: ... noches estimadas. Una frase de detalle.
2. **...** ...
3. **...** ...

## Para vigilar
- Uno o dos riesgos, cada uno con su cifra.

## Notas sobre los datos
- Una línea por cada alerta de "data_check_issues", con lo que hay que corregir.
"""

SYSTEM_EN = """You are the sales strategist for a small convention and visitors bureau (CVB) in Mexico. Each month you write a one-page brief for the director that says what happened, why it matters and what to do this month. A good brief changes what the team does tomorrow; a generic one is useless.

NUMBERS (absolute rule: a program checks every number and holds the brief if one is not in the results)
1. Use ONLY numbers that appear exactly as they are in the JSON results. Calculate nothing: no sums, differences, percentages or averages that are not there. Do not approximate ("almost half", "over 9,000"): write the exact number or leave it out.
2. Numbers with comma thousands separators (8,580). Changes and rates come as fractions (-0.048): write them as a percentage with one decimal (4.8%), using "fell" or "rose" instead of the sign.
3. Room nights for lost, open and priority leads are estimates (peak rooms times nights): say "estimated room nights".
4. Dates in English ("November 18, 2026"). The deadline for actions is "act_by" or earlier.

MONTH PERFORMANCE (top section)
- The program inserts a performance table where you put [TABLA], with the numbers from "performance_scorecard". Do not write it yourself.
- Below it, write the reading: three or four sentences that say, in relative terms, how the destination did in groups this month: against last year, year to date and against the market (hotel occupancy and air seats). Did we gain or lose ground? Does demand (leads received) support it or not? End with the decision the director needs to make.
- Use the "performance_scorecard" numbers exactly (changes in points are written as "4.9 points").

WHAT TO LOOK FOR IN THE FINDINGS (the results already contain these calculations; use them)
- The findings go beyond the table: they explain causes, contrasts and opportunities. Do not repeat the table.
- Contrasts the team cannot see at a glance: the most frequent loss reason against the one that cost the most room nights; the channel that wins most against the one used most; the sector with the best win rate against the one that takes most time.
- Urgencies: leads open for a long time ("stale_open_leads") and those arriving soon ("starting_within_3_months", "days_from_month_end_to_event").
- Need periods: which quiet months have little or nothing in the pipeline ("next_12_months", "need_months_without_priority_leads").
- What is at stake: estimated room nights in the priority pipeline and the 5 largest prospects.
- Do not invent causes or facts about the destination (flights, prices, events) that are not in the results. If the data do not say why something happened, the action is to find out, with a named person.

ACTIONS
- Exactly three. First whatever is due soonest (an upcoming event with the lead still open goes first); then by room nights at stake, largest first.
- Each names specific organizations from the results, an owner (Director, Sales or Partner hotels), a deadline and what is at stake in room nights.
- The room nights at stake in an action are those of the organizations it names, one by one, each with its own "Est. room nights" (for example: "390 estimated room nights at A, 340 at B and 304 at C"). Never use a month, sector or pipeline total for them, and do not add them up.
- No generic advice: nothing like "strengthen promotion", "improve the brand", "seize opportunities", or "follow up" without who and by when.
- Never propose pursuing or winning a lead marked "too big for the destination" or not a priority ("priority": false); for those, the only action you may propose is to close or release them. For growth, use the priority prospects.
- Overlapping dates: before writing an action, look up each organization in "date_clashes". If it is there, the action says which groups share its dates and how many peak rooms they add up to on the busiest night ("most_peak_rooms_on_one_night"), and includes confirming with Partner hotels that they can house all those groups on those dates. Never propose two groups with overlapping dates as if they were independent.
- Size: if an action proposes a lead with "Capacity fit": "tight", say it is above the comfortable size: its attendees and peak rooms against the comfortable ones ("comfortable_attendees", "comfortable_peak_rooms") and how many of the destination's spaces can hold it ("Venues that fit"). Do not name those spaces.

STYLE
- Plain, direct English for a busy executive. Between 350 and 450 words. No filler adjectives, no exclamation marks, no emojis.
- Translate the labels in the results into plain English (Association, Corporate, Incentive, Government and other, Medical association, Insurance and finance, Mexican corporate, Pharmaceutical, Sports, Price, Air access, Safety perception, Venue too small, Dates not available, Hotel referral, Trade show, Cvent RFP, Direct contact, Referral, Domestic, International). Organization, hotel and destination names stay as they are.
- The data are synthetic: keep the second line of the format exactly as it is.

Return ONLY the brief in Markdown, in exactly this format:

# Business events brief, {month and year of the report}
SYNTHETIC DATA. Prototype: hotels, groups and figures are invented.

## Month performance
[TABLA]
Reading: three or four sentences in relative terms and the decision the director needs to make.

## Three findings
1. **Headline with its number.** What happened, with a comparison. Why it matters, in room nights or groups.
2. **...** ...
3. **...** ...

## Three actions for {delivery month}
1. **Verb + what + with whom.** Owner: ... · Deadline: ... · At stake: ... estimated room nights. One sentence of detail.
2. **...** ...
3. **...** ...

## Watch
- One or two risks, each with its number.

## Data notes
- One line for each alert in "data_check_issues", with what needs fixing.
"""


def _post(body, key, timeout=120):
    req = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def call_claude(user_text, model, key, post=None, retries=2, system=None):
    post = post or _post
    body = {"model": model, "max_tokens": MAX_TOKENS, "system": system or SYSTEM,
            "messages": [{"role": "user", "content": user_text}]}
    last = None
    for attempt in range(retries + 1):
        try:
            resp = post(body, key)
            text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text").strip()
            if not text:
                raise RuntimeError(f"empty response (stop_reason={resp.get('stop_reason')})")
            return text, resp.get("model", model), resp.get("stop_reason"), resp.get("usage", {})
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            last = RuntimeError(f"HTTP {e.code}: {detail}")
            if e.code in (400, 401, 403, 404):  # bad request or key: retrying won't help
                break
        except Exception as e:  # network, timeout, empty reply
            last = e
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Claude API call failed: {last}")


def structure_problems(text, stop_reason, lang="es"):
    """A brief that was cut off or is missing a section is not a brief."""
    problems = []
    if stop_reason == "max_tokens":
        problems.append("el texto se cortó antes de terminar" if lang == "es" else "the text was cut off before the end")
    missing = [h[3:] for h in REQUIRED_SECTIONS[lang] if h not in text]
    if missing:
        problems.append(("faltan secciones: " if lang == "es" else "missing sections: ") + ", ".join(missing))
    if lang == "es":
        leaks = [w for w in ENGLISH_LABELS if w.lower() in text.lower()]
        if leaks:
            problems.append("etiquetas en inglés en el informe: " + ", ".join(f'"{w}"' for w in leaks))
    if "[TABLA]" not in text:
        problems.append("falta [TABLA] bajo 'Desempeño del mes'" if lang == "es" else "missing [TABLA] under 'Month performance'")
    return problems


def draft_brief(payload, destination, check, model=None, key=None, post=None, log=print, lang="es"):
    """Returns (brief_text or None, info dict). check(text) -> DataFrame with 'Found in results'."""
    model = model or os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)
    key = key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    data = json.dumps(payload, ensure_ascii=False, default=str, indent=1)
    if lang == "en":
        base = f"Destination: {destination}\nReport month: {payload['report_month']}\n\nQuery results (JSON):\n```json\n{data}\n```"
    else:
        base = f"Destino: {destination}\nMes del informe: {payload['report_month']}\n\nResultados de las consultas (JSON):\n```json\n{data}\n```"
    system = SYSTEM_EN if lang == "en" else SYSTEM
    info = {"model": model, "attempts": 0, "bad_numbers": [], "problems": []}
    prompt = base
    for attempt in (1, 2):
        info["attempts"] = attempt
        text, used_model, stop, usage = call_claude(prompt, model, key, post=post, system=system)
        info["model"] = used_model
        problems = structure_problems(text, stop, lang)
        res = check(text)
        bad = res.loc[res["Found in results"] != "Yes", "Number in brief"].tolist()
        log(f"   [{lang}] borrador {attempt}: {len(text.split())} palabras, fin={stop}, tokens={usage.get('output_tokens', '?')}; "
            f"{len(res)} cifras, {len(bad)} no encontradas {bad if bad else ''}; estructura: {'; '.join(problems) or 'OK'}")
        if not bad and not problems:
            info["bad_numbers"], info["problems"] = [], []
            return text, info
        info["bad_numbers"], info["problems"] = bad, problems
        fixes = []
        if lang == "en":
            if bad:
                fixes.append("used numbers that are NOT in the results: " + ", ".join(bad) + ". You probably calculated them; use only numbers that appear exactly as they are")
            if problems:
                fixes.append("did not follow the format (" + "; ".join(problems) + "); deliver the complete brief, with every section")
            prompt = base + "\n\nYour previous draft " + " and ".join(fixes) + ". Rewrite the whole brief."
        else:
            if bad:
                fixes.append("usó cifras que NO están en los resultados: " + ", ".join(bad)
                             + ". Probablemente las calculaste; usa solo cifras que aparezcan tal cual")
            if problems:
                fixes.append("no cumplió el formato (" + "; ".join(problems) + "); entrega el informe completo, con todas las secciones")
            prompt = base + "\n\nTu borrador anterior " + " y ".join(fixes) + ". Reescribe el informe completo."
    return None, info


TRANSLATE_EN = """You translate a monthly business events brief from Mexican Spanish into plain, direct English for a busy executive. The Spanish brief has already been checked; your English must say exactly the same thing.

Rules:
1. Keep every number exactly as it is: same digits, same comma thousands separators, same decimals. Do not add, drop, round or recalculate any number.
2. Keep the Markdown structure line for line, and keep the token [TABLA] on its own line exactly where it is.
3. Use exactly these lines and headings:
   - Title: "# Business events brief, {month and year}"
   - Second line: "SYNTHETIC DATA. Prototype: hotels, groups and figures are invented."
   - "## Desempeño del mes" becomes "## Month performance"
   - "## Tres hallazgos" becomes "## Three findings"
   - "## Tres acciones para {mes}" becomes "## Three actions for {month}"
   - "## Para vigilar" becomes "## Watch"
   - "## Notas sobre los datos" becomes "## Data notes"
   - "Lectura:" becomes "Reading:"
4. Owners: Dirección = Director, Ventas = Sales, Hoteles socios = Partner hotels. "Responsable" = "Owner", "Fecha límite" = "Deadline", "En juego" = "At stake", "noches estimadas" = "estimated room nights", "puntos" = "points".
5. Dates in English: "18 de noviembre de 2026" becomes "November 18, 2026".
6. Organization, hotel and destination names stay exactly as they are.

Return ONLY the English brief in Markdown.
"""


def numbers_in(text):
    import re
    text = re.sub(r"(?m)^\s*\d+\.\s", "", text)
    return sorted(m.rstrip(",.").replace(",", "") for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text))


def translate_brief(es_text, check, model=None, key=None, post=None, log=print):
    """English version of the verified Spanish brief. Same checks, plus: the same numbers as the Spanish."""
    model = model or os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)
    key = key or os.environ.get("ANTHROPIC_API_KEY")
    info = {"model": model, "attempts": 0, "bad_numbers": [], "problems": [], "translated": True}
    want = numbers_in(es_text)
    prompt = f"Spanish brief:\n\n{es_text}"
    for attempt in (1, 2):
        info["attempts"] = attempt
        text, used_model, stop, usage = call_claude(prompt, model, key, post=post, system=TRANSLATE_EN)
        info["model"] = used_model
        problems = structure_problems(text, stop, "en")
        got = numbers_in(text)
        if got != want:
            missing = sorted(set(want) - set(got))
            extra = sorted(set(got) - set(want))
            problems.append("numbers differ from the Spanish brief"
                            + (f" (missing: {', '.join(missing)})" if missing else "") + (f" (added: {', '.join(extra)})" if extra else ""))
        res = check(text)
        bad = res.loc[res["Found in results"] != "Yes", "Number in brief"].tolist()
        log(f"   [en] traducción {attempt}: {len(text.split())} palabras, fin={stop}; {len(res)} cifras, {len(bad)} no encontradas; "
            f"estructura: {'; '.join(problems) or 'OK'}")
        if not bad and not problems:
            info["bad_numbers"], info["problems"] = [], []
            return text, info
        info["bad_numbers"], info["problems"] = bad, problems
        prompt = (f"Spanish brief:\n\n{es_text}\n\nYour previous translation had problems: " + "; ".join(problems + ([f"numbers not in the results: {', '.join(bad)}"] if bad else []))
                  + ". Translate again, keeping every number exactly as in the Spanish.")
    return None, info
