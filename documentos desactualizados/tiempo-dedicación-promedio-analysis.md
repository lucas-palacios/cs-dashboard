# Tiempo de Dedicación Promedio — Etendo Service Desk (ESD)

## Qué hace este análisis

Calcula el tiempo promedio de dedicación por ticket del proyecto **ESD (Etendo Service Desk)** durante el **trimestre actual**, y lo compara contra el OKR de **≤ 4.15 horas/ticket**.

---

## Cómo ejecutarlo

Decirle a Claude:

> "Ejecuta el análisis de tiempo de dedicación promedio del trimestre actual usando el documento tiempo-dedicación-promedio-analysis.md"

Claude leerá este documento y ejecutará todo automáticamente.

---

## Lógica del análisis

### Credenciales Jira
Están en `/Users/lucaspalacios/.claude.json` bajo `mcpServers.jira`:
- **Host:** `etendoproject.atlassian.net`
- **User:** `lucas.palacios@smfconsulting.es`
- **Token:** en el archivo

### Tickets que entran en scope (dos fuentes, mergear por key)
1. Tickets con `status = Done` **creados en el trimestre actual**
2. Tickets con `status = Done` que tienen **worklog con fecha dentro del trimestre** (pueden haber sido creados antes)

```
JQL 1: project = ESD AND status = Done AND created >= "{Q_START}" AND created <= "{Q_END}"
JQL 2: project = ESD AND status = Done AND worklogDate >= "{Q_START}" AND worklogDate <= "{Q_END}"
```

> Los tickets sin worklog pero creados en el trimestre **cuentan con 0 horas** (se resolvieron sin esfuerzo).

### Tickets que NO cuentan (excluir)
1. `customfield_10300.requestType.name == "Cloud"`
2. Título (`summary`) contiene `[TEST AGENTE]`
3. Label `excluded` en el ticket
4. Status distinto de `Done`
4. Reporter es uno de los siguientes (tickets internos del equipo):
   - Juan Funes (`633af5977f85f16777a177d5` / `qm:...:de7de1b9-...`)
   - Leonardo Echenique (`63f6600afb3ac4003fa3743c` / `qm:...:d6836056-...`)
   - Lucas Palacios (`5a79ce9599b305616a1faa55` / `qm:...:f54eb844-...`)

### Cálculo de horas por ticket
- **Tickets creados en el trimestre:** usar campo `timespent` (segundos totales / 3600 = horas). Como fueron creados en el trimestre, todo su tiempo pertenece al trimestre.
- **Tickets pre-trimestre con worklog en el trimestre:** llamar a `GET /rest/api/3/issue/{key}/worklog` y sumar solo los worklogs con `started` dentro del trimestre.

### Cálculo del promedio
```
promedio = suma de horas de todos los tickets en scope / total tickets en scope
```
> El denominador incluye tickets con 0 horas.

### OKR
- **Target:** ≤ 4.15 horas/ticket
- ✅ Cumplido si promedio ≤ 4.15
- ❌ No cumplido si promedio > 4.15

---

## Resultado Q1 2026 (ejecutado el 17/03/2026)

| Métrica | Valor |
|---|---|
| Tickets creados en Q1 Done | 249 |
| Tickets pre-Q1 con worklog en Q1 Done | 101 |
| Excluidos Cloud | 140 |
| Excluidos [TEST AGENTE] | 12 |
| Excluidos reporter interno | 6 |
| **Tickets en scope** | **104** |
| Con tiempo registrado | 93 |
| Sin tiempo (0h) | 11 |
| Total horas Q1 | 343.25h |

### Resultado clave
| Métrica | Valor |
|---|---|
| **Promedio dedicación** | **3.30 h/ticket** |
| OKR target | ≤ 4.15 h/ticket |
| Margen sobre OKR | -0.85h (por debajo) |
| **Estado OKR** | **✅ CUMPLIDO** |

### Distribución de horas
| Rango | Tickets |
|---|---|
| 0h | 11 |
| 0–1h | 5 |
| 1–2h | 12 |
| 2–4h | 43 |
| 4–8h | 26 |
| >8h | 7 |

### Top 10 tickets por tiempo
| Ticket | Horas | Resumen |
|---|---|---|
| ESD-1360 | 13.50h | Problema con la visualización del registro en Ítems Relacionados |
| ESD-1485 | 11.50h | CLONE - Conexiones abiertas en BBDD relacionadas con Verifactu |
| ESD-1420 | 11.00h | Problemas al borrar un pedido |
| ESD-1370 | 9.50h | Traducción trial balance |
| ESD-1341 | 9.50h | Problemas relacionados con Cobros/Pagos tras pasar de 21.4.x a 24.4.x |
| ESD-1456 | 8.75h | Me gustaria saber en que estado está mi ticket ESD-1274 |
| ESD-1367 | 8.50h | Error al filtrar/ordenar la ventana "Cierre de año", pestaña "Contabilidad" |
| ESD-1400 | 7.75h | Error al "Seleccionar Facturas y Pedidos" desde "Remesa" |
| ESD-1554 | 6.75h | Error sii en version 4.7 |
| ESD-1385 | 6.50h | Problema al añadir cobros. Grid no carga |

---

## Notas técnicas

### Endpoint de búsqueda
Usar siempre `POST https://etendoproject.atlassian.net/rest/api/3/search/jql` (el antiguo `GET /rest/api/3/search` devuelve HTTP 410).

### Paginación de búsqueda
La respuesta incluye `isLast: bool` y `nextPageToken: str`. Iterar enviando `nextPageToken` en el body hasta que `isLast == True` o la lista venga vacía.

### Endpoint de worklogs
`GET /rest/api/3/issue/{key}/worklog` — la respuesta usa la clave **`"worklogs"`** (NO `"values"`). Paginación clásica con `startAt` en query param.

### Reporters internos excluidos (account IDs completos)
| Persona | Account ID |
|---|---|
| Juan Funes (smf) | `633af5977f85f16777a177d5` |
| Juan Funes (etendo) | `qm:cd4e9010-dcfd-49ec-8437-e747a969a347:de7de1b9-26e9-45f3-94e4-de5e60fccc63` |
| Leonardo Echenique (smf) | `63f6600afb3ac4003fa3743c` |
| Leonardo Echenique (etendo) | `qm:cd4e9010-dcfd-49ec-8437-e747a969a347:d6836056-0c71-4088-a97a-a8cfc2efa598` |
| Lucas Palacios (smf) | `5a79ce9599b305616a1faa55` |
| Lucas Palacios (etendo) | `qm:cd4e9010-dcfd-49ec-8437-e747a969a347:f54eb844-8b5e-4286-a9e8-c666f76cff07` |

---

## Script completo (Python — listo para ejecutar)

```python
import urllib.request, json, base64

TOKEN = "<leer de /Users/lucaspalacios/.claude.json → mcpServers.jira.env.JIRA_API_TOKEN>"
USER  = "lucas.palacios@smfconsulting.es"
HOST  = "etendoproject.atlassian.net"
Q_START, Q_END = "2026-01-01", "2026-03-31"   # ajustar al trimestre actual

EXCLUDED_REPORTERS = {
    "633af5977f85f16777a177d5",
    "qm:cd4e9010-dcfd-49ec-8437-e747a969a347:de7de1b9-26e9-45f3-94e4-de5e60fccc63",
    "63f6600afb3ac4003fa3743c",
    "qm:cd4e9010-dcfd-49ec-8437-e747a969a347:d6836056-0c71-4088-a97a-a8cfc2efa598",
    "5a79ce9599b305616a1faa55",
    "qm:cd4e9010-dcfd-49ec-8437-e747a969a347:f54eb844-8b5e-4286-a9e8-c666f76cff07",
}

creds = base64.b64encode(f"{USER}:{TOKEN}".encode()).decode()
headers = {
    "Authorization": f"Basic {creds}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def fetch_all(jql):
    issues, next_page_token = [], None
    while True:
        payload = {
            "jql": jql,
            "fields": ["summary", "customfield_10300", "created", "timespent", "reporter"],
            "maxResults": 100
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token
        req = urllib.request.Request(
            f"https://{HOST}/rest/api/3/search/jql",
            data=json.dumps(payload).encode(),
            headers=headers, method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            result = json.load(resp)
        batch = result.get("issues", [])
        issues.extend(batch)
        if result.get("isLast", True) or not batch:
            break
        next_page_token = result.get("nextPageToken")
    return issues

def get_worklog_hours_in_q(key):
    total_seconds, start_at = 0, 0
    while True:
        req = urllib.request.Request(
            f"https://{HOST}/rest/api/3/issue/{key}/worklog?startAt={start_at}",
            headers={"Authorization": headers["Authorization"], "Accept": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            result = json.load(resp)
        for wl in result.get("worklogs", []):  # ⚠️ clave "worklogs", NO "values"
            started = wl.get("started", "")[:10]
            if Q_START <= started <= Q_END:
                total_seconds += wl.get("timeSpentSeconds", 0)
        total   = result.get("total", 0)
        max_res = result.get("maxResults", 0)
        if start_at + max_res >= total:
            break
        start_at += max_res
    return total_seconds / 3600

# Fetch ambas fuentes y mergear por key
issues1 = fetch_all(f'project = ESD AND status = Done AND created >= "{Q_START}" AND created <= "{Q_END}"')
issues2 = fetch_all(f'project = ESD AND status = Done AND worklogDate >= "{Q_START}" AND worklogDate <= "{Q_END}"')

all_by_key = {}
for issue in issues1:
    all_by_key[issue["key"]] = {"issue": issue, "source": "created_in_q"}
for issue in issues2:
    key = issue["key"]
    if key not in all_by_key:
        all_by_key[key] = {"issue": issue, "source": "worklog_in_q"}

# Exclusiones y cálculo de horas
in_scope = []
excl_cloud = excl_test = excl_reporter = 0

for key, entry in all_by_key.items():
    issue   = entry["issue"]
    source  = entry["source"]
    fields  = issue.get("fields", {})
    summary = fields.get("summary", "")
    cf      = fields.get("customfield_10300") or {}
    req_type= cf.get("requestType", {}).get("name", "")
    reporter_id = (fields.get("reporter") or {}).get("accountId", "")

    if req_type == "Cloud":               excl_cloud    += 1; continue
    if "[TEST AGENTE]" in summary:        excl_test     += 1; continue
    if reporter_id in EXCLUDED_REPORTERS: excl_reporter += 1; continue

    if source == "created_in_q":
        hours = (fields.get("timespent") or 0) / 3600
    else:
        hours = get_worklog_hours_in_q(key)

    in_scope.append({"key": key, "summary": summary, "hours": hours})

# Métricas
from collections import Counter
total_hours  = sum(t["hours"] for t in in_scope)
avg          = total_hours / len(in_scope) if in_scope else 0
with_time    = [t for t in in_scope if t["hours"] > 0]
without_time = [t for t in in_scope if t["hours"] == 0]

dist = {"0h": 0, "0-1h": 0, "1-2h": 0, "2-4h": 0, "4-8h": 0, ">8h": 0}
for t in in_scope:
    h = t["hours"]
    if h == 0:   dist["0h"] += 1
    elif h < 1:  dist["0-1h"] += 1
    elif h < 2:  dist["1-2h"] += 1
    elif h < 4:  dist["2-4h"] += 1
    elif h < 8:  dist["4-8h"] += 1
    else:        dist[">8h"] += 1

top10 = sorted(in_scope, key=lambda t: t["hours"], reverse=True)[:10]

print(f"Total Done (pre-filtro):               {len(issues1) + len(issues2)}")
print(f"Tickets creados en Q Done:             {len(issues1)}")
print(f"Tickets pre-Q con worklog en Q Done:   {len(issues2)}")
print(f"Excluidos Cloud:                       {excl_cloud}")
print(f"Excluidos [TEST AGENTE]:               {excl_test}")
print(f"Excluidos reporter interno:            {excl_reporter}")
print(f"En scope:                              {len(in_scope)}")
print(f"Con tiempo registrado:                 {len(with_time)}")
print(f"Sin tiempo (0h):                       {len(without_time)}")
print(f"Total horas:                           {total_hours:.2f}h")
print(f"Promedio:                              {avg:.2f} h/ticket")
print(f"OKR target:                            ≤ 4.15 h/ticket")
print(f"Estado OKR:                            {'✅ CUMPLIDO' if avg <= 4.15 else '❌ NO CUMPLIDO'}")
print("\nDistribución:")
for rango, count in dist.items():
    print(f"  {rango:>6}: {count}")
print("\nTop 10 por tiempo:")
for t in top10:
    print(f"  {t['key']} | {t['hours']:.2f}h | {t['summary'][:60]}")
print("\nTickets sin tiempo (0h):")
for t in sorted(without_time, key=lambda t: t["key"]):
    print(f"  {t['key']} | {t['summary'][:65]}")
```
