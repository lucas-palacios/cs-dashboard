* Lee el archivo .claude.json que está en /Users/lucaspalacios   Dentro encontrarás el acceso al mcp de jira para mi usuario.
* En nuestro Jira se encuentra nuestro portal de soporte de Etendo. El proyecto se llama Etendo Service Desk (ESD).
* Tenemos un bot de IA que se encarga de responder los tickets e interactuar con el partner. Cuando no sabe dar la respuesta, solicita de la ayuda de un humano.
* Necesito saber en cuantos tickets la IA nos ha ayudado. Para eso, en cada uno de los tickets utilizamos los Labels, en donde ponemos una etiqueta que es un número del 1 al 5. 1 como que no nos ayudó nada, y 5 como que resolvió el tikcet.
* Yo considero que nos ha ayudado cuando la etiqueta que se le colocó es "4" o "5".
* Entonces necesito saber que porcentaje de tickets del trimestre la IA nos ha ayudado. 
* Para ello, tu tarea es recolectar todos los tickets que se trabajaron en el Q1 de 2026 y sacar la lista de todos aquellos que tienen la etiqueta "4" o "5."
* Y una vez recolectados, darme la info de cantidad de tickets que terminaron con 4, cuantos con 5, cantidad de tickets total que se tuvieron en cuenta, promedio, etc.
* Cuales tickets hay que tener en cuenta? todos aquellos que se crearon en este Q tengan o no etiqueta.
* cuales tickets no hay que tener en cuenta? 1) Los que son de Request Type "Cloud" 2) los que tienen  en el título del ticket lo siguiente: "[TEST AGENTE]" 3) los que no están en estado DONE.

---

## Atajos de ejecución

### Credenciales y configuración
- El MCP de Atlassian se autentica via claude.ai (no en .claude.json). Usar `/mcp` y seleccionar "claude.ai Atlassian".
- **cloudId:** `b79eca5e-7328-40d8-a6cf-be75e6f159b2` (etendoproject.atlassian.net)

### JQL para tickets DONE del trimestre (excl. [TEST AGENTE])
```
project = ESD AND created >= "YYYY-MM-DD" AND created <= "YYYY-MM-DD" AND status = Done AND summary !~ "[TEST AGENTE]" ORDER BY key ASC
```
- Fechas Q1 2026: `2026-01-01` / `2026-03-31`
- Fechas Q2 2026: `2026-04-01` / `2026-06-30`
- Paginar con `AND key > "ESD-XXXX"` usando la última clave devuelta (máx 100 por página).
- Campos a pedir: `["summary", "status", "labels", "issuetype", "created"]`

### JQL para tickets Cloud (a excluir)
```
project = ESD AND created >= "YYYY-MM-DD" AND created <= "YYYY-MM-DD" AND status = Done AND "Customer Request Type" = "Cloud" ORDER BY key ASC
```
- El campo correcto es **"Customer Request Type"** (no "Request Type").
- También paginar con `AND key > "ESD-XXXX"` si hay más de 100.

### Script de análisis (Python)
Una vez descargados los archivos JSON de los resultados, usar este script adaptando las rutas:

```python
import json
from collections import Counter

# Cargar páginas de tickets DONE
done_files = [ ... ]  # lista de rutas a los archivos JSON
cloud_files = [ ... ] # lista de rutas a los archivos JSON de Cloud

all_done = []
for f in done_files:
    with open(f) as fp:
        data = json.load(fp)
    all_done.extend(data['issues']['nodes'])

cloud_keys = set()
for f in cloud_files:
    with open(f) as fp:
        data = json.load(fp)
    for issue in data['issues']['nodes']:
        cloud_keys.add(issue['key'])

# Filtrar Cloud y [TEST AGENTE]
filtered = [i for i in all_done
            if i['key'] not in cloud_keys
            and '[TEST AGENTE]' not in i['fields'].get('summary','').upper()]

# Calcular métricas
ai_labels = {'1','2','3','4','5'}
label_counts = Counter()
for issue in filtered:
    labels = issue['fields'].get('labels', [])
    scores = [l for l in labels if l in ai_labels]
    if scores:
        label_counts[scores[0]] += 1

total = len(filtered)
helped = label_counts.get('4', 0) + label_counts.get('5', 0)
total_labeled = sum(label_counts.values())
print(f"Total válidos: {total}, IA ayudó: {helped} ({helped/total*100:.1f}%)")
```