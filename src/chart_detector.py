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


def resolve_chart_type(user_prompt: str, df: pd.DataFrame) -> str | None:
    explicit = detect_explicit_chart_request(user_prompt)
    if explicit == "none":
        return None
    if explicit is not None:
        # Verificación defensiva: si el usuario pidió un tipo de gráfico que
        # no aplica a la forma real del resultado, caemos a la heurística automática.
        if explicit == "line" and not _find_year_column(df):
            return suggest_chart_type(df)
        if explicit == "scatter" and len(df.select_dtypes(include="number").columns) < 2:
            return suggest_chart_type(df)
        return explicit
    return suggest_chart_type(df)


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

def get_chart_columns(df: pd.DataFrame, chart_type: str) -> dict:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()
    year_col = _find_year_column(df)

    # Excluir la columna de año de las candidatas a "valor numérico a graficar"
    non_year_numeric_cols = [c for c in numeric_cols if c != year_col]

    if chart_type == "metric":
        value_col = non_year_numeric_cols[0] if non_year_numeric_cols else numeric_cols[0]
        label_col = text_cols[0] if text_cols else value_col
        return {"value_col": value_col, "label_col": label_col}

    if chart_type == "bar_h":
        return {"category_col": text_cols[0], "value_col": non_year_numeric_cols[0]}

    if chart_type == "line":
        x_col = year_col or df.columns[0]
        y_candidates = non_year_numeric_cols if non_year_numeric_cols else numeric_cols
        y_col = y_candidates[0]
        return {"x_col": x_col, "y_col": y_col}

    if chart_type == "scatter":
        # también excluimos año de los ejes del scatter, no tiene sentido graficar año vs año
        scatter_numeric = non_year_numeric_cols if len(non_year_numeric_cols) >= 2 else numeric_cols
        return {
            "x_col": scatter_numeric[0],
            "y_col": scatter_numeric[1],
            "label_col": text_cols[0] if text_cols else None,
        }

    return {}