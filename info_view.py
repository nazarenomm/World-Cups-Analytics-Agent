import streamlit as st
import json

@st.cache_data
def load_schema_metadata():
    with open("schema/schema_metadata.json", "r", encoding="utf-8") as f:
        return json.load(f)

st.subheader("Modelo de datos disponible")
st.caption("Estas son las tablas que el agente puede consultar en modo SQL.")

schema_metadata = load_schema_metadata()

for table in schema_metadata["tables"]:
    with st.expander(f"**{table['name']}**"):
        st.markdown(table["description"])
        st.markdown("**Columnas:** " + ", ".join(f"`{col}`" for col in table["columns"].keys()))

st.divider()

st.subheader("Temas cubiertos por el corpus histórico (RAG)")
st.markdown("""
- **Confederaciones**: CONMEBOL, UEFA, CAF, AFC, etc.
- **Ediciones**: cada Mundial, 1930–2022
- **Partidos famosos**: Maracanazo, Mano de Dios, etc.
- **Estadios**
- **Selecciones nacionales**
- **Historia general**
""")