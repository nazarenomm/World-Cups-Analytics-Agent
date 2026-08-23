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
from .schema_pruning import get_relevant_tables, get_all_tables
from .db import execute_query, UnsafeQueryError

load_dotenv()

_GENERATE_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=RESPONSE_SCHEMA,
)


def _get_schema_injection(user_prompt: str) -> str:
    if USE_SCHEMA_PRUNING:
        relevant = get_relevant_tables(user_prompt, top_k=SCHEMA_PRUNING_TOP_K)
    else:
        relevant = get_all_tables()
    return format_schema_for_prompt(relevant)


def _send_with_fallback(prompt_to_send: str, history: list[dict] | None = None) -> tuple[dict, list[dict]]:
    """
    history: lista de mensajes previos [{"role": "user"/"model", "parts": [...]}]
    en vez de un objeto chat_session vivo. Se reconstruye un client + chat
    frescos en cada llamada, evitando reusar transporte httpx potencialmente cerrado.
    """
    last_exception = None
    history = history or []

    for model_name in GEMINI_MODELS_FALLBACK:
        try:
            client = genai.Client(api_key=os.environ["GOOGLE_KEY"])  # cliente nuevo, sin estado viejo
            chat = client.chats.create(model=model_name, history=history)
            response = chat.send_message(prompt_to_send, config=_GENERATE_CONFIG)
            new_history = chat.get_history()  # lista serializable de Content
            return json.loads(response.text), new_history
        except (genai_errors.ClientError, genai_errors.ServerError) as e:
            last_exception = e
            continue

    raise RuntimeError(f"Todos los modelos de fallback fallaron. Último error: {last_exception}")

def run_pipeline(user_prompt: str, history: list | None = None) -> dict:
    """
    history: historial de mensajes previos (lista serializable), para mantener
    contexto conversacional entre preguntas del usuario, ej. 'top 10' -> 'mejor top 20'.
    Si es None, es la primera pregunta de la sesión.
    """
    schema_injection = _get_schema_injection(user_prompt)

    is_first_message = history is None
    prompt_to_send = (
        build_text_to_sql_prompt(user_prompt, schema_injection)
        if is_first_message
        else build_followup_prompt(user_prompt, schema_injection)
    )

    try:
        parsed, history = _send_with_fallback(prompt_to_send, history)
    except RuntimeError as e:
        return {
            "success": False,
            "answerable": True,
            "sql": None,
            "error": f"No se pudo contactar a ningún modelo disponible. {e}",
            "attempts": 0,
            "history": history,
        }

    if not parsed.get("answerable", False):
        return {
            "success": False,
            "answerable": False,
            "reason": parsed.get("reason", "No se pudo determinar el motivo."),
            "sql": None,
            "attempts": 1,
            "history": history,
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
                "history": history,
                "llm_chart_type": parsed.get("chart_type", "none"),
                "llm_chart_color_by": parsed.get("chart_color_by", "") or None,
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
                parsed, history = _send_with_fallback(retry_prompt, history)
            except RuntimeError as fallback_error:
                return {
                    "success": False,
                    "answerable": True,
                    "sql": sql,
                    "error": f"No se pudo contactar a ningún modelo disponible durante el reintento. {fallback_error}",
                    "attempts": attempt,
                    "history": history,
                }

            if not parsed.get("answerable", False):
                return {
                    "success": False,
                    "answerable": False,
                    "reason": parsed.get("reason", "No se pudo determinar el motivo."),
                    "sql": sql,
                    "attempts": attempt,
                    "history": history,
                }
            sql = parsed["sql_query"].strip()

    return {
        "success": False,
        "answerable": True,  # era respondible, pero falló técnicamente tras los reintentos
        "sql": sql,
        "error": last_error,
        "attempts": attempt,
        "history": history,
    }


if __name__ == "__main__":
    result = run_pipeline("¿Cuántas asistencias dio Messi en mundiales?")
    print(result)