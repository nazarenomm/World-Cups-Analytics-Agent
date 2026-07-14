"""
World Cup Analytics Agent — Wikipedia fetcher para corpus de RAG.

Qué hace:
1. Busca un título de artículo en Wikipedia (EN y ES) usando la API de búsqueda
   (más robusto que pedir el título exacto, porque tolera variaciones de nombre).
2. Si encuentra el artículo, baja el contenido completo (texto plano, sin markup).
3. Extrae metadata útil: título, idioma, resumen (primeras líneas), secciones,
   categorías, y URL.
4. Guarda todo como JSON por evento, con un doc por idioma disponible.

Uso:
    python wiki_fetch.py

Requiere: wikipedia-api, requests (pip install wikipedia-api requests --break-system-packages)
"""

import json
import os
import time
from pathlib import Path
import wikipediaapi
import requests
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path("./corpus")
OUTPUT_DIR.mkdir(exist_ok=True)

USER_AGENT = os.getenv("USER_AGENT")

wiki_en = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language="en")
wiki_es = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language="es")


def search_wikipedia_candidates(query: str, lang: str, limit: int = 5) -> list:
    """
    Devuelve varios candidatos (título + snippet) para que el usuario elija,
    en vez de asumir que el primer resultado es el correcto.
    Útil para explorar antes de decidir qué título exacto usar.
    """
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": limit,
    }
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("query", {}).get("search", [])
    return [{"title": r["title"], "snippet": r["snippet"].replace("<span class=\"searchmatch\">", "").replace("</span>", "")} for r in results]


def preview_article(title: str, lang: str):
    """
    Trae un artículo por TÍTULO EXACTO (el que vos ya identificaste, ej. copiado
    de la URL de Wikipedia) y devuelve un preview para que decidas si es el correcto
    antes de guardarlo. No escribe nada a disco.
    """
    wiki = wiki_en if lang == "en" else wiki_es
    page = wiki.page(title)
    if not page.exists():
        print(f"  No existe el artículo '{title}' en {lang}.wikipedia.org")
        return None

    doc = {
        "lang": lang,
        "title": page.title,
        "url": page.fullurl,
        "summary": page.summary,
        "text": page.text
    }

    print(f"Título: {doc['title']}")
    print(f"URL: {doc['url']}")
    print(f"\nResumen:\n{doc['summary'][:800]}...")
    return doc


def fetch_article(query: str, lang: str):
    """Búsqueda automática simple (fallback, no recomendado para artículos ambiguos)."""
    candidates = search_wikipedia_candidates(query, lang, limit=1)
    if not candidates:
        return None
    return preview_article(candidates[0]["title"], lang)


def save_doc(doc: dict, event_id: str, output_dir: Path = OUTPUT_DIR):
    """
    Guarda UN doc (un idioma) dentro del JSON del evento. Si el evento ya tiene
    un archivo con otro idioma guardado previamente, lo agrega sin pisarlo.
    """
    out_path = output_dir / f"{event_id}.json"
    if out_path.exists():
        result = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        result = {"event_id": event_id, "docs": []}

    # Evita duplicar el mismo idioma dos veces (lo reemplaza si ya existía)
    result["docs"] = [d for d in result["docs"] if d["lang"] != doc["lang"]]
    result["docs"].append(doc)

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado en {out_path} (idiomas ahora: {[d['lang'] for d in result['docs']]})")


# --------------------------------------------------------------------------
# FLUJO MANUAL RECOMENDADO (para usar en Jupyter, celda por celda):
#
# 1. Buscás candidatos si no estás seguro del título exacto:
#
#     candidates = search_wikipedia_candidates("Zidane headbutt", lang="en")
#     for c in candidates:
#         print(c["title"], "-", c["snippet"][:100])
#
# 2. Una vez que tenés el título exacto (ya sea de la búsqueda de arriba,
#    o copiado directo de la URL de Wikipedia que viste en el navegador),
#    lo previsualizás SIN guardar nada todavía:
#
#     doc = preview_article("Zinedine Zidane headbutt incident", lang="en")
#
# 3. Revisás el preview impreso (resumen, secciones, longitud). Si es el
#    artículo correcto, lo guardás:
#
#     save_doc(doc, event_id="zidane_headbutt_2006")
#
# 4. Repetís el paso 2-3 para el otro idioma:
#
#     doc_es = preview_article("Cabezazo de Zidane a Materazzi", lang="es")
#     save_doc(doc_es, event_id="zidane_headbutt_2006")
#
# Si preview_article dice que el artículo no existe, probá variantes del
# título (con/sin guiones bajos, con/sin desambiguación entre paréntesis,
# etc.) o volvé al paso 1 para buscar candidatos.
# --------------------------------------------------------------------------