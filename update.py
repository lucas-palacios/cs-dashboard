#!/usr/bin/env python3
"""
CS Dashboard Updater — Etendo Service Desk
Calcula 3 métricas por trimestre y genera dashboard.html

Uso:
  python3 update.py               → actualiza métricas y publica dashboard
  python3 update.py --analyze     → analiza tickets sin etiquetar del Q actual,
                                    los puntúa (IA o interactivo) y aplica labels

Lógica de congelado:
  - Si el trimestre ya terminó Y existe su JSON con frozen=true → se salta.
  - El trimestre actual (en curso) se recalcula siempre.
  - Al terminar un trimestre, el JSON se congela automáticamente.
"""

import json, os, sys, base64, urllib.request, urllib.parse
from datetime import date, datetime

# ─── Credenciales ─────────────────────────────────────────────────────────────
# Se leen de variables de entorno o de un archivo .env junto al script
# (ver .env.example). Nunca escribir el token en el código: el repo es público.
def _load_dotenv():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_load_dotenv()
USER  = os.environ.get("JIRA_USER", "")
TOKEN = os.environ.get("JIRA_TOKEN", "")
HOST  = os.environ.get("JIRA_HOST", "etendoproject.atlassian.net")
if not USER or not TOKEN:
    sys.exit("❌ Faltan JIRA_USER / JIRA_TOKEN. Copiá .env.example a .env y completalo.")

OKR_DEDICACION = 1.7
OKR_CHATBOT    = 50.0

AI_BOT_ID = "712020:59b62909-e418-4125-8447-1a1e76f88ec0"  # "Information Etendo"

# Emails excluidos del SLO (CS interno que no debe computar como carga externa)
SLO_EXCLUDED_EMAILS = {
    "lucas.palacios@smfconsulting.es",
    "juan.funes@smfconsulting.es",
}

# Account IDs de reporters internos excluidos en Dedicación
INTERNAL_REPORTERS = {
    "633af5977f85f16777a177d5",
    "qm:cd4e9010-dcfd-49ec-8437-e747a969a347:de7de1b9-26e9-45f3-94e4-de5e60fccc63",
    "63f6600afb3ac4003fa3743c",
    "qm:cd4e9010-dcfd-49ec-8437-e747a969a347:d6836056-0c71-4088-a97a-a8cfc2efa598",
    "5a79ce9599b305616a1faa55",
    "qm:cd4e9010-dcfd-49ec-8437-e747a969a347:f54eb844-8b5e-4286-a9e8-c666f76cff07",
}

# ─── Configuración de trimestres ──────────────────────────────────────────────
# Para añadir un nuevo quarter: agregar una entrada a esta lista.
# chatbot_manual_exclude: tickets excluidos manualmente de la métrica chatbot.
QUARTERS = [
    {
        "id":    "Q1_2026",
        "label": "Q1 2026",
        "start": "2026-01-01",
        "end":   "2026-03-31",
        "chatbot_manual_exclude": [],
    },
    {
        "id":    "Q2_2026",
        "label": "Q2 2026",
        "start": "2026-04-01",
        "end":   "2026-06-30",
        "chatbot_manual_exclude": ["ESD-1722", "ESD-1717", "ESD-1721"],
    },
    {
        "id":    "Q3_2026",
        "label": "Q3 2026",
        "start": "2026-07-01",
        "end":   "2026-09-30",
        "chatbot_manual_exclude": [],
    },
    {
        "id":    "Q4_2026",
        "label": "Q4 2026",
        "start": "2026-10-01",
        "end":   "2026-12-31",
        "chatbot_manual_exclude": [],
    },
]

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data")
DASH_FILE = os.path.join(BASE_DIR, "index.html")

# ─── Jira API ─────────────────────────────────────────────────────────────────
_creds = base64.b64encode(f"{USER}:{TOKEN}".encode()).decode()
_H = {
    "Authorization": f"Basic {_creds}",
    "Content-Type":  "application/json",
    "Accept":        "application/json",
}

def jira_search(jql, fields):
    """Pagina y devuelve todos los issues de una búsqueda JQL."""
    issues, tok = [], None
    while True:
        payload = {"jql": jql, "fields": fields, "maxResults": 100}
        if tok:
            payload["nextPageToken"] = tok
        req = urllib.request.Request(
            f"https://{HOST}/rest/api/3/search/jql",
            data=json.dumps(payload).encode(), headers=_H, method="POST"
        )
        with urllib.request.urlopen(req) as r:
            res = json.load(r)
        batch = res.get("issues", [])
        issues.extend(batch)
        if res.get("isLast", True) or not batch:
            break
        tok = res.get("nextPageToken")
    return issues

_account_type_cache = {}

def get_account_type(account_id):
    if account_id in _account_type_cache:
        return _account_type_cache[account_id]
    try:
        req = urllib.request.Request(
            f"https://{HOST}/rest/api/3/user?accountId={urllib.parse.quote(account_id)}",
            headers={"Authorization": _H["Authorization"], "Accept": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            t = json.load(r).get("accountType", "unknown")
    except Exception:
        t = "unknown"
    _account_type_cache[account_id] = t
    return t

def is_cs_agent_comment(author):
    aid = author.get("accountId", "")
    if aid == AI_BOT_ID:
        return False
    if aid.startswith("qm:"):
        return False
    return get_account_type(aid) == "atlassian"

def get_all_comments(key):
    comments, start_at = [], 0
    while True:
        req = urllib.request.Request(
            f"https://{HOST}/rest/api/3/issue/{key}/comment?startAt={start_at}&maxResults=100",
            headers={"Authorization": _H["Authorization"], "Accept": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            res = json.load(r)
        batch = res.get("comments", [])
        comments.extend(batch)
        start_at += len(batch)
        if start_at >= res.get("total", 0) or not batch:
            break
    return comments

def worklog_hours_in_q(key, q_start, q_end):
    """Suma las horas de worklogs de un ticket que caen dentro del trimestre."""
    total, start_at = 0, 0
    while True:
        req = urllib.request.Request(
            f"https://{HOST}/rest/api/3/issue/{key}/worklog?startAt={start_at}",
            headers={"Authorization": _H["Authorization"], "Accept": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            res = json.load(r)
        for wl in res.get("worklogs", []):
            if q_start <= wl.get("started", "")[:10] <= q_end:
                total += wl.get("timeSpentSeconds", 0)
        total_wl = res.get("total", 0)
        start_at += res.get("maxResults", 20)
        if start_at >= total_wl:
            break
    return total / 3600

def is_cloud(f):
    cf = f.get("customfield_10300") or {}
    return (cf.get("requestType") or {}).get("name", "") == "Cloud"

def is_test(f):
    s = f.get("summary", "")
    return "[TEST]" in s or "[TEST AGENTE]" in s or "TestAgente" in f.get("labels", [])

def has_excluded_label(f):
    return "excluded" in f.get("labels", [])

# ─── Métrica 1: SLO de tiempo de resolución ───────────────────────────────────
def calc_slo(q):
    """
    Busca desde 2 meses antes del inicio del Q, más los tickets resueltos dentro
    del Q sin importar cuándo se crearon (para atribuir al Q de CIERRE, no al de
    apertura, cuando un ticket cruza el límite de trimestre).
    En scope:
      - Tickets creados en el Q y aún no resueltos (cuentan como abiertos en su Q de origen).
      - Tickets resueltos (Done) dentro del Q, sin importar cuándo se crearon.
      - Tickets anteriores cuyo SLO venció dentro del Q (breach por fecha de vencimiento,
        independientemente de cuándo se cierren finalmente).
    Excluye: Cloud, TEST AGENTE, reporters internos (etendo.software / smfconsulting).
    """
    q0 = date.fromisoformat(q["start"])
    q1 = date.fromisoformat(q["end"])
    m = q0.month - 2
    search_from = date(q0.year if m > 0 else q0.year - 1, m if m > 0 else m + 12, 1)

    flds = ["summary", "status", "reporter", "customfield_12095", "customfield_10300",
            "created", "labels", "resolutiondate"]

    created_pool = jira_search(
        f'project = ESD AND created >= "{search_from}" ORDER BY created ASC', flds
    )
    resolved_pool = jira_search(
        f'project = ESD AND status = Done AND resolutiondate >= "{q0}" AND resolutiondate <= "{q1}"', flds
    )

    by_key = {i["key"]: i for i in created_pool}
    for i in resolved_pool:
        by_key.setdefault(i["key"], i)

    excl = {"cloud": 0, "test": 0, "internal": 0, "excluded_tag": 0}
    scope = []

    for iss in by_key.values():
        f = iss["fields"]
        email = (f.get("reporter") or {}).get("emailAddress", "")
        if is_cloud(f):              excl["cloud"]        += 1; continue
        if is_test(f):               excl["test"]         += 1; continue
        if has_excluded_label(f):    excl["excluded_tag"] += 1; continue
        if email in SLO_EXCLUDED_EMAILS:
            excl["internal"] += 1; continue

        created = date.fromisoformat(f.get("created", "")[:10])
        slo_str = f.get("customfield_12095")
        slo_dt  = date.fromisoformat(slo_str[:10]) if slo_str else None
        status  = (f.get("status") or {}).get("name", "")
        res_str = f.get("resolutiondate")
        res_dt  = date.fromisoformat(res_str[:10]) if res_str else None

        # Un ticket cuyo SLO venció antes del inicio del Q ya quedó atribuido a un Q
        # anterior (por pre_breach de ese Q). No debe recontarse aquí solo porque se
        # haya cerrado (Done) dentro de este Q — eso duplicaría el vencido en dos Qs.
        already_breached_before_q = slo_dt is not None and slo_dt < q0

        resolved_in_q   = (status == "Done" and res_dt is not None and q0 <= res_dt <= q1
                            and not already_breached_before_q)
        still_open_in_q = status != "Done" and q0 <= created <= q1
        pre_breach      = created < q0 and slo_dt and q0 <= slo_dt <= q1

        if resolved_in_q or still_open_in_q or pre_breach:
            scope.append({"breached": slo_dt is not None, "done": status == "Done"})

    breached = sum(1 for t in scope if t["breached"])
    met      = sum(1 for t in scope if not t["breached"] and t["done"])
    open_t   = sum(1 for t in scope if not t["breached"] and not t["done"])
    closed   = breached + met
    rate     = breached / closed * 100 if closed else 0.0

    return {
        "consulted_from": str(search_from),
        "excluded":   excl,
        "in_scope":   len(scope),
        "closed":     closed,
        "open":       open_t,
        "breached":   breached,
        "met":        met,
        "breach_rate":  round(rate, 1),
        "compliance":   round(100 - rate, 1),
    }

# ─── Métrica 2: Tiempo de dedicación promedio ─────────────────────────────────
def calc_dedicacion(q):
    """
    Fuente 1: tickets Done creados en el Q (usan timespent total).
    Fuente 2: tickets Done con worklog en el Q (usan solo horas del Q).
    Excluye: Cloud, TEST AGENTE, reporters internos (por account ID).
    OKR: ≤ OKR_DEDICACION h/ticket.
    """
    s, e  = q["start"], q["end"]
    flds  = ["summary", "customfield_10300", "created", "timespent", "reporter", "labels"]
    c_iss = jira_search(f'project=ESD AND status=Done AND created>="{s}" AND created<="{e}"', flds)
    w_iss = jira_search(f'project=ESD AND status=Done AND worklogDate>="{s}" AND worklogDate<="{e}"', flds)

    by_key = {}
    for iss in c_iss: by_key[iss["key"]] = {"iss": iss, "src": "created"}
    for iss in w_iss:
        if iss["key"] not in by_key:
            by_key[iss["key"]] = {"iss": iss, "src": "worklog"}

    excl  = {"cloud": 0, "test": 0, "internal": 0, "excluded_tag": 0}
    scope = []

    for key, entry in by_key.items():
        f   = entry["iss"]["fields"]
        rid = (f.get("reporter") or {}).get("accountId", "")
        agent_time_only = "AGENT_TIME_ONLY" in f.get("labels", [])
        if is_cloud(f):                                    excl["cloud"]        += 1; continue
        if is_test(f):                                     excl["test"]         += 1; continue
        if has_excluded_label(f) and not agent_time_only: excl["excluded_tag"] += 1; continue
        if rid in INTERNAL_REPORTERS:                      excl["internal"]     += 1; continue
        hrs = (f.get("timespent") or 0) / 3600 if entry["src"] == "created" \
              else worklog_hours_in_q(key, s, e)
        scope.append({"key": key, "hours": round(hrs, 2)})

    total = sum(t["hours"] for t in scope)
    avg   = total / len(scope) if scope else 0
    dist  = {"0h": 0, "0-1h": 0, "1-2h": 0, "2-4h": 0, "4-8h": 0, ">8h": 0}
    for t in scope:
        h = t["hours"]
        if   h == 0: dist["0h"]   += 1
        elif h <  1: dist["0-1h"] += 1
        elif h <  2: dist["1-2h"] += 1
        elif h <  4: dist["2-4h"] += 1
        elif h <  8: dist["4-8h"] += 1
        else:        dist[">8h"]  += 1
    top10 = sorted(scope, key=lambda t: t["hours"], reverse=True)[:10]

    return {
        "excluded":     excl,
        "in_scope":     len(scope),
        "with_time":    sum(1 for t in scope if t["hours"] > 0),
        "without_time": sum(1 for t in scope if t["hours"] == 0),
        "total_hours":  round(total, 2),
        "avg_hours":    round(avg, 2),
        "okr_target":   OKR_DEDICACION,
        "okr_met":      avg <= OKR_DEDICACION,
        "dist":         dist,
        "top10":        top10,
    }

# ─── Métrica 3: Chatbot IA ────────────────────────────────────────────────────
def calc_chatbot(q):
    """
    Tickets creados en el Q que estén Done, más los no cerrados que ya tengan
    etiqueta IA (1-5).
    Excluye: Cloud, TEST AGENTE, AGENT_TIME_ONLY, exclusiones manuales del quarter.
    NO excluye por reporter (a diferencia de SLO).
    Etiqueta IA: label numérico 1-5. Ayudó = 4 ó 5.
    """
    s, e      = q["start"], q["end"]
    excl_keys = set(q.get("chatbot_manual_exclude", []))
    issues    = jira_search(
        f'project=ESD AND created>="{s}" AND created<="{e}" '
        f'AND (status=Done OR labels in ("1","2","3","4","5"))',
        ["summary", "labels", "customfield_10300"]
    )

    excl  = {"cloud": 0, "test": 0, "excluded_tag": 0, "manual": len(excl_keys)}
    scope = []

    for iss in issues:
        if iss["key"] in excl_keys: continue
        f = iss["fields"]
        if is_cloud(f):                                      excl["cloud"]        += 1; continue
        if is_test(f):                                       excl["test"]         += 1; continue
        if has_excluded_label(f):                            excl["excluded_tag"] += 1; continue
        if "AGENT_TIME_ONLY" in f.get("labels", []):        excl["excluded_tag"] += 1; continue
        ai  = [l for l in f.get("labels", []) if l in ["1","2","3","4","5"]]
        score = max(ai, key=int) if ai else None
        scope.append({"key": iss["key"], "score": score, "summary": f.get("summary", "")})

    labeled    = [t for t in scope if t["score"]]
    unlabeled_list = [{"key": t["key"], "summary": t["summary"]} for t in scope if not t["score"]]
    helped     = [t for t in labeled if t["score"] in ["4","5"]]
    avg_score  = sum(int(t["score"]) for t in labeled) / len(labeled) if labeled else 0
    score_dist = {s: sum(1 for t in labeled if t["score"] == s) for s in ["1","2","3","4","5"]}
    pct_total  = len(helped) / len(scope)   * 100 if scope   else 0
    pct_labeled= len(helped) / len(labeled) * 100 if labeled else 0

    # Tickets resueltos solo por IA: hay comentario del bot y ningún agente CS comentó
    solo_resolved = []
    for t in scope:
        comments = get_all_comments(t["key"])
        has_ai    = any(c["author"].get("accountId") == AI_BOT_ID for c in comments)
        has_human = any(is_cs_agent_comment(c["author"]) for c in comments)
        if has_ai and not has_human:
            solo_resolved.append(t["key"])

    return {
        "excluded":       excl,
        "in_scope":       len(scope),
        "labeled":        len(labeled),
        "unlabeled":      len(unlabeled_list),
        "unlabeled_keys": unlabeled_list,
        "helped":         len(helped),
        "not_helped":     len(labeled) - len(helped),
        "pct_total":      round(pct_total, 1),
        "pct_labeled":    round(pct_labeled, 1),
        "avg_score":      round(avg_score, 2),
        "score_dist":     score_dist,
        "solo_resolved":  solo_resolved,
        "okr_target":     OKR_CHATBOT,
        "okr_met":        pct_total >= OKR_CHATBOT,
    }

# ─── Generador HTML ───────────────────────────────────────────────────────────
def gen_html(quarters):
    qs = sorted(quarters, key=lambda q: q["start"], reverse=True)
    current_id = qs[0]["id"]

    cards = ""
    rows  = ""

    for q in qs:
        slo = q["slo"]
        ded = q["dedicacion"]
        bot = q["chatbot"]
        cur = q["id"] == current_id
        slo_ok  = slo["compliance"] >= 99
        ded_ok  = ded["okr_met"]
        bot_okr = bot.get("okr_target", OKR_CHATBOT)
        bot_ok  = bot.get("okr_met", bot["pct_total"] >= bot_okr)

        unlabeled_keys = bot.get("unlabeled_keys", [])
        if unlabeled_keys:
            badges = "".join(
                f'<a class="unlabeled-badge" href="https://etendoproject.atlassian.net/browse/{t["key"]}" '
                f'target="_blank" rel="noopener" title="{t["summary"][:80]}">{t["key"]}</a>'
                for t in unlabeled_keys
            )
            unlabeled_warn = f' <span class="warn">⚠ {len(unlabeled_keys)} sin etiquetar: {badges}</span>'
        else:
            unlabeled_warn = ""

        solo_keys = bot.get("solo_resolved", [])
        solo_badges = "".join(
            f'<a class="solo-badge" href="https://etendoproject.atlassian.net/browse/{k}" '
            f'target="_blank" rel="noopener">{k}</a>'
            for k in solo_keys
        )
        solo_section = f"""
      <div class="solo-block">
        <div class="solo-title">🤖 Sin intervención humana &nbsp;<span class="solo-count">{len(solo_keys)}</span></div>
        <div class="solo-list">{solo_badges if solo_badges else '<span class="mdet">ninguno registrado aún</span>'}</div>
      </div>""" if True else ""

        cards += f"""
  <div class="card{'  card-current' if cur else ''}">
    <div class="card-header">
      <span class="qlabel">{q['label']}</span>
      {'<span class="ctag">ACTUAL</span>' if cur else '<span class="ftag">CERRADO</span>'}
      <span class="upd">actualizado: {q['last_updated']}</span>
    </div>
    <div class="metrics">
      <div class="metric">
        <div class="mtitle">⏱ SLO Resolución</div>
        <div class="mvalue {'green' if slo_ok else 'red'}">{slo['compliance']}%</div>
        <div class="msub">cumplimiento · {'✅ Sin vencimientos' if slo['breached']==0 else f'❌ {slo["breached"]} vencidos'}</div>
        <div class="mdet">{slo['closed']} cerrados · {slo['open']} abiertos · {slo['in_scope']} en scope</div>
      </div>
      <div class="metric">
        <div class="mtitle">🕐 Dedicación Promedio</div>
        <div class="mvalue {'green' if ded_ok else 'red'}">{ded['avg_hours']}h</div>
        <div class="msub">por ticket · {'✅' if ded_ok else '❌'} OKR ≤ {ded['okr_target']}h</div>
        <div class="mdet">{ded['in_scope']} tickets · {ded['total_hours']}h total</div>
      </div>
      <div class="metric">
        <div class="mtitle">🤖 Chatbot IA</div>
        <div class="mvalue {'green' if bot_ok else 'red'}">{bot['pct_total']}%</div>
        <div class="msub">tickets donde ayudó · {'✅' if bot_ok else '❌'} OKR ≥ {bot_okr}%</div>
        <div class="mdet">{bot['helped']}/{bot['in_scope']} tickets · score {bot['avg_score']}/5{unlabeled_warn}</div>
      </div>
    </div>{solo_section}
  </div>"""

        rows += f"""
  <tr {'class="rcur"' if cur else ''}>
    <td><strong>{q['label']}</strong>{'<br><small class="ctag-sm">ACTUAL</small>' if cur else ''}</td>
    <td class="{'ok' if slo_ok else 'fail'}">{slo['compliance']}%<br>
      <small>{slo['breached']} vencidos / {slo['closed']} cerrados</small></td>
    <td class="{'ok' if ded_ok else 'fail'}">{ded['avg_hours']}h<br>
      <small>{'✅' if ded_ok else '❌'} OKR {ded['okr_target']}h &nbsp;·&nbsp; {ded['total_hours']}h total</small></td>
    <td class="{'ok' if bot_ok else 'fail'}">{bot['pct_total']}%<br>
      <small>{'✅' if bot_ok else '❌'} OKR {bot_okr}% &nbsp;·&nbsp; {bot['helped']}/{bot['in_scope']} &nbsp;·&nbsp; avg {bot['avg_score']}/5</small></td>
  </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CS Dashboard — Etendo Service Desk</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: #0f172a; color: #e2e8f0; padding: 36px 28px; min-height: 100vh; }}
  h1  {{ font-size: 1.55rem; font-weight: 700; color: #f8fafc; margin-bottom: 4px; }}
  .sub {{ color: #64748b; font-size: .85rem; margin-bottom: 32px; }}

  /* ── Cards ── */
  .card {{ background: #1e293b; border-radius: 14px; padding: 24px;
           margin-bottom: 22px; border: 1px solid #334155; }}
  .card-current {{ border-color: #6366f1; box-shadow: 0 0 0 1px #6366f133; }}
  .card-header {{ display: flex; align-items: center; gap: 10px;
                  margin-bottom: 20px; flex-wrap: wrap; }}
  .qlabel  {{ font-size: 1.18rem; font-weight: 700; color: #f1f5f9; }}
  .ctag    {{ background: #6366f1; color: #fff; font-size: .68rem; font-weight: 700;
              padding: 2px 9px; border-radius: 999px; letter-spacing: .05em; }}
  .ftag    {{ background: #334155; color: #94a3b8; font-size: .68rem; font-weight: 600;
              padding: 2px 9px; border-radius: 999px; letter-spacing: .05em; }}
  .ctag-sm {{ color: #818cf8; font-size: .75rem; }}
  .upd     {{ margin-left: auto; color: #475569; font-size: .78rem; }}

  /* ── Metric cells ── */
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px,1fr)); gap: 14px; }}
  .metric  {{ background: #0f172a; border-radius: 10px; padding: 16px; border: 1px solid #1e293b; }}
  .mtitle  {{ font-size: .72rem; color: #64748b; font-weight: 600;
              text-transform: uppercase; letter-spacing: .06em; margin-bottom: 9px; }}
  .mvalue  {{ font-size: 2.1rem; font-weight: 800; line-height: 1; margin-bottom: 6px; color: #f1f5f9; }}
  .mvalue.green {{ color: #4ade80; }}
  .mvalue.red   {{ color: #f87171; }}
  .msub  {{ font-size: .78rem; color: #94a3b8; margin-bottom: 4px; }}
  .mdet  {{ font-size: .73rem; color: #475569; }}
  .warn  {{ color: #fbbf24; }}

  /* ── Historical table ── */
  .stitle {{ font-size: .82rem; font-weight: 700; color: #475569;
             text-transform: uppercase; letter-spacing: .08em; margin: 32px 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; background: #1e293b;
           border-radius: 14px; overflow: hidden; border: 1px solid #334155; }}
  th    {{ background: #0f172a; padding: 12px 16px; text-align: left;
           font-size: .74rem; color: #64748b; text-transform: uppercase; letter-spacing: .05em; }}
  td    {{ padding: 14px 16px; font-size: .88rem; border-top: 1px solid #334155;
           vertical-align: top; line-height: 1.5; }}
  td small {{ color: #64748b; font-size: .76rem; }}
  .rcur td {{ background: #1c1d3e; }}
  .ok   {{ color: #4ade80; font-weight: 600; }}
  .fail {{ color: #f87171; font-weight: 600; }}

  /* ── Solo-resolved block ── */
  .solo-block {{ margin-top: 16px; padding: 14px 16px;
                background: #0f172a; border-radius: 10px;
                border: 1px solid #1e3a5f; }}
  .solo-title {{ font-size: .72rem; color: #64748b; font-weight: 600;
                text-transform: uppercase; letter-spacing: .06em;
                margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }}
  .solo-count {{ background: #1d4ed8; color: #bfdbfe; font-size: .7rem;
                font-weight: 700; padding: 1px 8px; border-radius: 999px; }}
  .solo-list  {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .solo-badge {{ background: #1e3a5f; color: #93c5fd; font-size: .76rem;
                font-weight: 600; padding: 3px 10px; border-radius: 6px;
                text-decoration: none; border: 1px solid #1d4ed8;
                transition: background .15s; }}
  .solo-badge:hover {{ background: #1d4ed8; color: #fff; }}

  /* ── Unlabeled badges ── */
  .unlabeled-badge {{ background: #451a03; color: #fbbf24; font-size: .72rem;
                font-weight: 600; padding: 1px 7px; border-radius: 5px;
                text-decoration: none; border: 1px solid #92400e;
                margin-left: 3px; transition: background .15s; white-space: nowrap; }}
  .unlabeled-badge:hover {{ background: #92400e; color: #fff; }}
</style>
</head>
<body>
<h1>CS Dashboard — Etendo Service Desk</h1>
<p class="sub">Métricas de soporte por trimestre &nbsp;·&nbsp; generado el {date.today().isoformat()}</p>
{cards}
<div class="stitle">Histórico por trimestre</div>
<table>
  <thead>
    <tr>
      <th>Quarter</th>
      <th>⏱ SLO Resolución</th>
      <th>🕐 Dedicación Prom.</th>
      <th>🤖 Chatbot IA</th>
    </tr>
  </thead>
  <tbody>{rows}
  </tbody>
</table>
</body>
</html>"""

    with open(DASH_FILE, "w", encoding="utf-8") as f:
        f.write(html)

# ─── Análisis de tickets sin etiquetar ───────────────────────────────────────

def adf_to_text(node):
    """Convierte un nodo ADF (Atlassian Document Format) a texto plano."""
    if not node:
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = [adf_to_text(c) for c in node.get("content", [])]
    sep = "\n" if node.get("type") in ("paragraph", "bulletList", "listItem", "heading", "blockquote") else ""
    return sep.join(p for p in parts if p)

def fetch_comments_for_analysis(key):
    """Devuelve lista de {author, is_ai, text} para un ticket."""
    comments, start_at = [], 0
    while True:
        req = urllib.request.Request(
            f"https://{HOST}/rest/api/3/issue/{key}/comment?startAt={start_at}&maxResults=100",
            headers={"Authorization": _H["Authorization"], "Accept": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            res = json.load(r)
        for c in res.get("comments", []):
            aid   = c["author"].get("accountId", "")
            is_ai = aid == AI_BOT_ID
            text  = adf_to_text(c.get("body", {})).strip()
            if text:
                comments.append({
                    "author": "🤖 IA (ValerIA)" if is_ai else c["author"].get("displayName", "?"),
                    "is_ai":  is_ai,
                    "text":   text[:800],
                })
        start_at += len(res.get("comments", []))
        if start_at >= res.get("total", 0):
            break
    return comments

def apply_label(key, score, existing_labels):
    """Añade la etiqueta numérica al ticket, eliminando cualquier score previo."""
    new_labels = [l for l in existing_labels if l not in ["1","2","3","4","5"]] + [str(score)]
    payload = json.dumps({"fields": {"labels": new_labels}}).encode()
    req = urllib.request.Request(
        f"https://{HOST}/rest/api/3/issue/{key}",
        data=payload, headers=_H, method="PUT"
    )
    with urllib.request.urlopen(req) as r:
        r.read()
    return new_labels

def score_with_claude(key, summary, comments):
    """Llama a la API de Claude para puntuar la contribución de la IA (1-5)."""
    import anthropic
    conversation = "\n\n".join(
        f"[{c['author']}]\n{c['text']}" for c in comments
    ) or "(sin comentarios)"

    prompt = f"""Eres evaluador de calidad de un chatbot de soporte técnico llamado ValerIA.
Analiza la conversación del ticket de soporte y puntúa del 1 al 5 cuánto contribuyó la IA a resolver el problema.

Criterios:
5 — La IA resolvió el ticket sola, sin necesidad de intervención humana.
4 — La IA dio una respuesta concreta y útil que el agente humano solo confirmó/cerró.
3 — La IA ayudó parcialmente: acotó el problema o dio contexto útil, pero el humano hizo la resolución principal.
2 — La IA apenas ayudó: hizo preguntas genéricas o dio información básica, el humano resolvió todo.
1 — La IA no ayudó o fue irrelevante para la resolución.

Ticket: {key}
Asunto: {summary}

Conversación:
{conversation}

Responde ÚNICAMENTE con el número (1, 2, 3, 4 o 5) seguido de una justificación de una sola línea.
Formato exacto:  SCORE: <número> — <justificación>"""

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # extraer el número
    import re
    m = re.search(r"SCORE:\s*([1-5])", text)
    score = int(m.group(1)) if m else None
    justification = text.split("—", 1)[-1].strip() if "—" in text else text
    return score, justification

def analyze_unlabeled(dry_run=False):
    """Busca tickets sin etiquetar en el Q actual, los puntúa y aplica labels."""
    # Identificar el Q actual (no frozen)
    today = date.today()
    current_q = next(
        (q for q in QUARTERS if date.fromisoformat(q["start"]) <= today <= date.fromisoformat(q["end"])),
        QUARTERS[-1]
    )
    q = current_q
    s, e = q["start"], q["end"]
    excl_keys = set(q.get("chatbot_manual_exclude", []))

    print(f"\n🔍 Buscando tickets sin etiquetar en {q['label']}...")

    issues = jira_search(
        f'project=ESD AND created>="{s}" AND created<="{e}" AND status=Done',
        ["summary", "labels", "customfield_10300"]
    )

    unlabeled = []
    for iss in issues:
        if iss["key"] in excl_keys:
            continue
        f = iss["fields"]
        if is_cloud(f) or is_test(f) or has_excluded_label(f):
            continue
        if not any(l in ["1","2","3","4","5"] for l in f.get("labels", [])):
            unlabeled.append({
                "key":     iss["key"],
                "summary": f.get("summary", ""),
                "labels":  f.get("labels", []),
            })

    if not unlabeled:
        print("   ✅ No hay tickets sin etiquetar.")
        return

    print(f"   ⚠️  {len(unlabeled)} ticket(s) sin etiquetar:\n")

    use_ai = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if use_ai:
        print("   🤖 Modo automático (Claude API)\n")
    else:
        print("   ✏️  Modo interactivo — no se encontró ANTHROPIC_API_KEY\n")

    results = []
    for t in unlabeled:
        key     = t["key"]
        summary = t["summary"]
        comments = fetch_comments_for_analysis(key)

        print(f"  {'─'*60}")
        print(f"  [{key}] {summary[:70]}")

        if use_ai:
            score, justification = score_with_claude(key, summary, comments)
            if score is None:
                print("   ⚠️  No se pudo extraer score, se omite.")
                continue
            print(f"   → Score IA: {score}/5 — {justification}")
        else:
            # Mostrar comentarios y pedir score manual
            for c in comments:
                print(f"\n     [{c['author']}]")
                print(f"     {c['text'][:400]}")
            print()
            while True:
                raw = input(f"  Puntuación para {key} [1-5] (Enter para omitir): ").strip()
                if raw == "":
                    score = None
                    break
                if raw in ("1","2","3","4","5"):
                    score = int(raw)
                    break
                print("  Introduce un número del 1 al 5.")
            if score is None:
                print("   ↷ Omitido")
                continue

        results.append({"key": key, "score": score, "labels": t["labels"]})

    if not results:
        print("\n  Sin cambios que aplicar.")
        return

    print(f"\n{'─'*60}")
    print(f"  Resumen de etiquetas a aplicar:")
    for r in results:
        print(f"    {r['key']}  →  {r['score']}/5")

    if dry_run:
        print("\n  [--dry-run] No se aplicaron cambios en Jira.")
        return

    print()
    for r in results:
        new_labels = apply_label(r["key"], r["score"], r["labels"])
        print(f"   ✅ {r['key']}  etiquetado con '{r['score']}'  (labels: {new_labels})")

    print(f"\n🏁 {len(results)} ticket(s) etiquetados. Ejecuta update.py para recalcular el dashboard.")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    today     = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_data  = []

    for q in QUARTERS:
        path     = os.path.join(DATA_DIR, f"{q['id']}.json")
        existing = None
        if os.path.exists(path):
            with open(path) as f:
                existing = json.load(f)

        # Si está frozen y el JSON ya existe → usar datos guardados
        if existing and existing.get("frozen"):
            print(f"⏭  {q['label']} — frozen, usando datos guardados")
            all_data.append(existing)
            continue

        print(f"\n🔄  {q['label']} — calculando...")
        print("   → SLO...",       end="", flush=True)
        slo = calc_slo(q);          print(" ok")
        print("   → Dedicación...", end="", flush=True)
        ded = calc_dedicacion(q);   print(" ok")
        print("   → Chatbot...",    end="", flush=True)
        bot = calc_chatbot(q);      print(" ok")

        # Congelar si el trimestre ya terminó. Los tickets que se abrieron en este Q
        # y se resuelven en un Q posterior ya NO se pierden: las 3 métricas atribuyen
        # cada ticket al Q de RESOLUCIÓN (no al de creación), así que el Q siguiente
        # los recoge automáticamente al recalcularse.
        frozen = date.today() > date.fromisoformat(q["end"])

        data = {
            "id":           q["id"],
            "label":        q["label"],
            "start":        q["start"],
            "end":          q["end"],
            "frozen":       frozen,
            "last_updated": today,
            "slo":          slo,
            "dedicacion":   ded,
            "chatbot":      bot,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Guardado → {path}")
        all_data.append(data)

    gen_html(all_data)
    print(f"\n📊 Dashboard generado → {DASH_FILE}")
    push_to_github()

def push_to_github():
    import subprocess

    def run(cmd):
        r = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    print("\n🚀 Publicando en GitHub Pages...")

    _, out = run(["git", "add", "index.html"])

    code, out = run(["git", "commit", "-m", f"Dashboard update {date.today().isoformat()}"])
    if code != 0 and "nothing to commit" in out:
        print("   ℹ️  Sin cambios respecto al último push")
        return
    if code != 0:
        print(f"   ⚠️  git commit falló: {out.strip()}")
        return

    code, out = run(["git", "push"])
    if code != 0:
        print(f"   ⚠️  git push falló: {out.strip()}")
        return

    print("   ✅ Publicado correctamente")

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--analyze" in args:
        analyze_unlabeled(dry_run="--dry-run" in args)
    else:
        main()
