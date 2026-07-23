import streamlit as st
import pandas as pd

from src import run_pipeline

st.set_page_config(page_title="World Cup Analytics Agent", page_icon="⚽", layout="wide")
st.title("⚽ World Cup Analytics Agent")
st.caption("Preguntá sobre estadísticas históricas de los Mundiales de fútbol (1930 a 2022)")

# --- Estado de sesión ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

if "messages" not in st.session_state:
    st.session_state.messages = []  # lista de dicts: {role, content, sql?, df?}

# --- Render del historial ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("df") is not None:
            st.dataframe(msg["df"], use_container_width=True)
        if msg.get("sql"):
            with st.expander("Ver consulta SQL generada"):
                st.code(msg["sql"], language="sql")

# --- Input del usuario ---
user_prompt = st.chat_input("Ej: ¿Quién es el máximo goleador histórico de los mundiales?")

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
            response_text = f"Encontré {len(df)} resultado(s)."
            st.markdown(response_text)
            st.dataframe(df, use_container_width=True)
            with st.expander("Ver consulta SQL generada"):
                st.code(result["sql"], language="sql")

            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text,
                "df": df,
                "sql": result["sql"],
            })
        else:
            error_text = f"No pude generar una consulta válida después de {result['attempts']} intento(s).\n\nError: `{result['error']}`"
            st.error(error_text)
            with st.expander("Ver última consulta SQL intentada"):
                st.code(result["sql"], language="sql")

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