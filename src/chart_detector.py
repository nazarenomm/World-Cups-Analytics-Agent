"""
Heurística (sin LLM) para decidir si y qué tipo de gráfico mostrar
según el prompt del usuario y la forma del resultado de la query.
"""
import pandas as pd


def detect_explicit_chart_request(user_prompt: str) -> str | None:
    prompt_lower = user_prompt.lower()

    if any(kw in prompt_lower for kw in ["sin gráfico", "sin grafico", "solo tabla", "solo la tabla"]):
        return "none"
    if any(kw in prompt_lower for kw in ["gráfico de barras", "grafico de barras", "bar chart", "barras"]):
        return "bar_h"
    if any(kw in prompt_lower for kw in ["gráfico de línea", "grafico de linea", "evolución", "evolucion", "a lo largo del tiempo", "por año", "por mundial", "por edición", "por edicion"]):
        return "line"
    if any(kw in prompt_lower for kw in ["scatter", "dispersión", "dispersion", "correlación", "correlacion"]):
        return "scatter"

    return None


def suggest_chart_type(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None

    n_rows = len(df)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()

    # 1 sola fila con al menos un valor numérico -> métrica destacada,
    # sin importar cuántas columnas de texto acompañen (ej. nombre + goles)
    if n_rows == 1 and numeric_cols:
        return "metric"

    if not numeric_cols:
        return None

    year_like_cols = _find_year_column(df)
    if year_like_cols:
        return "line"

    if text_cols and n_rows <= 30:
        return "bar_h"

    if len(numeric_cols) >= 2 and not text_cols:
        return "scatter"

    return None


def resolve_chart_type(
    user_prompt: str,
    df: pd.DataFrame,
    llm_suggestion: str | None = None,
) -> str | None:
    """
    Prioridad: pedido explícito del usuario (keyword) > sugerencia del LLM
    (si es válida para la forma real del resultado) > heurística automática.
    """
    explicit = detect_explicit_chart_request(user_prompt)
    if explicit == "none":
        return None
    if explicit is not None:
        if _chart_type_fits_data(explicit, df):
            return explicit
        return suggest_chart_type(df)

    if llm_suggestion and llm_suggestion != "none":
        if _chart_type_fits_data(llm_suggestion, df):
            return llm_suggestion
        # el LLM sugirió algo que no calza con los datos reales -> fallback a heurística
        return suggest_chart_type(df)

    if llm_suggestion == "none":
        return None  # el LLM decidió explícitamente que no aporta un gráfico

    return suggest_chart_type(df)


def _chart_type_fits_data(chart_type: str, df: pd.DataFrame) -> bool:
    """Valida que el tipo de gráfico propuesto sea técnicamente viable con este resultado."""
    if df.empty:
        return False

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()

    if chart_type == "metric":
        return len(df) == 1 and bool(numeric_cols)
    if chart_type == "bar_h":
        return bool(text_cols) and bool(numeric_cols)
    if chart_type == "line":
        return bool(_find_year_column(df)) and bool(numeric_cols)
    if chart_type == "scatter":
        return len(numeric_cols) >= 2

    return False

def _find_year_column(df: pd.DataFrame) -> str | None:
    """Busca una columna que represente año/edición, devuelve su nombre real (no hardcodeado)."""
    candidates = [c for c in df.columns if any(kw in c.lower() for kw in ["year", "año", "anio", "tournament_year"])]
    return candidates[0] if candidates else None


def normalize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza los tipos de columna que vienen de psycopg2/Postgres para que
    pandas los reconozca correctamente como numéricos o texto.
    - Decimal (NUMERIC/SUM) llega como dtype object -> convertir a numérico si aplica.
    - StringDtype -> convertir a object estándar para que select_dtypes(include="object") lo capture.
    """
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue  # ya es numérico, no tocar

        # Intentar convertir a numérico (captura Decimal, y strings que son números)
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() == df[col].notna().sum():
            # Se pudo convertir sin perder datos válidos -> es realmente numérica
            df[col] = converted
        else:
            # No es numérica, asegurar que quede como object estándar
            df[col] = df[col].astype(object)

    return df

def get_chart_columns(df: pd.DataFrame, chart_type: str, color_by: str | None = None) -> dict:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()
    year_col = _find_year_column(df)
    non_year_numeric_cols = [c for c in numeric_cols if c != year_col]

    # Validar que la columna de color exista realmente en el resultado (por si el LLM alucina)
    valid_color_by = color_by if color_by in df.columns else None

    if chart_type == "metric":
        value_col = non_year_numeric_cols[0] if non_year_numeric_cols else numeric_cols[0]
        label_col = text_cols[0] if text_cols else value_col
        return {"value_col": value_col, "label_col": label_col}

    if chart_type == "bar_h":
        return {
            "category_col": text_cols[0],
            "value_col": non_year_numeric_cols[0],
            "color_col": valid_color_by,
        }

    if chart_type == "line":
        x_col = year_col or df.columns[0]
        y_col = (non_year_numeric_cols or numeric_cols)[0]
        return {"x_col": x_col, "y_col": y_col, "color_col": valid_color_by}

    if chart_type == "scatter":
        scatter_numeric = non_year_numeric_cols if len(non_year_numeric_cols) >= 2 else numeric_cols
        return {
            "x_col": scatter_numeric[0],
            "y_col": scatter_numeric[1],
            "label_col": text_cols[0] if text_cols else None,
            "color_col": valid_color_by,
        }

    return {}