"""
Script para precalcular los embeddings de las descripciones de tablas/vistas.
Correr una sola vez (o cada vez que se edite schema_metadata.json).
"""
import json
import os
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "schema_metadata.json"
CACHE_PATH = Path(__file__).parent.parent / "schema" / "embeddings_cache.pkl"

MODEL_PATH = Path(__file__).parent.parent / "schema" / "local_model"


def build_embedding_text(table: dict) -> str:
    """
    Arma el texto que se va a vectorizar para cada tabla/vista.
    Combina description + example_questions, porque las preguntas de ejemplo
    suelen matchear mejor contra prompts reales de usuario que la descripción sola.
    """
    parts = [table["description"]]
    parts.extend(table.get("example_questions", []))
    return " ".join(parts)


def main():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    model = SentenceTransformer(str(MODEL_PATH))

    table_names = []
    texts = []
    for table in schema["tables"]:
        table_names.append(table["name"])
        texts.append(build_embedding_text(table))

    print(f"Calculando embeddings para {len(table_names)} tablas/vistas...")
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

    cache = {
        "table_names": table_names,
        "embeddings": embeddings
    }

    with open(CACHE_PATH, "wb") as f:
        pickle.dump(cache, f)

    print(f"Embeddings guardados en {CACHE_PATH}")


if __name__ == "__main__":
    main()