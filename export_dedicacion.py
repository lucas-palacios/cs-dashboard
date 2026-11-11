#!/usr/bin/env python3
"""
Exporta la métrica de Dedicación del Q actual a un Excel con dos hojas:
  - En scope: tickets que entraron en el cálculo
  - Fuera de scope: tickets excluidos con motivo
"""

import json, base64, urllib.request, urllib.parse
from datetime import date
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import os, sys
# Credenciales y reporters internos: se reutilizan de update.py (que lee .env)
from update import USER, TOKEN, HOST, INTERNAL_REPORTERS, QUARTERS

def _current_quarter():
    today = date.today()
    for q in QUARTERS:
        if date.fromisoformat(q["start"]) <= today <= date.fromisoformat(q["end"]):
            return q
    return QUARTERS[-1]

# Uso: python3 export_dedicacion.py [Q_ID]   (ej: Q3_2026). Por defecto, el Q actual.
_arg = sys.argv[1] if len(sys.argv) > 1 else None
QUARTER = next((q for q in QUARTERS if q["id"] == _arg), None) if _arg else _current_quarter()
if QUARTER is None:
    sys.exit(f"❌ Quarter desconocido: {_arg}. Disponibles: {[q['id'] for q in QUARTERS]}")

_creds = base64.b64encode(f"{USER}:{TOKEN}".encode()).decode()
_H = {
    "Authorization": f"Basic {_creds}",
    "Content-Type":  "application/json",
    "Accept":        "application/json",
}

# ─── Jira helpers ─────────────────────────────────────────────────────────────
def jira_search(jql, fields):
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

def worklog_hours_in_q(key, q_start, q_end):
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

# ─── Recolección de datos ──────────────────────────────────────────────────────
def collect(q):
    s, e  = q["start"], q["end"]
    flds  = ["summary", "customfield_10300", "created", "timespent",
             "reporter", "labels", "status"]

    print("  Descargando tickets creados en el Q...", end="", flush=True)
    c_iss = jira_search(
        f'project=ESD AND status=Done AND created>="{s}" AND created<="{e}"', flds
    )
    print(f" {len(c_iss)}")

    print("  Descargando tickets con worklog en el Q...", end="", flush=True)
    w_iss = jira_search(
        f'project=ESD AND status=Done AND worklogDate>="{s}" AND worklogDate<="{e}"', flds
    )
    print(f" {len(w_iss)}")

    by_key = {}
    for iss in c_iss:
        by_key[iss["key"]] = {"iss": iss, "src": "created"}
    for iss in w_iss:
        if iss["key"] not in by_key:
            by_key[iss["key"]] = {"iss": iss, "src": "worklog"}

    in_scope  = []
    out_scope = []

    total = len(by_key)
    for i, (key, entry) in enumerate(sorted(by_key.items()), 1):
        print(f"\r  Procesando {i}/{total}: {key}    ", end="", flush=True)
        f      = entry["iss"]["fields"]
        rid    = (f.get("reporter") or {}).get("accountId", "")
        rname  = (f.get("reporter") or {}).get("displayName", "—")
        summary = f.get("summary", "")
        labels  = f.get("labels", [])
        agent_time_only = "AGENT_TIME_ONLY" in labels

        if is_cloud(f):
            out_scope.append({"key": key, "summary": summary, "reporter": rname,
                               "motivo": "Cloud (tipo de request Cloud)"})
            continue
        if is_test(f):
            out_scope.append({"key": key, "summary": summary, "reporter": rname,
                               "motivo": "Test (summary contiene [TEST] o label TestAgente)"})
            continue
        if has_excluded_label(f) and not agent_time_only:
            out_scope.append({"key": key, "summary": summary, "reporter": rname,
                               "motivo": 'Label "excluded" aplicada manualmente'})
            continue
        if rid in INTERNAL_REPORTERS:
            out_scope.append({"key": key, "summary": summary, "reporter": rname,
                               "motivo": "Reporter interno (SMF / Etendo)"})
            continue

        # En scope: calcular horas
        if entry["src"] == "created":
            hrs = (f.get("timespent") or 0) / 3600
            fuente = "timespent total"
        else:
            hrs = worklog_hours_in_q(key, s, e)
            fuente = "worklogs del Q"

        in_scope.append({
            "key":      key,
            "summary":  summary,
            "reporter": rname,
            "hours":    round(hrs, 2),
            "fuente":   fuente,
            "labels":   ", ".join(labels) if labels else "—",
        })

    print()
    return in_scope, out_scope

# ─── Estilos Excel ────────────────────────────────────────────────────────────
HDR_FILL   = PatternFill("solid", fgColor="1E3A5F")
HDR_FONT   = Font(bold=True, color="FFFFFF", size=11)
ALT_FILL   = PatternFill("solid", fgColor="F0F4FA")
LINK_FONT  = Font(color="1E55A0", underline="single")
THIN       = Side(style="thin", color="CCCCCC")
BORDER     = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER     = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT       = Alignment(horizontal="left",  vertical="center", wrap_text=True)

def style_header(ws, col_widths):
    for col_idx, (header, width) in enumerate(col_widths, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font      = HDR_FONT
        cell.fill      = HDR_FILL
        cell.alignment = CENTER
        cell.border    = BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"

def write_cell(ws, row, col, value, link=None, alt=False, center=False):
    cell = ws.cell(row=row, column=col, value=value)
    cell.border    = BORDER
    cell.alignment = CENTER if center else LEFT
    if alt:
        cell.fill = ALT_FILL
    if link:
        cell.hyperlink = link
        cell.font = LINK_FONT
    return cell

# ─── Generar Excel ────────────────────────────────────────────────────────────
def build_excel(in_scope, out_scope, quarter_label, output_path):
    wb = openpyxl.Workbook()

    # ── Hoja 1: En scope ───────────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "En scope"

    cols1 = [
        ("Ticket",     14),
        ("Resumen",    55),
        ("Reporter",   22),
        ("Horas",      10),
        ("Fuente",     20),
        ("Labels",     22),
    ]
    style_header(ws1, cols1)

    in_sorted = sorted(in_scope, key=lambda x: x["hours"], reverse=True)
    for i, t in enumerate(in_sorted, 2):
        alt  = (i % 2 == 0)
        url  = f"https://etendoproject.atlassian.net/browse/{t['key']}"
        write_cell(ws1, i, 1, t["key"],     link=url, alt=alt, center=True)
        write_cell(ws1, i, 2, t["summary"],             alt=alt)
        write_cell(ws1, i, 3, t["reporter"],             alt=alt)
        write_cell(ws1, i, 4, t["hours"],                alt=alt, center=True)
        write_cell(ws1, i, 5, t["fuente"],               alt=alt, center=True)
        write_cell(ws1, i, 6, t["labels"],               alt=alt)
        ws1.row_dimensions[i].height = 18

    # Fila totales
    tr = len(in_sorted) + 2
    total_h = round(sum(t["hours"] for t in in_scope), 2)
    avg_h   = round(total_h / len(in_scope), 2) if in_scope else 0
    for col in range(1, 7):
        cell = ws1.cell(row=tr, column=col)
        cell.border    = BORDER
        cell.fill      = PatternFill("solid", fgColor="1E3A5F")
        cell.font      = Font(bold=True, color="FFFFFF")
        cell.alignment = CENTER
    ws1.cell(row=tr, column=1).value = f"TOTAL: {len(in_scope)} tickets"
    ws1.cell(row=tr, column=4).value = total_h
    ws1.cell(row=tr, column=5).value = f"Prom: {avg_h}h"

    ws1.auto_filter.ref = f"A1:F{tr - 1}"

    # ── Hoja 2: Fuera de scope ─────────────────────────────────────────────────
    ws2 = wb.create_sheet("Fuera de scope")

    cols2 = [
        ("Ticket",                 14),
        ("Resumen",                55),
        ("Reporter",               22),
        ("Motivo de exclusión",    45),
    ]
    style_header(ws2, cols2)

    MOTIVO_COLORS = {
        "Cloud":    "D6E4F0",
        "Test":     "FFF3CD",
        "Label":    "FCE4D6",
        "Reporter": "E2EFDA",
    }

    def motivo_fill(motivo):
        for k, color in MOTIVO_COLORS.items():
            if k.lower() in motivo.lower():
                return PatternFill("solid", fgColor=color)
        return None

    out_sorted = sorted(out_scope, key=lambda x: x["motivo"])
    for i, t in enumerate(out_sorted, 2):
        url  = f"https://etendoproject.atlassian.net/browse/{t['key']}"
        fill = motivo_fill(t["motivo"])
        write_cell(ws2, i, 1, t["key"],    link=url, center=True)
        write_cell(ws2, i, 2, t["summary"])
        write_cell(ws2, i, 3, t["reporter"])
        write_cell(ws2, i, 4, t["motivo"])
        if fill:
            for col in range(1, 5):
                ws2.cell(row=i, column=col).fill = fill
        ws2.row_dimensions[i].height = 18

    tr2 = len(out_sorted) + 2
    for col in range(1, 5):
        cell = ws2.cell(row=tr2, column=col)
        cell.border    = BORDER
        cell.fill      = PatternFill("solid", fgColor="1E3A5F")
        cell.font      = Font(bold=True, color="FFFFFF")
        cell.alignment = CENTER
    ws2.cell(row=tr2, column=1).value = f"TOTAL: {len(out_scope)} tickets excluidos"

    ws2.auto_filter.ref = f"A1:D{tr2 - 1}"

    wb.save(output_path)
    print(f"\n✅  Excel guardado → {output_path}")
    print(f"    Hoja 'En scope':       {len(in_scope)} tickets   (total {total_h}h, prom {avg_h}h)")
    print(f"    Hoja 'Fuera de scope': {len(out_scope)} tickets excluidos")

    # Resumen por motivo
    from collections import Counter
    motivos = Counter(t["motivo"].split(" (")[0] for t in out_scope)
    for m, n in sorted(motivos.items(), key=lambda x: -x[1]):
        print(f"      · {m}: {n}")

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    q = QUARTER
    print(f"\n📊 Exportando Dedicación — {q['label']}")
    print(f"   Rango: {q['start']} → {q['end']}\n")

    in_scope, out_scope = collect(q)
    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"dedicacion_{q['id']}.xlsx")
    build_excel(in_scope, out_scope, q["label"], output)
