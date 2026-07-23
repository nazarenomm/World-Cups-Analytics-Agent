"""
Capa de ejecución de SQL: validación defensiva + conexión de solo lectura
+ manejo de errores para reintentos.
"""
import os
import re
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["AGENT_DB_CONNECTION_STRING"]


# Excepción personalizada para queries no seguras
class UnsafeQueryError(Exception):
    """La query no pasó la validación de solo-lectura."""
    pass


def is_safe_select(query: str) -> bool:
    """
    Validación defensiva (segunda capa, no la principal).
    La barrera dura real es el rol agent_readonly a nivel de Postgres.
    """
    q = query.strip().rstrip(";")

    # Debe empezar con SELECT o WITH (para las CTEs)
    if not re.match(r"(?is)^\s*(SELECT|WITH)\b", q):
        return False

    # Bloquea keywords de escritura/DDL en cualquier parte de la query
    forbidden = r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXECUTE|CALL)\b"
    if re.search(forbidden, q, re.IGNORECASE):
        return False

    # Bloquea múltiples statements encadenados (';' en medio de la query, no al final)
    if ";" in q:
        return False

    return True


def execute_query(query: str) -> tuple[list[str], list[tuple]]:
    """
    Ejecuta una query SELECT validada contra la base con el rol agent_readonly.
    Devuelve (nombres_de_columnas, filas).
    Levanta UnsafeQueryError si la query no pasa la validación de texto,
    o psycopg2.Error si Postgres la rechaza.
    """
    if not is_safe_select(query):
        raise UnsafeQueryError(f"La consulta no pasó la validación de solo lectura: {query}")

    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    try:
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        return colnames, rows
    finally:
        conn.close()


if __name__ == "__main__":
    # Tests rápidos
    test_queries = [
        "SELECT * FROM teams LIMIT 5", # select, deberia pasar
        "DELETE FROM matches WHERE match_id = 'M-1930-01'", # delete
        "SELECT * FROM teams; DROP TABLE teams;", # dos statements
        "WITH t AS (SELECT * FROM teams) SELECT * FROM t LIMIT 3", # CTE, deberia pasar
    ]
    for q in test_queries:
        print(f"{q!r:60} -> safe={is_safe_select(q)}")

    print("\n--- Ejecución real ---")
    cols, rows = execute_query("SELECT team_name FROM teams LIMIT 3")
    print(cols)
    for r in rows:
        print(r)