"""
Genera una consulta SQL a partir de un prompt en lenguaje natural,
usando Gemini y el schema injection (podado o completo según config).
"""
import os
from google import genai
from dotenv import load_dotenv

from .config import USE_SCHEMA_PRUNING, GEMINI_MODEL, SCHEMA_PRUNING_TOP_K, SCHEMA_FULL_TOP_K
from .prompts import build_text_to_sql_prompt
from .schema_format import format_schema_for_prompt
from .schema_pruning import get_relevant_tables

load_dotenv()

_client = genai.Client(api_key=os.environ["GOOGLE_KEY"])


def _get_schema_injection(user_prompt: str) -> str:
    top_k = SCHEMA_PRUNING_TOP_K if USE_SCHEMA_PRUNING else SCHEMA_FULL_TOP_K
    relevant = get_relevant_tables(user_prompt, top_k=top_k)
    return format_schema_for_prompt(relevant)


def generate_sql(user_prompt: str) -> str:
    """
    Devuelve el texto de la consulta SQL generada por el LLM para el prompt dado.
    No ejecuta la query ni valida sintaxis — eso es responsabilidad de la capa
    de ejecución (ver src/db.py, próximo paso).
    """
    schema_injection = _get_schema_injection(user_prompt)
    full_prompt = build_text_to_sql_prompt(user_prompt, schema_injection)

    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=full_prompt,
    )
    return response.text.strip()


if __name__ == "__main__":
    test_prompt = "¿Cuántos goles hizo Messi en el mundial 2022?"
    sql = generate_sql(test_prompt)
    print(f"Prompt: {test_prompt}\n\nSQL generado:\n{sql}")