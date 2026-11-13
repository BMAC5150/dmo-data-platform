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

SYSTEM = """Eres el analista de inteligencia de mercado de una oficina de convenciones y visitantes (OCV) pequeña en México. Escribes el informe mensual de eventos de negocios para el director o la directora.

Reglas, sin excepción:
1. Usa SOLO las cifras que aparecen en los resultados JSON que te paso. No calcules nada nuevo: no sumes, no restes, no saques porcentajes ni promedios que no estén en los resultados. Si una cifra no está, no la escribas.
2. Escribe las cifras tal como vienen, con coma de miles (8,580). Los cambios y tasas vienen como fracción (por ejemplo -0.048): escríbelos como porcentaje con un decimal (4.8%). Puedes decir "bajó" o "subió" en vez de usar el signo.
3. Español de México, claro y directo, para alguien ocupado. Sin rodeos, sin adjetivos de relleno, sin exclamaciones, sin emojis.
4. Traduce las etiquetas en inglés de los resultados (Association = asociaciones, Corporate = corporativo, Incentive = incentivos, Government & other = gobierno y otros, Medical association = asociaciones médicas, Insurance & finance = seguros y finanzas, Mexican corporate = corporativo mexicano, Sports = deportes, Price = precio, Air access = acceso aéreo, Safety perception = percepción de seguridad, Domestic = nacional, International = internacional). Los nombres de organizaciones, hoteles y destinos van tal cual.
5. Cada hallazgo y cada acción lleva al menos una cifra de los resultados.
6. Las acciones son concretas y para este mes: a quién llamar, qué revisar, qué preparar. Si hay oportunidades prioritarias que llegan en los próximos 3 meses ("starting_within_3_months" con puntaje igual o mayor al umbral), la primera acción empieza por ellas.
7. Menciona en "Notas sobre los datos" cada alerta de "data_check_issues".
8. Los datos son sintéticos: conserva la segunda línea tal como está en el formato.

Devuelve SOLO el informe en Markdown, con exactamente este formato:

# Informe de eventos de negocios · {destino} · {mes y año en español}
DATOS SINTÉTICOS. Prototipo: los hoteles, grupos y cifras son inventados.

## Tres hallazgos
1. **Frase-titular con su cifra.** Dos o tres frases de explicación con cifras.
2. **...** ...
3. **...** ...

## Tres acciones
1. **Acción en una frase.** Una o dos frases con el detalle y su cifra.
2. **...** ...
3. **...** ...

## Notas sobre los datos
- ...
"""


def _post(body, key, timeout=120):
    req = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def call_claude(user_text, model, key, post=None, retries=2):
    post = post or _post
    body = {"model": model, "max_tokens": 2000, "system": SYSTEM,
            "messages": [{"role": "user", "content": user_text}]}
    last = None
    for attempt in range(retries + 1):
        try:
            resp = post(body, key)
            text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text").strip()
            if not text:
                raise RuntimeError(f"empty response (stop_reason={resp.get('stop_reason')})")
            return text, resp.get("model", model)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            last = RuntimeError(f"HTTP {e.code}: {detail}")
            if e.code in (400, 401, 403, 404):  # bad request or key: retrying won't help
                break
        except Exception as e:  # network, timeout, empty reply
            last = e
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Claude API call failed: {last}")


def draft_brief(payload, destination, check, model=None, key=None, post=None, log=print):
    """Returns (brief_text or None, info dict). check(text) -> DataFrame with 'Found in results'."""
    model = model or os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)
    key = key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    base = (f"Destino: {destination}\nMes del informe: {payload['report_month']}\n\n"
            f"Resultados de las consultas (JSON):\n```json\n{json.dumps(payload, ensure_ascii=False, default=str, indent=1)}\n```")
    info = {"model": model, "attempts": 0, "bad_numbers": []}
    prompt = base
    for attempt in (1, 2):
        info["attempts"] = attempt
        text, used_model = call_claude(prompt, model, key, post=post)
        info["model"] = used_model
        res = check(text)
        bad = res.loc[res["Found in results"] != "Yes", "Number in brief"].tolist()
        log(f"   draft {attempt}: {len(res)} numbers, {len(bad)} not found in results {bad if bad else ''}")
        if not bad:
            info["bad_numbers"] = []
            return text, info
        info["bad_numbers"] = bad
        prompt = (base + "\n\nTu borrador anterior usó cifras que NO están en los resultados: "
                  + ", ".join(bad) + ". Probablemente las calculaste. Reescribe el informe completo usando "
                  "solo cifras que aparezcan tal cual en los resultados.")
    return None, info
