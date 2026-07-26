"""
Orquesta el flujo completo: prompt del usuario -> SQL generado -> ejecución de la query
-> retry con el error si falla, hasta un máximo de intentos.
"""
import os
import json
from google import genai
from google.genai import types
import psycopg2
from dotenv import load_dotenv

from .config import USE_SCHEMA_PRUNING, GEMINI_MODEL, SCHEMA_PRUNING_TOP_K, SCHEMA_FULL_TOP_K, MAX_SQL_RETRIES
from .prompts import build_followup_prompt, build_text_to_sql_prompt, build_retry_prompt, RESPONSE_SCHEMA
from .schema_format import format_schema_for_prompt
from .schema_pruning import get_relevant_tables
from .db import execute_query, UnsafeQueryError

load_dotenv()

_client = genai.Client(api_key=os.environ["GOOGLE_KEY"])

_GENERATE_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=RESPONSE_SCHEMA,
)


def _get_schema_injection(user_prompt: str) -> str:
    top_k = SCHEMA_PRUNING_TOP_K if USE_SCHEMA_PRUNING else SCHEMA_FULL_TOP_K
    relevant = get_relevant_tables(user_prompt, top_k=top_k)
    return format_schema_for_prompt(relevant)


def _send_and_parse(chat_session, prompt_to_send: str) -> dict:
    """Envía el mensaje y parsea la respuesta JSON estructurada."""
    response = chat_session.send_message(prompt_to_send, config=_GENERATE_CONFIG)
    return json.loads(response.text)


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
        prompt_to_send = build_followup_prompt(user_prompt, schema_injection)

    parsed = _send_and_parse(chat_session, prompt_to_send)

    if not parsed.get("answerable", False):
        return {
            "success": False,
            "answerable": False,
            "reason": parsed.get("reason", "No se pudo determinar el motivo."),
            "sql": None,
            "attempts": 1,
            "chat_session": chat_session,
        }

    sql = parsed["sql_query"].strip()

    last_error = None
    attempt = 1
    for attempt in range(1, MAX_SQL_RETRIES + 1):
        try:
            columns, rows = execute_query(sql)
            return {
                "success": True,
                "answerable": True,
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "attempts": attempt,
                "chat_session": chat_session,
            }
        except UnsafeQueryError as e:
            last_error = str(e)
            break
        except psycopg2.Error as e:
            last_error = str(e)
            if attempt == MAX_SQL_RETRIES:
                break
            retry_prompt = build_retry_prompt(sql, last_error)
            parsed = _send_and_parse(chat_session, retry_prompt)

            if not parsed.get("answerable", False):
                return {
                    "success": False,
                    "answerable": False,
                    "reason": parsed.get("reason", "No se pudo determinar el motivo."),
                    "sql": sql,
                    "attempts": attempt,
                    "chat_session": chat_session,
                }
            sql = parsed["sql_query"].strip()

    return {
        "success": False,
        "answerable": True,  # era respondible, pero falló técnicamente tras los reintentos
        "sql": sql,
        "error": last_error,
        "attempts": attempt,
        "chat_session": chat_session,
    }


if __name__ == "__main__":
    result = run_pipeline("¿Cuántas asistencias dio Messi en mundiales?")
    print(result)