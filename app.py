import streamlit as st
import pandas as pd
import plotly.express as px
import sqlparse

from src import run_pipeline, resolve_chart_type, get_chart_columns, normalize_dtypes

def format_sql_for_display(sql: str) -> str:
    return sqlparse.format(sql, reindent=True, keyword_case="upper")

st.set_page_config(page_title="World Cup Analytics Agent", page_icon="⚽", layout="wide")
st.title("⚽ World Cup Analytics Agent")
st.caption("Preguntá sobre estadísticas históricas de los Mundiales de fútbol (1930 a 2022)")

# --- Estado de sesión ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

if "messages" not in st.session_state:
    st.session_state.messages = []  # lista de dicts: {role, content, sql?, df?}

# --- Render del historial ---
def render_chart(chart_type: str, df: pd.DataFrame, color_by: str | None = None):
    if chart_type is None:
        return

    cols = get_chart_columns(df, chart_type, color_by=color_by)

    if chart_type == "metric":
        label = df.iloc[0][cols["label_col"]] if cols["label_col"] != cols["value_col"] else cols["value_col"]
        st.metric(label=str(label), value=df.iloc[0][cols["value_col"]])
        return

    if chart_type == "bar_h":
        chart_df = df.sort_values(cols["value_col"], ascending=False)
        fig = px.bar(
            chart_df,
            x=cols["value_col"],
            y=cols["category_col"],
            orientation="h",
            color=cols["color_col"],
            category_orders={cols["category_col"]: chart_df[cols["category_col"]].tolist()},
        )
        fig.update_layout(margin=dict(l=10, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        return

    if chart_type == "line":
        if cols["x_col"] not in df.columns:
            st.dataframe(df, use_container_width=True)
            return
        chart_df = df.sort_values(cols["x_col"])
        fig = px.line(
            chart_df,
            x=cols["x_col"],
            y=cols["y_col"],
            color=cols["color_col"],
            markers=True,
        )
        fig.update_layout(margin=dict(l=40, r=40, t=20, b=40))
        st.plotly_chart(fig, use_container_width=True)
        return

    if chart_type == "scatter":
        fig = px.scatter(
            df,
            x=cols["x_col"],
            y=cols["y_col"],
            hover_name=cols["label_col"],
            color=cols["color_col"],
            text=cols["label_col"] if len(df) <= 15 else None,
        )
        fig.update_traces(marker=dict(size=10), textposition="top center")
        fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig, use_container_width=True)
        return
    
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("df") is not None:
            if msg.get("chart_type"):
                render_chart(msg["chart_type"], msg["df"], color_by=msg.get("chart_color_by", ""))
            with st.expander("Ver tabla de resultados"):
                st.dataframe(msg["df"], use_container_width=True)
        if msg.get("sql"):
            with st.expander("Ver consulta SQL generada"):
                st.code(format_sql_for_display(msg["sql"]), language="sql")

# --- Input del usuario ---
user_prompt = st.chat_input("Ej: ¿Quién es el máximo goleador histórico?")

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generando y ejecutando consulta..."):
            result = run_pipeline(user_prompt, chat_session=st.session_state.chat_session)

        st.session_state.chat_session = result["chat_session"]

        if result["success"]:
            df = pd.DataFrame(result["rows"], columns=result["columns"])
            df = normalize_dtypes(df)
            chart_type = resolve_chart_type(user_prompt, df, llm_suggestion=result.get("llm_chart_type"))
            color_by = result.get("llm_chart_color_by")

            response_text = f"Encontré {len(df)} resultado(s)."
            st.markdown(response_text)
            render_chart(chart_type, df, color_by=color_by)

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

# --- Sidebar: nuevo chat ---
with st.sidebar:
    st.header("Opciones")
    if st.button("🔄 Nueva conversación"):
        st.session_state.chat_session = None
        st.session_state.messages = []
        st.rerun()