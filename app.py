import streamlit as st

st.set_page_config(page_title="World Cup Analytics Agent", layout="wide")

pg = st.navigation([
    st.Page("chat_view.py", title="Chat", icon="💬", default=True),
    st.Page("info_view.py", title="Datos disponibles", icon="📊"),
])
pg.run()