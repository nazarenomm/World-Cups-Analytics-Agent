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

_GENERATE_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=RESPONSE_SCHEMA,
)


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

def run_rag_pipeline(user_prompt: str, history: list | None = None, category: str | None = None) -> dict:
    """
    history: historial de mensajes previos (lista serializable), para mantener
    contexto conversacional entre preguntas. Si es None, es la primera pregunta.
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
            "history": history,
        }

    is_first_message = history is None
    prompt_to_send = (
        build_rag_prompt(user_prompt, chunks)
        if is_first_message
        else build_rag_followup_prompt(user_prompt, chunks)
    )

    try:
        parsed, history = _send_with_fallback(prompt_to_send, history)
    except RuntimeError as e:
        return {
            "success": False,
            "answerable": True,
            "answer": None,
            "error": f"No se pudo contactar a ningún modelo disponible. {e}",
            "cited_sources": [],
            "attempts": 0,
            "history": history,
        }

    if not parsed.get("answerable", False):
        return {
            "success": False,
            "answerable": False,
            "reason": parsed.get("reason", "No se pudo determinar el motivo."),
            "answer": None,
            "cited_sources": [],
            "attempts": 1,
            "history": history,
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
        "history": history,
    }


if __name__ == "__main__":
    result = run_rag_pipeline("¿Por qué Uruguay se negó a jugar el mundial de 1934?")
    print(result)