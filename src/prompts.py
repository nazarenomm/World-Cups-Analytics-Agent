"""
Prompts y reglas de dominio para el pipeline de Text-to-SQL.
"""

GENERAL_SQL_RULES = """
Reglas generales importantes a tener en cuenta al generar la consulta:

1. Entidades históricas divididas: algunos países aparecen como múltiples filas 
   distintas en `teams` (team_id distintos) debido a cambios políticos históricos:
   - Alemania: 'West Germany' y 'East Germany' (1954-1990) y 'Germany' (1994-presente)
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
   
   Si la pregunta pide totales de carrera de un jugador/DT junto con su país,
   preferí tomar UN equipo representativo por persona (ej. usando 
   DISTINCT ON (player_id) ordenado por tournament_id DESC para tomar el más 
   reciente) en vez de agrupar o unir de forma que divida o duplique el total.
"""

SYSTEM_ROLE = "especialista en PostgreSQL"

def build_text_to_sql_prompt(user_prompt: str, schema_injection: str) -> str:
    return f"""
    rol: {SYSTEM_ROLE},
    
    prompt del usuario: 
    {user_prompt}
    
    tablas disponibles:
    {schema_injection}
    
    {GENERAL_SQL_RULES}
    
    instrucciones: Genera la consulta SQL que responda a la pregunta del prompt 
    usando las tablas disponibles. No agregues explicaciones ni comentarios, 
    devolvé únicamente el código SQL, sin backticks ni bloques de markdown.
    No cometas errores.
    """

def build_retry_prompt(failed_sql: str, error_message: str) -> str:
    return f"""
    La consulta SQL que generaste falló al ejecutarse contra la base de datos.
    
    Consulta que falló:
    {failed_sql}
    
    Error de PostgreSQL:
    {error_message}
    
    Corregí la consulta para que se ejecute correctamente, manteniendo el objetivo 
    original de la pregunta. Devolvé únicamente el SQL corregido, sin backticks 
    ni bloques de markdown, sin explicaciones.
    """

def build_followup_prompt(user_prompt: str, schema_injection: str) -> str:
    return f"""
    El usuario hizo un nuevo pedido o una corrección del pedido anterior.

    Nuevo pedido del usuario:
    {user_prompt}

    tablas disponibles:
    {schema_injection}

    {GENERAL_SQL_RULES}

    instrucciones: Genera la consulta SQL que responda al nuevo pedido, teniendo en cuenta
    el contexto de la conversación anterior si es relevante. Si el pedido es independiente
    y no se relaciona con lo anterior, respondé solo a este nuevo pedido.
    Devolvé únicamente el código SQL, sin backticks ni bloques de markdown, sin explicaciones.
    """