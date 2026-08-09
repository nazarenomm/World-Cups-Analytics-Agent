"""
Lee chunks_embeddings_cache.pkl (generado por compute_chunks_embeddings.py) y carga
los chunks a la tabla rag_chunks en Supabase via supabase-py.
"""

import os
import pickle
from pathlib import Path
from dotenv import load_dotenv

from supabase import create_client

load_dotenv()

INPUT_PATH = Path("chunks_embeddings_cache.pkl")
BATCH_SIZE = 50  # inserts en lotes

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]


def main():
    with open(INPUT_PATH, "rb") as f:
        chunks = pickle.load(f)

    print(f"Cargando {len(chunks)} chunks a Supabase...")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    rows = [
        {
            "parent_doc_id": c["parent_doc_id"],
            "parent_title": c["parent_title"],
            "category": c["category"],
            "source_url": c["source_url"],
            "header_path": c["header_path"],
            "part": c["part"],
            "content": c["content"],
            "embedding": c["embedding"],
        }
        for c in chunks
    ]

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        client.table("rag_chunks").insert(batch).execute()
        print(f"  Insertado batch {i // BATCH_SIZE + 1} ({len(batch)} filas)")

    print("Listo.")


if __name__ == "__main__":
    main()