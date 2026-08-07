"""
build_corpus.py

Lee los .txt de wikipedia_links/ (uno por categoría), descarga cada artículo
de Wikipedia en español, lo trocea por secciones (respetando la jerarquía de
headers) y guarda un JSON por artículo en corpus/{categoria}/{id}.json

Uso:
    python build_corpus.py                  # procesa todas las categorías
    python build_corpus.py --category teams  # procesa solo una categoría
    python build_corpus.py --dry-run         # muestra qué haría, no descarga
"""

import json
import os
import re
import time
import unicodedata
import argparse
from pathlib import Path
from urllib.parse import unquote, urlparse
from datetime import date
from dotenv import load_dotenv
load_dotenv()  # carga variables de entorno desde .env

import wikipediaapi

LINKS_DIR = Path("wikipedia_links")
CORPUS_DIR = Path("corpus")
USER_AGENT = os.getenv("USER_AGENT")
LANGUAGE = "es"
SLEEP_BETWEEN_REQUESTS = 0.5  # segundos

wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language=LANGUAGE)


def slugify(text: str) -> str:
    """Convierte un título en un id apto para nombre de archivo."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def url_to_title(url: str) -> str:
    """Extrae el título de página de una URL de Wikipedia en español."""
    path = urlparse(url).path  # /wiki/Copa_Mundial_de_F%C3%BAtbol_de_1930
    title = path.split("/wiki/")[-1]
    title = unquote(title)
    title = title.replace("_", " ")
    return title


def flatten_sections(sections, parent_path=None, min_chars=40):
    """
    Recorre recursivamente las secciones de wikipedia-api y las aplana
    en una lista de {header_path: [...], content: "..."}.
    Ignora secciones con muy poco contenido (ej. "Véase también", vacías).
    """
    parent_path = parent_path or []
    flat = []
    # secciones a descartar por ser boilerplate, no contenido real
    SKIP_TITLES = {
        "véase también", "referencias", "enlaces externos",
        "notas", "bibliografía", "fuentes",
        # tournaments: resultados y reconocimientos que ya están en tablas, no son texto útil
        "estadísticas finales", "resultados", "goleadores", "reconocimientos", "premios y reconocimientos",
        "estadísticas"
        # teams: palmarés, jugadores, sponsors, inferiores, etc. que no son contenido útil para RAG
        "palmarés", "jugadores", "plantel", "plantilla",
        "patrocinadores", "transmisión televisiva", "categorías inferiores", "entrenadores", "directores técnicos",
    }
    for section in sections:
        header_path = parent_path + [section.title]
        title_lower = section.title.strip().lower()

        if title_lower not in SKIP_TITLES:
            content = section.text.strip()
            if len(content) >= min_chars:
                flat.append({
                    "header_path": header_path,
                    "content": content,
                })

        # recursión para subsecciones, incluso si la sección padre se descartó
        flat.extend(flatten_sections(section.sections, header_path, min_chars))

    return flat


def fetch_article(url: str, category: str) -> dict | None:
    title = url_to_title(url)
    page = wiki.page(title)

    if not page.exists():
        print(f"  [NO EXISTE] {title} ({url})")
        return None

    sections = []

    # el resumen inicial (antes del primer header) va como sección propia
    if page.summary.strip():
        sections.append({
            "header_path": ["Resumen"],
            "content": page.summary.strip(),
        })

    sections.extend(flatten_sections(page.sections))

    if not sections:
        print(f"  [SIN CONTENIDO] {title}")
        return None

    doc = {
        "id": slugify(page.title),
        "title": page.title,
        "source_url": url,
        "category": category,
        "retrieved_at": date.today().isoformat(),
        "sections": sections,
    }
    return doc


def process_category(category: str, dry_run: bool = False):
    links_file = LINKS_DIR / f"{category}.txt"
    if not links_file.exists():
        print(f"[AVISO] No existe {links_file}, salteando")
        return

    urls = [
        line.strip()
        for line in links_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    out_dir = CORPUS_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {category} ({len(urls)} artículos) ===")

    for url in urls:
        title_preview = url_to_title(url)
        out_path = out_dir / f"{slugify(title_preview)}.json"

        if out_path.exists():
            print(f"  [YA EXISTE] {title_preview}, salteando (borrá el JSON si querés reprocesar)")
            continue

        if dry_run:
            print(f"  [DRY RUN] descargaría: {title_preview} -> {out_path}")
            continue

        print(f"  Descargando: {title_preview}")
        try:
            doc = fetch_article(url, category)
        except Exception as e:
            print(f"  [ERROR] {title_preview}: {e}")
            continue

        if doc is None:
            continue

        out_path.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        n_sections = len(doc["sections"])
        print(f"  [OK] {doc['id']} ({n_sections} secciones) -> {out_path}")

        time.sleep(SLEEP_BETWEEN_REQUESTS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", help="Procesar solo esta categoría (nombre del .txt sin extensión)")
    parser.add_argument("--dry-run", action="store_true", help="No descarga nada, solo muestra qué haría")
    args = parser.parse_args()

    if args.category:
        process_category(args.category, dry_run=args.dry_run)
    else:
        categories = [f.stem for f in sorted(LINKS_DIR.glob("*.txt"))]
        for category in categories:
            process_category(category, dry_run=args.dry_run)

    print("\nListo.")


if __name__ == "__main__":
    main()