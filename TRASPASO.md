# Traspaso — CS Dashboard (Lucas Palacios → Juan Funes)

Fecha: 2026-11-11

## Qué es

Script en Python que consulta Jira (proyecto **ESD**, Etendo Service Desk), calcula 3 métricas
por trimestre (SLO de resolución, Dedicación promedio y Chatbot IA) y publica el resultado en
GitHub Pages: https://lucas-palacios.github.io/cs-dashboard/

Detalle de cada métrica y sus exclusiones: ver `README.md`. **Si el README y `update.py` no
coinciden, manda el código.**

## Puesta en marcha (una sola vez)

1. Clonar el repo y tener Python 3.10 o superior.
2. `pip install -r requirements.txt`
3. Crear tu API token de Atlassian: https://id.atlassian.com/manage-profile/security/api-tokens
4. `cp .env.example .env` y completar `JIRA_USER` (tu email de Jira) y `JIRA_TOKEN`.
   - `.env` está en `.gitignore`. El repo es **público**: no pongas el token en el código.
5. (Opcional) `ANTHROPIC_API_KEY` en `.env` para que `--analyze` puntúe con IA. Sin esa clave,
   el modo es interactivo y te pide la nota de cada ticket.
6. Prueba: `python3 update.py`. Debería recalcular el Q actual, regenerar `index.html` y hacer
   commit + push. Para el push necesitás permiso de escritura en el repo.

## Uso habitual

| Comando | Qué hace |
|---|---|
| `python3 update.py` | Recalcula los Q no congelados, genera `index.html`, commit y push (publica) |
| `python3 update.py --analyze` | Busca tickets Done del Q actual sin label 1–5 y les aplica la puntuación del chatbot en Jira |
| `python3 update.py --analyze --dry-run` | Igual, pero sin escribir en Jira |
| `python3 export_dedicacion.py [Q_ID]` | Excel con los tickets en scope y fuera de scope de Dedicación (por defecto, el Q actual) |

Hasta ahora se ejecutaba a mano unas 2 o 3 veces por semana (ver `git log`).

## Tareas recurrentes y cosas a tener en cuenta

- **Antes del 1 de enero de 2027: añadir `Q1_2027` a `QUARTERS` en `update.py`.** Si no está,
  Q4 se congela y ya no se calcula ningún quarter nuevo.
- **Congelado:** cuando pasa la fecha de fin de un Q, su JSON en `data/` queda `"frozen": true`
  y no se vuelve a consultar Jira. Para recalcularlo, poner `"frozen": false` a mano.
- **Exclusiones manuales del chatbot:** `chatbot_manual_exclude` dentro de cada quarter.
- **OKRs:** `OKR_DEDICACION` (1.7 h/ticket) y `OKR_CHATBOT` (50 %) arriba del todo en `update.py`.
- **Reporters internos excluidos:** `SLO_EXCLUDED_EMAILS` e `INTERNAL_REPORTERS`. Si entra
  alguien nuevo al equipo de CS, hay que añadirlo ahí.
- **Label `excluded`** en un ticket de Jira lo saca de las tres métricas. **`AGENT_TIME_ONLY`**
  lo saca solo del chatbot.
- `documentos desactualizados/` son los análisis originales de cada métrica. Sirven de contexto,
  pero pueden no reflejar la lógica actual.

## Pendiente del traspaso

- [ ] Juan: crear su token de Jira y su `.env`.
- [x] Dar a Juan acceso de escritura al repo (invitación enviada a `juanfunes1996`; tiene que aceptarla).
- [ ] Lucas: revocar su token de Jira en este script cuando Juan ya lo tenga funcionando.
- [ ] Juan: añadir `Q1_2027` antes de fin de año.
