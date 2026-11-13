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
REQUIRED_SECTIONS = ["## Desempeño del mes", "## Tres hallazgos", "## Tres acciones", "## Para vigilar", "## Notas sobre los datos"]

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
- Prohibido lo genérico: nada de "fortalecer la promoción", "mejorar la marca", "aprovechar oportunidades", "dar seguimiento" sin a quién y para cuándo.

ESTILO
- Español de México, directo, para alguien ocupado. Entre 350 y 450 palabras. Sin adjetivos de relleno, sin exclamaciones, sin emojis.
- Traduce las etiquetas en inglés (Association = asociaciones, Corporate = corporativo, Incentive = incentivos, Government & other = gobierno y otros, Medical association = asociaciones médicas, Insurance & finance = seguros y finanzas, Mexican corporate = corporativo mexicano, Pharma = farmacéutico, Sports = deportes, Price = precio, Air access = acceso aéreo, Safety perception = percepción de seguridad, Venue too small = sede insuficiente, Dates not available = fechas no disponibles, Hotel referral = referencia de hoteles, Trade show = ferias, RFP (Cvent) = solicitudes por Cvent, Direct = contacto directo, Referral = recomendación, Domestic = nacional, International = internacional). Nombres de organizaciones, hoteles y destinos van tal cual.
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


def _post(body, key, timeout=120):
    req = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def call_claude(user_text, model, key, post=None, retries=2):
    post = post or _post
    body = {"model": model, "max_tokens": MAX_TOKENS, "system": SYSTEM,
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


def structure_problems(text, stop_reason):
    """A brief that was cut off or is missing a section is not a brief."""
    problems = []
    if stop_reason == "max_tokens":
        problems.append("el texto se cortó antes de terminar")
    missing = [h[3:] for h in REQUIRED_SECTIONS if h not in text]
    if missing:
        problems.append("faltan secciones: " + ", ".join(missing))
    if "[TABLA]" not in text:
        problems.append("falta [TABLA] bajo 'Desempeño del mes'")
    return problems


def draft_brief(payload, destination, check, model=None, key=None, post=None, log=print):
    """Returns (brief_text or None, info dict). check(text) -> DataFrame with 'Found in results'."""
    model = model or os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)
    key = key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    base = (f"Destino: {destination}\nMes del informe: {payload['report_month']}\n\n"
            f"Resultados de las consultas (JSON):\n```json\n{json.dumps(payload, ensure_ascii=False, default=str, indent=1)}\n```")
    info = {"model": model, "attempts": 0, "bad_numbers": [], "problems": []}
    prompt = base
    for attempt in (1, 2):
        info["attempts"] = attempt
        text, used_model, stop, usage = call_claude(prompt, model, key, post=post)
        info["model"] = used_model
        problems = structure_problems(text, stop)
        res = check(text)
        bad = res.loc[res["Found in results"] != "Yes", "Number in brief"].tolist()
        log(f"   borrador {attempt}: {len(text.split())} palabras, fin={stop}, tokens={usage.get('output_tokens', '?')}; "
            f"{len(res)} cifras, {len(bad)} no encontradas {bad if bad else ''}; estructura: {'; '.join(problems) or 'OK'}")
        if not bad and not problems:
            info["bad_numbers"], info["problems"] = [], []
            return text, info
        info["bad_numbers"], info["problems"] = bad, problems
        fixes = []
        if bad:
            fixes.append("usó cifras que NO están en los resultados: " + ", ".join(bad)
                         + ". Probablemente las calculaste; usa solo cifras que aparezcan tal cual")
        if problems:
            fixes.append("no cumplió el formato (" + "; ".join(problems) + "); entrega el informe completo, con todas las secciones")
        prompt = base + "\n\nTu borrador anterior " + " y ".join(fixes) + ". Reescribe el informe completo."
    return None, info
