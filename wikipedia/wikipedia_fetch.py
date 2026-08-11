import os
import wikipediaapi
import requests
from dotenv import load_dotenv

load_dotenv()

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