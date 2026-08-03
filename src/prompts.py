"""
Prompts y reglas de dominio para el pipeline de Text-to-SQL.
"""

GENERAL_SQL_RULES = """
Reglas generales importantes a tener en cuenta al generar la consulta:

1. Entidades históricas divididas: algunos países aparecen como múltiples filas 
   distintas en `teams` (team_id distintos) debido a cambios políticos históricos:
   - Alemania: 'West Germany',  'East Germany' (1954-1990) y 'Germany' (1930-1950 y 1994-presente)
   - URSS/Rusia: 'Soviet Union' (hasta 1990) y 'Russia' (desde 1994)
   - Yugoslavia: 'Yugoslavia' (hasta 1992), 'Serbia and Montenegro' (1992-2006), 'Serbia' (desde 2006), 'Croatia', etc.
   - Czechoslovakia: 'Czechoslovakia' (hasta 1992), 'Czech Republic' (desde 1994), 'Slovakia' (desde 1994)
   - Considerar otros casos que puedan surgir en los datos...

   Esto puede causar dos problemas si no se maneja con cuidado:
   a) Al hacer GROUP BY team_id/team_name sobre estadísticas de carrera de un 
      jugador/DT, su total puede quedar DIVIDIDO en dos filas si jugó bajo ambas 
      entidades (ej. Lothar Matthäus con Alemania Occidental y Alemania), 
      pudiendo hacerlo desaparecer de un ranking top-N.
   b) Al hacer JOIN de una vista de estadísticas de carrera (ya agregada por 
      jugador) con player_appointments/team para obtener el nombre del equipo, 
      un jugador con apariciones bajo ambas entidades genera FILAS DUPLICADAS 
      con el mismo total.
   c) En un top de equipos por cantidad de goles, victorias, etc., un país histórico puede
      aparecer como dos filas separadas (ej. Alemania Occidental y Alemania, cuando actualmente 
      se las considera la misma entidad).
   
   Si la pregunta pide totales de carrera de un jugador/DT junto con su país,
   preferí tomar UN equipo representativo por persona (ej. usando 
   DISTINCT ON (player_id) ordenado por tournament_id DESC para tomar el más 
   reciente) en vez de agrupar o unir de forma que divida o duplique el total.

2. Cuando el usuario pida un ranking top-N, evita usar LIMIT,
   usar FETCH FIRST N ROWS WITH TIES en su lugar para incluir empates en el último lugar del ranking.

3. Asigná alias explicativos a las columnas de la consulta SQL para que el resultado sea más legible en el idioma del prompt.

4. Si la pregunta pide un dato que NO EXISTE en el schema disponible (ej. asistencias 
   de gol, valor de mercado, altura de los jugadores, lesiones), marcá 
   answerable=false y explicá en "reason" qué dato falta específicamente. No inventes 
   ni aproximes ese dato con columnas que midan algo distinto.

5. Ordená los resultados de ser necesario según la intención real de la pregunta: si pide "más", "mayor", 
   "top" (sin calificar dirección), usá ORDER BY ... DESC. Si pide "menos", "menor", 
   "mínimo" (ej. "equipos con menos goles recibidos"), usá ORDER BY ... ASC. El primer 
   resultado de la consulta debe ser siempre el que mejor responde la pregunta.

6. Si el usuario pide por un mapa, debes incluir una columna numerica que represente la magnitud de la variable a mostrar en el mapa.
   Si la pregunta es binaria que la columna numerica es 1 para los que cumplen la condición y 0 para los que no cumplen la condición.
"""

CHART_RULES = """
Además de la consulta SQL, sugerí el tipo de gráfico más apropiado para visualizar
el resultado, considerando la intención de la pregunta (no solo la forma de los datos):

- "metric": un solo valor destacado (ej. "¿cuántos goles hizo X?").
- "bar_h": comparar una métrica numérica entre pocas categorías (ej. rankings, top-N).
- "line": evolución de una métrica a través del tiempo/ediciones de mundiales.
- "scatter": relación entre dos variables numéricas.
- "none": cuando un gráfico no aporta valor (ej. listas de nombres sin métrica clara, demasiadas variables, etc.).

Si el usuario pidió explícitamente "colorear por" o "agrupar por" alguna variable, indicá el nombre EXACTO de la 
columna correspondiente (tal como aparece en el resultado de tu propia consulta SQL,
usando el alias que le hayas dado) en "chart_color_by". Solo colorear si se pide. 
En caso contrario, dejá "chart_color_by" como string vacío "".
"""

SYSTEM_ROLE = "especialista en PostgreSQL y visualización de datos"

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "reason": {"type": "string"},
        "sql_query": {"type": "string"},
        "chart_type": {
            "type": "string",
            "enum": ["none", "metric", "bar_h", "line", "scatter", "pie", "bar_v", "map"],
        },
        "chart_color_by": {"type": "string"},
    },
    "required": ["answerable", "reason", "sql_query", "chart_type", "chart_color_by"],
}


def build_text_to_sql_prompt(user_prompt: str, schema_injection: str) -> str:
    return f"""
    rol: {SYSTEM_ROLE},
    
    prompt del usuario: 
    {user_prompt}
    
    tablas disponibles:
    {schema_injection}
    
    {GENERAL_SQL_RULES}

    {CHART_RULES}
    
    instrucciones: Analizá si la pregunta del usuario puede responderse con las tablas 
    disponibles. Si es así, generá la consulta SQL correspondiente. Si no es así 
    (porque pide un dato que no existe en el schema), explicá brevemente por qué en 
    el campo "reason" y dejá "sql_query" como string vacío.
    
    Respondé siguiendo estrictamente el formato JSON solicitado.
    """


def build_retry_prompt(failed_sql: str, error_message: str) -> str:
    return f"""
    La consulta SQL que generaste falló al ejecutarse contra la base de datos.
    
    Consulta que falló:
    {failed_sql}
    
    Error de PostgreSQL:
    {error_message}
    
    Corregí la consulta para que se ejecute correctamente, manteniendo el objetivo 
    original de la pregunta. Si al analizar el error concluís que la pregunta en 
    realidad no es respondible con las tablas disponibles, marcá answerable=false 
    y explicá por qué en "reason".
    
    Respondé siguiendo estrictamente el formato JSON solicitado.
    """


def build_followup_prompt(user_prompt: str, schema_injection: str) -> str:
    return f"""
    El usuario hizo un nuevo pedido o una corrección del pedido anterior.

    Nuevo pedido del usuario:
    {user_prompt}

    tablas disponibles:
    {schema_injection}

    {GENERAL_SQL_RULES}

    {CHART_RULES}

    instrucciones: Analizá si este nuevo pedido puede responderse con las tablas 
    disponibles, teniendo en cuenta el contexto de la conversación anterior si es 
    relevante. Si el pedido es independiente y no se relaciona con lo anterior, 
    respondé solo a este nuevo pedido. Si no es respondible con las tablas 
    disponibles, marcá answerable=false y explicá por qué en "reason".
    
    Respondé siguiendo estrictamente el formato JSON solicitado.
    """