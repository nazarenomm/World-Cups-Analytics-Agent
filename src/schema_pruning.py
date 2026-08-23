"""
Dado un prompt de usuario, devuelve las top-k tablas/vistas más relevantes
del schema, junto con su metadata completa de columnas para el schema injection.
"""
import json
import pickle
from pathlib import Path
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "schema_metadata.json"
CACHE_PATH = Path(__file__).parent.parent / "schema" / "schema_embeddings_cache.pkl"
MODEL_PATH = Path(__file__).parent.parent / "schema" / "local_model"


@lru_cache(maxsize=1)
def _load_schema_metadata():
    """Carga solo la metadata del schema (JSON). Liviano, siempre necesario."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    return {t["name"]: t for t in schema["tables"]}


@lru_cache(maxsize=1)
def _load_resources():
    """
    Carga schema, embeddings y modelo una sola vez (cacheado en memoria).
    Solo se llama cuando USE_SCHEMA_PRUNING=True — requiere el modelo local
    de sentence-transformers disponible en el filesystem.
    """
    tables_by_name = _load_schema_metadata()

    with open(CACHE_PATH, "rb") as f:
        cache = pickle.load(f)

    model = SentenceTransformer(str(MODEL_PATH))  # local, sin token

    return {
        "tables_by_name": tables_by_name,
        "table_names": cache["table_names"],
        "embeddings": cache["embeddings"],
        "model": model,
    }


def _cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    query_norm = query_vec / np.linalg.norm(query_vec)
    matrix_norm = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix_norm @ query_norm


def get_relevant_tables(user_prompt: str, top_k: int = 4) -> list[dict]:
    """
    Devuelve la metadata completa (incluyendo columnas) de las top_k tablas/vistas
    más relevantes para el prompt del usuario, según similitud de embeddings.

    Con top_k = total de tablas, devuelve efectivamente el schema completo
    (usado cuando USE_SCHEMA_PRUNING=False), ordenado por similitud pero sin filtrar.
    """
    resources = _load_resources()

    query_vec = resources["model"].encode(user_prompt, convert_to_numpy=True)
    similarities = _cosine_similarity(query_vec, resources["embeddings"])

    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        table_name = resources["table_names"][idx]
        table_meta = resources["tables_by_name"][table_name]
        results.append({
            "name": table_name,
            "similarity": float(similarities[idx]),
            "metadata": table_meta,
        })

    return results


def get_all_tables() -> list[dict]:
    """
    Devuelve la metadata completa de todas las tablas/vistas, sin embeddings
    ni cálculo de similitud. Usado cuando USE_SCHEMA_PRUNING=False, evitando
    cargar el modelo de sentence-transformers en producción.
    """
    tables_by_name = _load_schema_metadata()

    return [
        {"name": name, "similarity": None, "metadata": meta}
        for name, meta in tables_by_name.items()
    ]

if __name__ == "__main__":
    from schema_format import format_schema_for_prompt

    prompt = "¿Cuántos goles hizo Messi en el mundial 2022?"
    relevant = get_relevant_tables(prompt, top_k=4)

    print(f"Prompt: {prompt}\n")
    for r in relevant:
        print(f"  {r['name']}  (similarity={r['similarity']:.3f})")

    print("\n--- Schema injection ---\n")
    print(format_schema_for_prompt(relevant))