import streamlit as st
import pandas as pd
import plotly.express as px
import sqlparse
import plotly.io as pio
pio.templates.default = "presentation"

from src import run_pipeline, resolve_chart_type, get_chart_columns, normalize_dtypes, run_rag_pipeline

def format_sql_for_display(sql: str) -> str:
    return sqlparse.format(sql, reindent=True, keyword_case="upper")

st.set_page_config(page_title="World Cup Analytics Agent", layout="wide")
st.title("World Cup Analytics Agent")
st.caption("#### Pregunta lo que quieras sobre los Mundiales de fútbol (1930 a 2022).  \n"
"Selecciona el modo de consulta que prefieras en la barra lateral:  \n"
"- Estadísticas, Tablas y Gráficos (SQL): preguntas sobre estadísticas, para explorar/descargar gráficos y tablas  \n"
"- Historia y Contexto (RAG): para consultas históricas o contextuales") # TODO: expandir, explicar que hay dos modos: SQL y RAG, y que se puede cambiar en la barra lateral.

# --- Estado de sesión ---
# Dos chat_session separadas: cada pipeline mantiene su propia conversación con Gemini.
if "sql_chat_session" not in st.session_state:
    st.session_state.sql_chat_session = None

if "rag_chat_session" not in st.session_state:
    st.session_state.rag_chat_session = None

if "messages" not in st.session_state:
    st.session_state.messages = []  # lista de dicts: {role, content, mode, sql?/df?/sources?}

if "mode" not in st.session_state:
    st.session_state.mode = "Estadísticas, Tablas y Gráficos (SQL)"

# --- Sidebar: selector de modo + nuevo chat ---
with st.sidebar:
    st.header("Opciones")
    st.session_state.mode = st.radio(
        "Modo de consulta",
        options=["Estadísticas, Tablas y Gráficos (SQL)", "Historia y Contexto (RAG)"],
        index=0 if st.session_state.mode == "Estadísticas, Tablas y Gráficos (SQL)" else 1,
        help=(
            "SQL: preguntas numéricas/estadísticas (rankings, totales, comparaciones).\n RAG: preguntas históricas o contextuales (por qué, cómo, repercusiones)."
        ),
    )
    if st.button("🔄 Nueva conversación"):
        st.session_state.sql_chat_session = None
        st.session_state.rag_chat_session = None
        st.session_state.messages = []
        st.rerun()

# --- Render del historial ---
def render_chart(chart_type: str, df: pd.DataFrame, color_by: str | None = None, key: str = None):
    if chart_type is None:
        return

    cols = get_chart_columns(df, chart_type, color_by=color_by)

    if chart_type == "metric":
        label = df.iloc[0][cols["label_col"]] if cols["label_col"] != cols["value_col"] else cols["value_col"]
        st.metric(label=str(label), value=df.iloc[0][cols["value_col"]])
        return

    if chart_type == "bar_h":
        fig = px.bar(
            df, x=cols["value_col"], y=cols["category_col"],
            orientation="h", color=cols["color_col"],
            category_orders={cols["category_col"]: df[cols["category_col"]].tolist()},
        )
        fig.update_layout(
            margin=dict(l=10, r=20, t=20, b=20),
            xaxis_title=cols["value_col"].replace("_", " ").title(),
            yaxis_title=cols["category_col"].replace("_", " ").title())
        st.plotly_chart(fig, use_container_width=True, key=key)
        return

    if chart_type == "bar_v":
        fig = px.bar(
            df, x=cols["category_col"], y=cols["value_col"],
            color=cols["color_col"],
            category_orders={cols["category_col"]: df[cols["category_col"]].tolist()},
        )
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=60),
            xaxis_title=cols["category_col"].replace("_", " ").title(),
            yaxis_title=cols["value_col"].replace("_", " ").title()
        )
        st.plotly_chart(fig, use_container_width=True, key=key)
        return

    if chart_type == "pie":
        fig = px.pie(df, names=cols["category_col"], values=cols["value_col"])
        fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True, key=key)
        return

    if chart_type == "map":
        fig = px.choropleth(
            df,
            locations=cols["category_col"],
            locationmode="country names",
            color=cols["value_col"],
            color_continuous_scale="Cividis",
        )
        fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True, key=key)
        return

    if chart_type == "line":
        if cols["x_col"] not in df.columns:
            st.dataframe(df, use_container_width=True)
            return
        chart_df = df.sort_values(cols["x_col"])
        fig = px.line(chart_df, x=cols["x_col"], y=cols["y_col"], color=cols["color_col"], markers=True)
        fig.update_layout(
            margin=dict(l=40, r=40, t=20, b=40),
            xaxis_title=cols["x_col"].replace("_", " ").title(),
            yaxis_title=cols["y_col"].replace("_", " ").title()
        )
        st.plotly_chart(fig, use_container_width=True, key=key)
        return

    if chart_type == "scatter":
        fig = px.scatter(
            df, x=cols["x_col"], y=cols["y_col"], hover_name=cols["label_col"],
            color=cols["color_col"], text=cols["label_col"] if len(df) <= 15 else None,
        )
        fig.update_traces(marker=dict(size=10), textposition="top center")
        fig.update_layout(
            margin=dict(l=40, r=40, t=40, b=40),
            xaxis_title=cols["x_col"].replace("_", " ").title(),
            yaxis_title=cols["y_col"].replace("_", " ").title()
        )
        st.plotly_chart(fig, use_container_width=True, key=key)
        return


def render_sources(sources: list[dict]):
    if not sources:
        return
    with st.expander(f"Ver fuentes citadas ({len(sources)})"):
        for s in sources:
            header = " > ".join(s["header_path"]) if s.get("header_path") else ""
            st.markdown(f"**[Fuente {s['n']}]** [{s['title']}]({s['url']})  \n_{header}_")


for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("df") is not None:
            if msg.get("chart_type"):
                render_chart(msg["chart_type"], msg["df"], color_by=msg.get("chart_color_by"), key=f"chart_history_{i}")
            with st.expander("Ver tabla de resultados"):
                st.dataframe(msg["df"], use_container_width=True)
        if msg.get("sql"):
            with st.expander("Ver consulta SQL generada"):
                st.code(format_sql_for_display(msg["sql"]), language="sql")
        if msg.get("sources"):
            render_sources(msg["sources"])

# --- Input del usuario ---
placeholder = (
    "Ej: Dame el top 10 goleadores de la historia de los mundiales"
    if st.session_state.mode == "Estadísticas, Tablas y Gráficos (SQL)"
    else "Ej: ¿Qué fue el Maracanazo?"
)
user_prompt = st.chat_input(placeholder)

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):

        # ============================================================
        # MODO SQL
        # ============================================================
        if st.session_state.mode == "Estadísticas, Tablas y Gráficos (SQL)":
            with st.spinner("Consultando base de datos..."):
                result = run_pipeline(user_prompt, chat_session=st.session_state.sql_chat_session)

            st.session_state.sql_chat_session = result["chat_session"]

            if result["success"]:
                df = pd.DataFrame(result["rows"], columns=result["columns"])
                df = normalize_dtypes(df)
                chart_type = resolve_chart_type(user_prompt, df, llm_suggestion=result.get("llm_chart_type"))
                color_by = result.get("llm_chart_color_by")

                response_text = f"Encontré {len(df)} fila(s)."
                st.markdown(response_text)
                render_chart(chart_type, df, color_by=color_by, key=f"chart_new_{len(st.session_state.messages)}")

                with st.expander("Ver tabla de resultados"):
                    st.dataframe(df, use_container_width=True)
                with st.expander("Ver consulta SQL generada"):
                    st.code(format_sql_for_display(result["sql"]), language="sql")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "df": df,
                    "chart_type": chart_type,
                    "sql": result["sql"],
                    "chart_color_by": color_by,
                })

            elif not result.get("answerable", True):
                warning_text = f"No tengo esa información disponible. {result['reason']}"
                st.warning(warning_text)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": warning_text,
                })

            else:
                error_text = f"No pude generar una consulta válida después de {result['attempts']} intento(s).\n\nError: `{result['error']}`"
                st.error(error_text)
                with st.expander("Ver última consulta SQL intentada"):
                    st.code(format_sql_for_display(result["sql"]), language="sql")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_text,
                    "sql": result["sql"],
                })

        # ============================================================
        # MODO RAG
        # ============================================================
        else:
            with st.spinner("Buscando en fuentes..."):
                result = run_rag_pipeline(user_prompt, chat_session=st.session_state.rag_chat_session)

            st.session_state.rag_chat_session = result["chat_session"]

            if result["success"]:
                st.markdown(result["answer"])
                render_sources(result["cited_sources"])

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result["cited_sources"],
                })

            elif not result.get("answerable", True):
                warning_text = f"No tengo esa información disponible. {result['reason']}"
                st.warning(warning_text)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": warning_text,
                })

            else:
                error_text = f"No pude generar una respuesta.\n\nError: `{result.get('error', 'desconocido')}`"
                st.error(error_text)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_text,
                })