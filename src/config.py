USE_SCHEMA_PRUNING = False
SCHEMA_PRUNING_TOP_K = 4
SCHEMA_FULL_TOP_K = 33  # total de tablas + vistas
MAX_SQL_RETRIES = 3
GEMINI_MODELS_FALLBACK = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash" # generalmente está saturado, pero lo dejo como fallback por si acaso
]
QUERY_PREFIX = "query: " # prefijo obligatorio para queries en retrieval asimétrico
