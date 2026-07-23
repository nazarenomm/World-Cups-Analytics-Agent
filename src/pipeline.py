"""
Orquesta el flujo completo: prompt del usuario -> SQL generado -> ejecución de la query
-> retry con el error si falla, hasta un máximo de intentos.
"""
import os
from google import genai
from dotenv import load_dotenv

from config import USE_SCHEMA_PRUNING, GEMINI_MODEL, SCHEMA_PRUNING_TOP_K, SCHEMA_FULL_TOP_K, MAX_SQL_RETRIES
from prompts import build_followup_prompt, build_text_to_sql_prompt, build_retry_prompt
from schema_format import format_schema_for_prompt
from schema_pruning import get_relevant_tables
from db import execute_query, UnsafeQueryError
import psycopg2

load_dotenv()

_client = genai.Client(api_key=os.environ["GOOGLE_KEY"])


def _clean_sql(raw_text: str) -> str:
    """Por si el LLM devuelve la query envuelta en markdown fences a pesar de la instrucción."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.removeprefix("sql").strip()
    return text.strip()


def _get_schema_injection(user_prompt: str) -> str:
    top_k = SCHEMA_PRUNING_TOP_K if USE_SCHEMA_PRUNING else SCHEMA_FULL_TOP_K
    relevant = get_relevant_tables(user_prompt, top_k=top_k)
    return format_schema_for_prompt(relevant)


def run_pipeline(user_prompt: str, chat_session=None) -> dict:
    """
    chat_session: sesión de chat existente (para mantener contexto conversacional
    entre preguntas del usuario, ej. 'top 10' -> 'mejor top 20'). Si es None,
    se crea una nueva (primera pregunta de la sesión).
    """
    schema_injection = _get_schema_injection(user_prompt)

    if chat_session is None:
        chat_session = _client.chats.create(model=GEMINI_MODEL)
        prompt_to_send = build_text_to_sql_prompt(user_prompt, schema_injection)
    else:
        # Ya tiene contexto previo; solo necesita el nuevo pedido + el schema
        prompt_to_send = build_followup_prompt(user_prompt, schema_injection)

    response = chat_session.send_message(prompt_to_send)
    sql = _clean_sql(response.text)

    last_error = None
    attempt = 1
    for attempt in range(1, MAX_SQL_RETRIES + 1):
        try:
            columns, rows = execute_query(sql)
            return {
                "success": True,
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "attempts": attempt,
                "chat_session": chat_session,  # se devuelve para persistir en session_state
            }
        except UnsafeQueryError as e:
            last_error = str(e)
            break
        except psycopg2.Error as e:
            last_error = str(e)
            if attempt == MAX_SQL_RETRIES:
                break
            retry_prompt = build_retry_prompt(sql, last_error)
            response = chat_session.send_message(retry_prompt)
            sql = _clean_sql(response.text)

    return {
        "success": False,
        "sql": sql,
        "error": last_error,
        "attempts": attempt,
        "chat_session": chat_session,
    }


if __name__ == "__main__":
    result = run_pipeline("¿Cuántos goles hizo Messi en el mundial 2022?")
    print(result)