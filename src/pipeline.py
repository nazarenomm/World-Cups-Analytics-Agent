"""
Orquesta el flujo completo: prompt del usuario -> SQL generado -> ejecución de la query
-> retry con el error si falla, hasta un máximo de intentos.
"""
import os
import json
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
import psycopg2
from dotenv import load_dotenv

from .config import (
    GEMINI_MODELS_FALLBACK,
    USE_SCHEMA_PRUNING,
    SCHEMA_PRUNING_TOP_K,
    SCHEMA_FULL_TOP_K,
    MAX_SQL_RETRIES,
)
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


def _send_with_fallback(prompt_to_send: str, chat_session=None) -> tuple[dict, object]:
    """
    Envía el prompt probando cada modelo de la lista de fallback en orden,
    hasta que uno responda exitosamente.

    Si chat_session ya existe (conversación en curso) y el modelo original
    falla, se pierde la continuidad de esa sesión: se crea una nueva sesión
    con el siguiente modelo de la lista. Trade-off aceptado conscientemente:
    preferimos responder con menos contexto que devolver un error crudo.

    Devuelve (respuesta_parseada, chat_session_usada).
    """
    last_exception = None
    session_to_try = chat_session

    for model_name in GEMINI_MODELS_FALLBACK:
        try:
            if session_to_try is None:
                session_to_try = _client.chats.create(model=model_name)
            response = session_to_try.send_message(prompt_to_send, config=_GENERATE_CONFIG)
            return json.loads(response.text), session_to_try
        except genai_errors.ClientError as e:
            # 429 = rate limit/cuota, 404/400 = modelo no existe o fue discontinuado
            last_exception = e
            session_to_try = None  # forzar nueva sesión con el siguiente modelo
            continue

    raise RuntimeError(f"Todos los modelos de fallback fallaron. Último error: {last_exception}")


def run_pipeline(user_prompt: str, chat_session=None) -> dict:
    """
    chat_session: sesión de chat existente (para mantener contexto conversacional
    entre preguntas del usuario, ej. 'top 10' -> 'mejor top 20'). Si es None,
    se crea una nueva (primera pregunta de la sesión).
    """
    schema_injection = _get_schema_injection(user_prompt)

    is_first_message = chat_session is None
    prompt_to_send = (
        build_text_to_sql_prompt(user_prompt, schema_injection)
        if is_first_message
        else build_followup_prompt(user_prompt, schema_injection)
    )

    try:
        parsed, chat_session = _send_with_fallback(prompt_to_send, chat_session)
    except RuntimeError as e:
        return {
            "success": False,
            "answerable": True,
            "sql": None,
            "error": f"No se pudo contactar a ningún modelo disponible. {e}",
            "attempts": 0,
            "chat_session": chat_session,
        }

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
            try:
                parsed, chat_session = _send_with_fallback(retry_prompt, chat_session)
            except RuntimeError as fallback_error:
                return {
                    "success": False,
                    "answerable": True,
                    "sql": sql,
                    "error": f"No se pudo contactar a ningún modelo disponible durante el reintento. {fallback_error}",
                    "attempts": attempt,
                    "chat_session": chat_session,
                }

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