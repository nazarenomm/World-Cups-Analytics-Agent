"""
Módulo de retrieval para el pipeline RAG. Embeddea la query del usuario con
el prefijo correcto para el modelo E5 (retrieval asimétrico) y llama a la
función match_chunks en Supabase.
"""

import os
from pathlib import Path

from sentence_transformers import SentenceTransformer
from supabase import create_client

from dotenv import load_dotenv

from .config import TOP_K_CHUNKS

load_dotenv()

MODEL_PATH = Path(__file__).parent.parent / "schema" / "local_model"

QUERY_PREFIX = "query: "

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

_model = None
_client = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(str(MODEL_PATH))
    return _model


def get_client():
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client



def retrieve(query: str, top_k: int = TOP_K_CHUNKS, category: str | None = None) -> list[dict]:
    """
    Dada una pregunta, devuelve los top_k chunks más relevantes.

    Args:
        query: pregunta del usuario, texto plano sin prefijo.
        top_k: cantidad de chunks a devolver.
        category: si se especifica, filtra por categoría (confederations,
                   editions, famous_matches, stadiums, teams, etc.)

    Returns:
        Lista de dicts con: id, parent_title, category, source_url,
        header_path, content, similarity.
    """
    model = get_model()
    client = get_client()

    query_embedding = model.encode(QUERY_PREFIX + query).tolist()

    result = client.rpc("match_chunks", {
        "query_embedding": query_embedding,
        "match_count": top_k,
        "filter_category": category,
    }).execute()

    return result.data


if __name__ == "__main__":
    test_queries = [
        # "¿Por qué no se jugaron mundiales entre 1930 y 1950?",
        # "¿Qué selecciones rechazaron jugar un mundial?",
        # "¿Cuáles fueron las repercusiones del Maracanazo?",
        # "¿Por qué Uruguay se negó a jugar un mundial?",
        # "¿En qué fase fue el gol del siglo?",
        # "¿En qué fase Maradona marcó el gol del siglo?",
        # preguntas de prueba para RAG: sin similaridad
        "¿Cuál es la capital de Francia?",
        "¿Quién es el presidente de Estados Unidos?",
        "¿Cuál es la población de China?",
        "¿Cómo se juega al ajedrez?",
        "¿Cuantos Emmys ganó Breaking Bad?",
        "¿Quién escribió 'Cien años de soledad'?",
    ]

    for q in test_queries:
        print(f"\n{'='*70}\nQuery: {q}")
        chunks = retrieve(q, top_k=5)
        for i, c in enumerate(chunks, 1):
            header = " > ".join(c["header_path"])
            preview = c["content"][:100].replace("\n", " ")
            print(f"  {i}. [{c['similarity']:.3f}] {c['parent_title']} > {header}")
            print(f"     {preview}...")