# Métrica Chatbot IA — Etendo Service Desk (ESD)

## Qué hace este análisis

Calcula el porcentaje de tickets del proyecto **ESD (Etendo Service Desk)** en los que el bot de IA ayudó a resolver el ticket durante el **trimestre actual**.

---

## Cómo ejecutarlo

Decirle a Claude:

> "Ejecuta el análisis del chatbot IA del trimestre actual usando el documento chatbot-soporte-metrica-analysis.md"

Claude leerá este documento y ejecutará todo automáticamente.

---

## Lógica del análisis

### Credenciales Jira
Están en `/Users/lucaspalacios/.claude.json` bajo `mcpServers.jira`:
- **Host:** `etendoproject.atlassian.net`
- **User:** `lucas.palacios@smfconsulting.es`
- **Token:** en el archivo

### Ventana de búsqueda
- Solo tickets **creados dentro del trimestre actual**.
- Ejemplo: para Q1 2026, buscar `created >= "2026-01-01" AND created <= "2026-03-31"`.

### Campo clave: `labels`
El bot de IA pone una etiqueta numérica del 1 al 5 en cada ticket:
- **1** → no ayudó nada
- **5** → resolvió el ticket completamente
- Sin etiqueta → el bot no interactuó o no fue evaluado

**La IA "ayudó" cuando la etiqueta es `4` o `5`.**

### Tickets que NO cuentan (excluir)
1. `customfield_10300.requestType.name == "Cloud"`
2. Título (`summary`) contiene `[TEST AGENTE]`
3. Label `excluded` en el ticket
4. Status distinto de `Done` (solo tickets cerrados)

> ⚠️ A diferencia del análisis SLO, **no se excluye por email del reporter**.

### Cálculo
```
% ayudó (sobre total)     = tickets con etiqueta 4 ó 5 / total en scope × 100
% ayudó (sobre etiquetados) = tickets con etiqueta 4 ó 5 / tickets con etiqueta × 100
promedio = suma de etiquetas / cantidad de tickets etiquetados
```

---

## Resultado Q1 2026 (ejecutado el 26/03/2026)

| Métrica | Valor |
|---|---|
| Tickets Done en Q1 2026 (pre-filtro) | 269 |
| Excluidos Cloud | 141 |
| Excluidos [TEST AGENTE] | 12 |
| **Tickets en scope** | **116** |
| Con etiqueta IA (1–5) | 19 |
| Sin etiqueta IA | 97 |

### Distribución de etiquetas
| Etiqueta | Tickets |
|---|---|
| 1 (no ayudó) | 3 |
| 2 | 1 |
| 3 | 3 |
| 4 | 7 |
| 5 (resolvió) | 5 |

**Promedio:** 3.53 / 5

### Resultado clave
| Métrica | Valor |
|---|---|
| ✅ Ayudó (etiqueta 4 ó 5) | 12 tickets |
| % sobre total en scope | **10.3%** |
| % sobre etiquetados | **63.2%** |
| ❌ No ayudó (1, 2, 3) | 7 tickets |
| ⬜ Sin etiqueta | 97 tickets |

### Tickets con etiqueta 4 ó 5
| Ticket | Etiqueta | Resumen |
|---|---|---|
| ESD-1361 | 5 | Error en deploy de clases - ClassNotFoundException |
| ESD-1365 | 5 | ExpandCore se queda colgado |
| ESD-1366 | 5 | Configure the Conversion rate downloader to populate the currency table via API every morning |
| ESD-1390 | 5 | No se pueden reactivar facturas con el registro de configuración de Verifactu desactivado |
| ESD-1547 | 5 | Upgrade Etendo 24 to 25 |
| ESD-1386 | 4 | Modelo 390 v2025 - Duplicación parámetros en Rango Impuesto "Servicios exentos" |
| ESD-1395 | 4 | Creación descontrolada de ficheros temporales de tomcat |
| ESD-1412 | 4 | ESD-1359: Data Encryption for Numeric Fields in Etendo |
| ESD-1467 | 4 | Problema con las versiones de librerias de jasper y poi |
| ESD-1482 | 4 | Ejecución/Llamada a Agentes de Copilot con procesos Background |
| ESD-1531 | 4 | Custom Oauth provider para Etendo Copilot |
| ESD-1541 | 4 | Modelo 347 rango de impuesto Prestación servicios exenta por suplido |

> ⚠️ **97 de 116 tickets (84%) no tienen etiqueta**. El porcentaje real podría variar significativamente si se etiquetaran todos los tickets.

---

## Resultado Q2 2026 (ejecutado el 15/04/2026)

> ⚠️ El Q2 acaba de comenzar. Solo hay 10 tickets en scope — los datos crecerán durante el trimestre.

| Métrica | Valor |
|---|---|
| Tickets Done en Q2 2026 (pre-filtro) | 13 |
| Excluidos Cloud | 0 |
| Excluidos [TEST AGENTE] | 0 |
| Excluidos manuales (ESD-1722, ESD-1717, ESD-1721) | 3 |
| **Tickets en scope** | **10** |
| Con etiqueta IA (1–5) | 10 |
| Sin etiqueta IA | 0 |

### Distribución de etiquetas
| Etiqueta | Tickets |
|---|---|
| 1 (no ayudó) | 1 |
| 2 | 2 |
| 3 | 1 |
| 4 | 3 |
| 5 (resolvió) | 3 |

**Promedio:** 3.50 / 5

### Resultado clave
| Métrica | Valor |
|---|---|
| ✅ Ayudó (etiqueta 4 ó 5) | 6 tickets |
| % sobre total en scope | **60.0%** |
| % sobre etiquetados | **60.0%** |
| ❌ No ayudó (1, 2, 3) | 4 tickets |
| ⬜ Sin etiqueta | 0 tickets |

### Todos los tickets en scope
| Ticket | Etiqueta | Resumen |
|---|---|---|
| ESD-1709 | 5 | Inquiry on Etendo 25.4.11 Compatibility with Tomcat 11 |
| ESD-1713 | 5 | Consulta sobre autenticación de doble factor (2FA) en Etendo |
| ESD-1714 | 5 | Problemas al instalar pack de localización 3.12.0 |
| ESD-1710 | 4 | Acogerse a Verifactu |
| ESD-1715 | 4 | Problema al imprimir reports tras actualizar de Etendo 24 a 25 |
| ESD-1724 | 4 | Issue After Etendo 25.4.11 Upgrade – Batik & Barcode JAR Error |
| ESD-1708 | 3 | Consulta SII – Liquidación trimestral Modelo 303 |
| ESD-1707 | 2 | Error al reactivar remesa |
| ESD-1712 | 2 | Problema al intentar loguearse un usuario con rol system admin |
| ESD-1706 | 1 | OpenAPI Request ejecutada por Copilot devuelve code 200 pero no ejecuta |

---

## Notas técnicas de implementación

### ⚠️ No usar el MCP de Jira para este análisis

El MCP tool `mcp__jira__jira_search_issues` **no sirve** para este análisis por dos razones:
1. **No devuelve `labels` ni `customfield_10300`** — solo retorna key, summary, description, acceptanceCriteria.
2. **La paginación con `startAt` no funciona** — devuelve siempre los mismos 100 resultados.

**Solución:** usar la API REST directamente vía `python3` con `urllib.request` (no hace falta instalar nada extra).

### Endpoint correcto

```
POST https://etendoproject.atlassian.net/rest/api/3/search/jql
```

> ⚠️ El endpoint antiguo `GET /rest/api/3/search` devuelve **HTTP 410** (eliminado). Usar siempre el POST `/search/jql`.

### Paginación

La respuesta incluye `isLast: bool` y `nextPageToken: str`. Iterar enviando `nextPageToken` en el body hasta que `isLast == True` o la lista venga vacía.

### Estructura de la respuesta relevante

```json
{
  "isLast": false,
  "nextPageToken": "...",
  "issues": [
    {
      "key": "ESD-XXXX",
      "fields": {
        "summary": "...",
        "labels": ["3"],
        "customfield_10300": {
          "requestType": { "name": "Cloud" }
        }
      }
    }
  ]
}
```

---

## Script completo (Python — listo para ejecutar)

```python
import urllib.request, json, base64

TOKEN = "<leer de /Users/lucaspalacios/.claude.json → mcpServers.jira.env.JIRA_API_TOKEN>"
USER  = "lucas.palacios@smfconsulting.es"
HOST  = "etendoproject.atlassian.net"
Q_START, Q_END = "2026-01-01", "2026-03-31"   # ajustar al trimestre actual

creds = base64.b64encode(f"{USER}:{TOKEN}".encode()).decode()
headers = {
    "Authorization": f"Basic {creds}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

all_issues = []
next_page_token = None

while True:
    payload = {
        "jql": f'project = ESD AND created >= "{Q_START}" AND created <= "{Q_END}" AND status = Done',
        "fields": ["summary", "labels", "customfield_10300"],
        "maxResults": 100
    }
    if next_page_token:
        payload["nextPageToken"] = next_page_token

    req = urllib.request.Request(
        f"https://{HOST}/rest/api/3/search/jql",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        result = json.load(resp)

    issues = result.get("issues", [])
    all_issues.extend(issues)
    if result.get("isLast", True) or not issues:
        break
    next_page_token = result.get("nextPageToken")

# --- Análisis ---
in_scope, excl_cloud, excl_test = [], 0, 0

for issue in all_issues:
    fields   = issue.get("fields", {})
    summary  = fields.get("summary", "")
    labels   = fields.get("labels", [])
    cf       = fields.get("customfield_10300") or {}
    req_type = cf.get("requestType", {}).get("name", "")

    if req_type == "Cloud":        excl_cloud += 1; continue
    if "[TEST AGENTE]" in summary: excl_test  += 1; continue

    ai_labels = [l for l in labels if l in ["1","2","3","4","5"]]
    ai_score  = max(ai_labels, key=int) if ai_labels else None
    in_scope.append({"key": issue["key"], "summary": summary, "ai_score": ai_score})

labeled   = [t for t in in_scope if t["ai_score"]]
unlabeled = [t for t in in_scope if not t["ai_score"]]
helped    = [t for t in labeled  if t["ai_score"] in ["4","5"]]
not_helped= [t for t in labeled  if t["ai_score"] in ["1","2","3"]]
avg       = sum(int(t["ai_score"]) for t in labeled) / len(labeled) if labeled else 0

from collections import Counter
score_dist = Counter(t["ai_score"] for t in labeled)

print(f"Total Done (pre-filtro): {len(all_issues)}")
print(f"Excluidos Cloud:         {excl_cloud}")
print(f"Excluidos [TEST AGENTE]: {excl_test}")
print(f"En scope:                {len(in_scope)}")
print(f"Con etiqueta:            {len(labeled)}")
print(f"Sin etiqueta:            {len(unlabeled)}")
for s in ["1","2","3","4","5"]:
    print(f"  Etiqueta {s}: {score_dist.get(s,0)}")
print(f"Ayudó (4-5):             {len(helped)}  → {len(helped)/len(in_scope)*100:.1f}% total, {len(helped)/len(labeled)*100:.1f}% etiquetados")
print(f"No ayudó (1-3):          {len(not_helped)}")
print(f"Promedio:                {avg:.2f} / 5")
print("\nTickets que ayudaron:")
for t in helped:
    print(f"  {t['key']} [{t['ai_score']}] {t['summary'][:70]}")
```
