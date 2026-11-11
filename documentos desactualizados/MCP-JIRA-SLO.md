* Lee el archivo .claude.json que está en /Users/lucaspalacios
* Dentro encontrarás el acceso al mcp de jira para mi usuario.
* En nuestro Jira se encuentra nuestro portal de soporte de Etendo. El proyecto se llama Etendo Service Desk (ESD).
* En ese proyecto tenemos configurado un SLA que se llama "Resolution Time SLO". 
* Actualmente para cada ticket medimos el SLO de tiempo de resolución utilizando el contador de Jira de los SLA. 
* Cómo sabemos que un ticket se ha vencido el SLO de tiempo de resolución? En cada ticket, verás que hay un campo custom creado llamado "SLO Resolution Time". Si este campo tiene un valor, quiere decir que se venció. Si está vacío y el ticket está en estado Closed, se ha cumplido. Es un campo de tipo fecha, que indica en que fecha se venció el ticket.
* Necesito calcular que porcentaje de tickets se han vencido en el trimestre actual. Para ello hay que comparar la fecha de creación con la que está informada en el campo "SLO Resolution Time". 
* No todos los tickets tienen que estar en la consideración del cálculo de vencimiento de SLO. Cuales no cuentan? 1) Los que son de Request Type "Cloud" 2) los que tienen  en el título del ticket lo siguiente: "[TEST AGENTE]" 3) Todos aquellos tickets que donde el reporter tenga email que contenga "etendo.software" o "smfconsulting"
* tienes permiso para consultar lo que quieras en jira. 
* tienes permiso para leer cualquier archivo de mi sistema.
* si un ticket se creó antes de este trimestre, pero su fecha de vencimiento está dentro de este Q1, también cuenta. Solo mira los tickets de un mes antes de que inicie el trimestre, para evitar ver todo el historial de tickets. Por ejemplo, dado que estamos en el Q1 de 2026, solo mira desde 01/12/2025. 1 mes antes de que inicie el Q1.