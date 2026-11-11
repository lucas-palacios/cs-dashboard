# CS Dashboard — Etendo Service Desk

Dashboard de métricas de soporte por trimestre. Consulta Jira automáticamente y genera `index.html`, que se publica en GitHub Pages: https://lucas-palacios.github.io/cs-dashboard/

---

## Uso rápido

```bash
cp .env.example .env        # solo la primera vez: poner tu email y token de Jira
pip install -r requirements.txt
python3 update.py           # recalcula, genera index.html y hace commit + push
```

Otros comandos:

```bash
python3 update.py --analyze             # puntúa tickets sin etiqueta del Q actual y aplica labels en Jira
python3 update.py --analyze --dry-run   # igual, sin escribir en Jira
python3 export_dedicacion.py [Q4_2026]  # Excel con tickets en scope / fuera de scope de Dedicación
```

---

## Estructura de archivos

```
dashboardcs/
├── update.py              # Script principal — ejecutar para actualizar
├── export_dedicacion.py   # Export a Excel de la métrica de Dedicación
├── index.html             # Dashboard generado (publicado en GitHub Pages)
├── .env.example           # Plantilla de credenciales (copiar a .env)
├── requirements.txt
├── README.md              # Este archivo
├── TRASPASO.md            # Notas de traspaso y tareas recurrentes
└── data/
    ├── Q1_2026.json   # Q1 2026 — frozen, no se recalcula
    ├── Q2_2026.json   # Q2 2026 — se recalcula en cada ejecución
    └── ...            # Futuros quarters
```

---

## Lógica de congelado

- Un quarter se **congela automáticamente** cuando su fecha de fin ha pasado.
- Quarters **frozen**: se cargan del JSON, no se consulta Jira.
- Quarter **actual** (no frozen): se recalcula en cada ejecución de `update.py`.
- Esto evita recalcular histórico y mantiene los tiempos de ejecución bajos.

Para forzar el recálculo de un quarter frozen: editar su JSON y poner `"frozen": false`.

---

## Métricas calculadas

### 1. ⏱ SLO de Tiempo de Resolución

**Fuente de verdad:** `SLO-Analysis-ESD.md`

**Campo Jira:** `customfield_12095` ("SLO Resolution Time")
- Si tiene valor → SLO **vencido** (la fecha indica cuándo).
- Si está vacío y el ticket está `Done` → SLO **cumplido**.

**Ventana de búsqueda:** desde 2 meses antes del inicio del Q (para capturar tickets creados antes del Q cuyo SLO venció dentro del Q).

**Tickets en scope:**
- Creados dentro del Q, O
- Creados antes del Q con fecha de vencimiento SLO dentro del Q.

**Exclusiones:**
- `customfield_10300.requestType.name == "Cloud"`
- Summary contiene `[TEST AGENTE]`
- Label `excluded` en el ticket
- Reporter con email `@etendo.software` o `@smfconsulting`

**Métrica principal:** `compliance = 100 - (vencidos / cerrados * 100)`

---

### 2. 🕐 Tiempo de Dedicación Promedio

**Fuente de verdad:** `tiempo-dedicación-promedio-analysis.md`

**OKR:** ≤ `OKR_DEDICACION` en `update.py` (actualmente 1.7 h/ticket; en Q1–Q2 era 4.15 h)

**Dos fuentes de tickets (mergeadas por key):**
1. Tickets `Done` **creados en el Q** → usan `timespent` total.
2. Tickets `Done` con **worklog con fecha en el Q** → usan solo horas del Q.

Los tickets sin worklog (creados en el Q) cuentan con 0h, porque se resolvieron sin esfuerzo.

**Exclusiones:**
- `customfield_10300.requestType.name == "Cloud"`
- Summary contiene `[TEST AGENTE]`
- Label `excluded` en el ticket
- Reporter interno por account ID (Juan Funes, Leonardo Echenique, Lucas Palacios — cuentas SMF y Etendo)

**Account IDs excluidos:**

| Persona | Account ID |
|---|---|
| Juan Funes (SMF) | `633af5977f85f16777a177d5` |
| Juan Funes (Etendo) | `qm:cd4e9010-...:de7de1b9-...` |
| Leonardo Echenique (SMF) | `63f6600afb3ac4003fa3743c` |
| Leonardo Echenique (Etendo) | `qm:cd4e9010-...:d6836056-...` |
| Lucas Palacios (SMF) | `5a79ce9599b305616a1faa55` |
| Lucas Palacios (Etendo) | `qm:cd4e9010-...:f54eb844-...` |

**Métrica principal:** `avg_hours = total_horas / total_tickets_en_scope`

---

### 3. 🤖 Chatbot IA (Agente de Soporte)

**Fuente de verdad:** `chatbot-soporte-metrica-analysis.md`

**Campo Jira:** `labels` — el bot pone una etiqueta numérica del 1 al 5.
- `1` = no ayudó nada
- `5` = resolvió el ticket completamente
- Sin etiqueta numérica = bot no interactuó o no fue evaluado

**Ayudó = etiqueta 4 ó 5.**

**Ventana:** tickets **creados en el Q** que estén `Done`, más los no cerrados que ya tengan etiqueta numérica (1-5).

**Exclusiones:**
- `customfield_10300.requestType.name == "Cloud"`
- Summary contiene `[TEST AGENTE]`
- Label `excluded` en el ticket
- Label `AGENT_TIME_ONLY` en el ticket
- ⚠️ **No se excluye por reporter** (a diferencia de SLO y Dedicación)
- `chatbot_manual_exclude` en la config del quarter (lista de keys a excluir manualmente)

**Métricas principales:**
- `pct_total = ayudó / total_en_scope * 100`
- `pct_labeled = ayudó / etiquetados * 100`
- `avg_score = suma_scores / etiquetados`

---

## Añadir un nuevo quarter

Editar `update.py` y agregar una entrada en la lista `QUARTERS`:

```python
{
    "id":    "Q3_2026",
    "label": "Q3 2026",
    "start": "2026-07-01",
    "end":   "2026-10-31",   # ← ajustar
    "chatbot_manual_exclude": [],   # ← añadir keys si hay exclusiones manuales
},
```

La próxima vez que se ejecute `python3 update.py`, calculará el nuevo quarter.

---

## Datos históricos

### Q1 2026 (01/01/2026 – 31/03/2026) — FROZEN

| Métrica | Valor |
|---|---|
| ⏱ SLO Resolución | **100%** · 0 vencidos / 73 cerrados |
| 🕐 Dedicación Promedio | **3.30 h/ticket** ✅ OKR ≤ 4.15h |
| 🤖 Chatbot IA | **10.3%** sobre total · 63.2% sobre etiquetados · score 3.53/5 |

> ⚠️ El análisis SLO de Q1 fue ejecutado el 13/03/2026 (antes de que terminara el Q). Los 24 tickets "abiertos" reflejan el estado en esa fecha.
>
> ⚠️ El chatbot Q1 tenía 97 de 116 tickets (84%) sin etiquetar, por lo que el 10.3% es un mínimo, no el valor real.

### Q2 2026 (01/04/2026 – 30/06/2026) — EN CURSO

Último cálculo: 15/04/2026 (15 días de Q).

| Métrica | Valor |
|---|---|
| ⏱ SLO Resolución | **100%** · 0 vencidos / 11 cerrados |
| 🕐 Dedicación Promedio | **1.23 h/ticket** ✅ OKR ≤ 4.15h |
| 🤖 Chatbot IA | **60.0%** sobre total · score 3.50/5 · 0 sin etiquetar |

---

## Credenciales Jira

Se leen de `.env` (o variables de entorno): `JIRA_USER`, `JIRA_TOKEN`, `JIRA_HOST`.
Cada persona usa **su propio** API token de Atlassian. `.env` está en `.gitignore`; el repo es público, no subir nunca un token.

---

## Documentos de referencia

Los análisis originales están en `documentos desactualizados/` (puede haber diferencias con el código actual; ante la duda, manda `update.py`):

| Documento | Métrica |
|---|---|
| `SLO-Analysis-ESD.md` | SLO de tiempo de resolución |
| `tiempo-dedicación-promedio-analysis.md` | Dedicación promedio |
| `chatbot-soporte-metrica-analysis.md` | Chatbot IA |
