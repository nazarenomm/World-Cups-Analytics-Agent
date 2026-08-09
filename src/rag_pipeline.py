"""
Orquesta el flujo RAG: prompt del usuario -> retrieval de chunks -> prompt con
fuentes -> respuesta de Gemini citando fuentes. Simétrico a pipeline.py (SQL),
mismo patrón de fallback multi-modelo y manejo de answerable.
"""
import os
import json
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from dotenv import load_dotenv

from .config import GEMINI_MODELS_FALLBACK, TOP_K_CHUNKS
from .rag_prompts import build_rag_prompt, build_rag_followup_prompt, RESPONSE_SCHEMA
from .retrieval import retrieve

load_dotenv()

_client = genai.Client(api_key=os.environ["GOOGLE_KEY"])

_GENERATE_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=RESPONSE_SCHEMA,
)


def _send_with_fallback(prompt_to_send: str, chat_session=None) -> tuple[dict, object]:
    """
    Envía el prompt probando cada modelo de la lista de fallback en orden,
    hasta que uno responda exitosamente.

    Idéntico al de pipeline.py (SQL). Se duplica en vez de compartir porque
    cada pipeline usa su propio RESPONSE_SCHEMA en _GENERATE_CONFIG.
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
            last_exception = e
            session_to_try = None
            continue

    raise RuntimeError(f"Todos los modelos de fallback fallaron. Último error: {last_exception}")


def run_rag_pipeline(user_prompt: str, chat_session=None, category: str | None = None) -> dict:
    """
    chat_session: sesión de chat existente (para mantener contexto conversacional
    entre preguntas). Si es None, se crea una nueva (primera pregunta de la sesión).
    category: filtro opcional de categoría para el retrieval (confederations,
              editions, famous_matches, stadiums, teams, etc.)
    """
    chunks = retrieve(user_prompt, top_k=TOP_K_CHUNKS, category=category)

    # Sin fuentes recuperadas (corpus vacío para el filtro, o falla de conexión):
    # cortar antes de gastar un call al LLM, no tiene sentido mandarle un prompt sin contexto.
    if not chunks:
        return {
            "success": False,
            "answerable": False,
            "reason": "No se encontraron fuentes relevantes para esta consulta.",
            "answer": None,
            "cited_sources": [],
            "attempts": 0,
            "chat_session": chat_session,
        }

    is_first_message = chat_session is None
    prompt_to_send = (
        build_rag_prompt(user_prompt, chunks)
        if is_first_message
        else build_rag_followup_prompt(user_prompt, chunks)
    )

    try:
        parsed, chat_session = _send_with_fallback(prompt_to_send, chat_session)
    except RuntimeError as e:
        return {
            "success": False,
            "answerable": True,
            "answer": None,
            "error": f"No se pudo contactar a ningún modelo disponible. {e}",
            "cited_sources": [],
            "attempts": 0,
            "chat_session": chat_session,
        }

    if not parsed.get("answerable", False):
        return {
            "success": False,
            "answerable": False,
            "reason": parsed.get("reason", "No se pudo determinar el motivo."),
            "answer": None,
            "cited_sources": [],
            "attempts": 1,
            "chat_session": chat_session,
        }

    # mapear los índices de sources_used -> chunks reales (título + URL) para que la UI pueda mostrar links
    sources_used = parsed.get("sources_used", [])
    cited_sources = [
        {
            "n": i,
            "title": chunks[i - 1]["parent_title"],
            "url": chunks[i - 1]["source_url"],
            "header_path": chunks[i - 1]["header_path"],
        }
        for i in sources_used
        if 1 <= i <= len(chunks)
    ]

    return {
        "success": True,
        "answerable": True,
        "answer": parsed["answer"],
        "cited_sources": cited_sources,
        "attempts": 1,
        "chat_session": chat_session,
    }


if __name__ == "__main__":
    result = run_rag_pipeline("¿Por qué Uruguay se negó a jugar el mundial de 1934?")
    print(result)