USE_SCHEMA_PRUNING = False
SCHEMA_PRUNING_TOP_K = 4
SCHEMA_FULL_TOP_K = 33  # total de tablas + vistas
MAX_SQL_RETRIES = 3
GEMINI_MODELS_FALLBACK = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",       # último recurso, por si el 3.x tiene problemas puntuales
]