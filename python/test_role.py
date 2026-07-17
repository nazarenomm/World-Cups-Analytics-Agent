import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.environ["AGENT_DB_CONNECTION_STRING"]

def test_select():
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()
    cur.execute("SELECT * FROM matches LIMIT 5;")
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    print(colnames)
    for row in rows:
        print(row)
    cur.close()
    conn.close()

def test_permission_denied():
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM match_balls WHERE ball_id = 'B-1';")
        conn.commit()
        print("⚠️ ALERTA: el DELETE se ejecutó, el rol NO está bien restringido")
    except psycopg2.errors.InsufficientPrivilege:
        print("✅ Correcto: permission denied, el rol está bien restringido")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    test_select()
    test_permission_denied()