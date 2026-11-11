# SLO Analysis — Etendo Service Desk (ESD)

## Qué hace este análisis

Calcula el porcentaje de tickets del proyecto **ESD (Etendo Service Desk)** en Jira que vencieron el SLO de tiempo de resolución ("Resolution Time SLO") durante el **trimestre actual**.

---

## Cómo ejecutarlo

Decirle a Claude:

> "Ejecuta el análisis SLO del trimestre actual usando el documento SLO-Analysis-ESD.md"

Claude leerá este documento y ejecutará todo automáticamente.

---

## Lógica del análisis

### Credenciales Jira
Están en `/Users/lucaspalacios/.claude.json` bajo `mcpServers.jira`:
- **Host:** `etendoproject.atlassian.net`
- **User:** `lucas.palacios@smfconsulting.es`
- **Token:** en el archivo

### Ventana de búsqueda
- Buscar tickets desde **2 meses antes del inicio del trimestre actual**.
- Ejemplo: para Q1 2026 (enero–marzo), buscar desde `2025-11-01`.

### Campo clave: `customfield_12095` — "SLO Resolution Time"
- Si tiene valor → el SLO **se venció** (la fecha indica cuándo).
- Si está vacío y el ticket está `Done` → el SLO **se cumplió**.

### Tickets que NO cuentan (excluir del análisis)
1. `customfield_10300.requestType.name == "Cloud"`
2. Título (`summary`) contiene `[TEST AGENTE]`
3. Label `excluded` en el ticket
4. Email del reporter contiene `etendo.software` o `smfconsulting`

### Tickets que SÍ cuentan para el trimestre (denominator)
- Creados **dentro del trimestre actual**, O
- Creados en el mes previo (ventana de búsqueda) cuyo campo `customfield_12095` cae **dentro del trimestre actual**.

### Cálculo
```
Tasa de vencimiento = tickets con SLO vencido / tickets cerrados (Done) en scope × 100
```
Solo se cuentan tickets cerrados (status = Done) porque los abiertos aún no tienen resultado definitivo.

---

## Resultado Q1 2026 (ejecutado el 13/03/2026)

| Métrica | Valor |
|---|---|
| Tickets consultados (desde 01/11/2025) | — (pendiente re-ejecutar) |
| Excluidos (Cloud + internos + TEST) | 190 |
| **Tickets en scope Q1** | **97** |
| Cerrados (Done) | 73 |
| Aún abiertos | 24 |
| ✅ SLO cumplido | 73 |
| ❌ SLO vencido | 0 |
| **Tasa de vencimiento** | **0.0%** |
| **Cumplimiento SLO** | **100%** |

### Nota ESD-1291
Ticket creado el 12/11/2025 (fuera de la ventana Dec 1), con SLO vencido el 21/01/2026 (Q1).
Quedó fuera por el corte de búsqueda. Si se incluyera: tasa = 1/74 = **1.4%**.

---

## Resultado Q2 2026 (ejecutado el 15/04/2026)

| Métrica | Valor |
|---|---|
| Tickets consultados (desde 01/02/2026) | 259 |
| Excluidos (Cloud + internos + TEST) | 148 |
| **Tickets en scope Q2** | **17** |
| Cerrados (Done) | 11 |
| Aún abiertos | 6 |
| ✅ SLO cumplido | 11 |
| ❌ SLO vencido | 0 |
| **Tasa de vencimiento** | **0.0%** |
| **Cumplimiento SLO** | **100%** |

> Nota: el Q2 acaba de comenzar (15/04/2026). Hay 6 tickets abiertos que aún no tienen resultado definitivo.

---

## Script de referencia (Python)

```python
# Autenticación Jira REST API v3
# Endpoint: POST https://etendoproject.atlassian.net/rest/api/3/search/jql
# Fields: summary, status, reporter, customfield_12095, customfield_10300, created
# JQL base: project = ESD AND created >= "{Q_MINUS_2_MONTHS}" ORDER BY created ASC
# Paginar con nextPageToken hasta isLast=True

# Exclusiones:
#   customfield_10300.requestType.name == "Cloud"
#   "[TEST AGENTE]" in summary
#   "etendo.software" or "smfconsulting" in reporter.emailAddress

# Scope Q1:
#   q1_start <= created_date <= q1_end  → in scope
#   created_date < q1_start AND q1_start <= slo_breach_date <= q1_end → in scope

# Métricas:
#   breached = [t for t in scope if t.customfield_12095 is not None]
#   met = [t for t in scope if not t.customfield_12095 and t.status == "Done"]
#   rate = len(breached) / (len(breached) + len(met)) * 100
```
