"""
Recorre corpus/, arma un chunk por sección (con splitting o merging simple para
tamaños extremos), calcula embeddings con sentence-transformers y guarda
todo en un pickle local (chunks + vectores) para revisión antes de subir
a Supabase.
"""

import json
import pickle
from pathlib import Path
import re
from sentence_transformers import SentenceTransformer


CORPUS_DIR = Path("corpus")
OUTPUT_PATH = Path("chunks_embeddings_cache.pkl")

MODEL_PATH = Path(__file__).parent.parent / "schema" / "local_model"

EMBEDDING_DIM = 768

PASSAGE_PREFIX = "passage: " # prefijo obligatorio para chunks en retrieval asimétrico

MIN_WORDS = 15    # por debajo de esto, se fusiona con la sección siguiente
MAX_WORDS = 350   # por encima, se corta en sub-chunks por oración
OVERLAP_WORDS = 50  # palabras de solapamiento entre sub-chunks consecutivos


def split_long_section(content: str, max_words: int, overlap_words: int) -> list[str]:
    """
    Corta una sección larga en sub-chunks con overlap, trabajando a nivel de
    oración (no párrafo) para no cortar en medio de una idea. Muchas secciones
    largas de Wikipedia (ej. "Historia") vienen como pocos párrafos gigantes,
    así que particionar solo por párrafo no alcanza.
    """
    # split simple por oración: punto/exclamación/interrogación + espacio + mayúscula
    
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])", content.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [content]

    chunks = []
    current = []
    current_len = 0

    for sent in sentences:
        s_len = len(sent.split())

        if current and current_len + s_len > max_words:
            chunks.append(" ".join(current))
            # tomar las últimas ~overlap_words palabras del chunk anterior, para no perder contexto en el corte
            overlap_text = " ".join(" ".join(current).split()[-overlap_words:])
            current = [overlap_text] if overlap_text else []
            current_len = len(overlap_text.split())

        current.append(sent)
        current_len += s_len

    if current:
        chunks.append(" ".join(current))

    return chunks if chunks else [content]


def build_chunks():
    """Recorre el corpus y arma la lista final de chunks."""
    chunks = []

    for json_file in sorted(CORPUS_DIR.rglob("*.json")):
        doc = json.loads(json_file.read_text(encoding="utf-8"))
        pending_short = None  # buffer para fusionar secciones cortas

        for section in doc["sections"]:
            content = section["content"]
            n_words = len(content.split())
            header_path = section["header_path"]

            # fusionar sección corta con la siguiente
            if pending_short is not None:
                content = pending_short["content"] + " " + content
                header_path = pending_short["header_path"]  # conserva el header más específico previo
                n_words = len(content.split())
                pending_short = None

            if n_words < MIN_WORDS:
                pending_short = {"content": content, "header_path": header_path}
                continue

            if n_words > MAX_WORDS:
                sub_chunks = split_long_section(content, MAX_WORDS, OVERLAP_WORDS)
                for i, sub in enumerate(sub_chunks):
                    chunks.append({
                        "parent_doc_id": doc["id"],
                        "parent_title": doc["title"],
                        "category": doc["category"],
                        "source_url": doc["source_url"],
                        "header_path": header_path,
                        "part": i + 1 if len(sub_chunks) > 1 else None,
                        "content": sub,
                    })
            else:
                chunks.append({
                    "parent_doc_id": doc["id"],
                    "parent_title": doc["title"],
                    "category": doc["category"],
                    "source_url": doc["source_url"],
                    "header_path": header_path,
                    "part": None,
                    "content": content,
                })

        # si quedó un remanente corto sin fusionar al final del doc, se agrega igual
        if pending_short is not None:
            chunks.append({
                "parent_doc_id": doc["id"],
                "parent_title": doc["title"],
                "category": doc["category"],
                "source_url": doc["source_url"],
                "header_path": pending_short["header_path"],
                "part": None,
                "content": pending_short["content"],
            })

    return chunks


def main():
    print("Armando chunks desde corpus/...")
    chunks = build_chunks()
    print(f"Total chunks: {len(chunks)}")

    print(f"Cargando modelo...")
    model = SentenceTransformer(str(MODEL_PATH))

    texts = [c["content"] for c in chunks]
    print("Calculando embeddings...")
    embeddings = model.encode(
        [PASSAGE_PREFIX + t for t in texts],
        show_progress_bar=True,
        batch_size=32,
    )

    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb.tolist()

    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(chunks, f)

    print(f"\nGuardado en {OUTPUT_PATH} ({len(chunks)} chunks, dim={len(embeddings[0])})")

if __name__ == "__main__":
    main()