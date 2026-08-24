# World Cups Analytics Agent

Un agente conversacional que responde preguntas en lenguaje natural sobre los Mundiales de fútbol (1930–2022), combinando dos pipelines complementarios:

- **Text-to-SQL** para preguntas estadísticas o estructuradas
- **RAG** para preguntas históricas y contextuales

---

## Demo en vivo: [[streamlit](https://wc-analytics-agent.streamlit.app/)]

> ⚠️ **Nota**: la app está deployada en Streamlit Community Cloud. Si estuvo inactiva, Streamlit "duerme" la aplicación. Si ves un mensaje del tipo "Zzzz: This app has gone to sleep due to inactivity", hacé click en "Yes, get this app back up!".

Preguntás en lenguaje natural, eligiendo el modo según el tipo de pregunta:

Ambos modos mantienen contexto conversacional de forma independiente (podés hacer preguntas de seguimiento sin repetir contexto, dentro del mismo modo).


### SQL:
Estadísticas de jugadores, DTs, selecciones, partidos, árbitros, pelotas oficiales, etc. Devuelve tabla + gráfico automático + la consulta SQL generada (visible para debug/transparencia; el dataset origen es público).

**Visualizaciones disponibles:**

#### - Gráfico de dispersión (scatter)

<img src="imagenes_demo/scatter.png" width="800">  

Además del gráfico, se muestra una tabla ordenable con los datos solicitados:  
<img src="imagenes_demo/scatter_tabla.png" width="800">

El chatbot tiene memoria y puede realizar modificaciones:  
<img src="imagenes_demo/scatter_2.png" width="800">

#### - Gráfico de barras  
<img src="imagenes_demo/barchart.png" width="800">

#### - Gráfico de líneas  
<img src="imagenes_demo/linechart.png" width="800">  

<img src="imagenes_demo/linechart_2.png" width="800">

#### - Gráfico de torta (piechart)
Este tipo de gráfico debe ser pedido explícitamente, el default es el gráfico de barras  

<img src="imagenes_demo/piechart.png" width="800">

#### - Mapa  
Este tipo de gráfico debe ser pedido explícitamente, el default es el gráfico de barras  
<img src="imagenes_demo/mapa.png" width="800">

#### - Métrica
Cuando se solicite un dato específico se devuelve una tarjeta con el valor encontrado  
<img src="imagenes_demo/metrica.png" width="800">

### RAG:
Contexto histórico, motivaciones, repercusiones de eventos puntuales. Devuelve una respuesta narrativa con **citas a las fuentes usadas**, cada una linkeada al artículo de Wikipedia correspondiente.

**Ejemplos:**  
<img src="imagenes_demo/rag_0.png" width="800">  

<img src="imagenes_demo/rag_1.png" width="800">

---

## Stack

- **UI**: Streamlit
- **Base de datos**: Supabase (PostgreSQL + pgvector)
- **LLM**: Google Gemini (free tier vía AI Studio)
- **Embeddings**: `intfloat/multilingual-e5-base`
- **Gráficos**: Plotly

---

## Fuentes de datos

### Datos estructurados

La base estructurada (torneos, partidos, jugadores, goles, etc.) parte del dataset [**Fjelstul World Cup Database**](https://www.github.com/jfjelstul/worldcup), creado por Joshua C. Fjelstul, Ph.D.

> © 2023 Joshua C. Fjelstul, Ph.D. La estructura y organización original de la Fjelstul World Cup Database, así como toda su documentación, están publicadas bajo licencia [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode).
>
> **Modificaciones realizadas sobre el dataset original:** los datos fueron reprocesados y cargados bajo un **schema relacional propio** (claves primarias sustitutas, normalización y organización de tablas distinta a la original), diseñado específicamente para este proyecto. La estructura de tablas, las vistas agregadas, y todo el código de este repositorio son trabajo propio derivado del dataset original.

Este proyecto, al ser obra derivada, se distribuye también bajo licencia **CC-BY-SA 4.0**.

### Datos adicionales

- Pelotas oficiales de cada Mundial (`match_balls`): scrapeadas de Wikipedia.
- **Corpus RAG**: artículos seleccionados manualmente de Wikipedia.

---

## Estructura del repo

```
world-cups-analytics-agent/
├── app.py                     # Entrypoint de Streamlit
├── chat_view.py               # Ventana de Streamlit para interactuar con el agente
├── info_view.py               # Ventana de Streamlit con información sobre los datos disponibles
├── requirements_local.txt     # Requerimientos para instalación local
├── requirements.txt           # Requerimientos para deploy en Streamlit Cloud
├── corpus/                    # Artículos extraídos de Wikipedia, en JSON
├── data/
│   └── processed/             # Archivos .csv cargados a Supabase (base de datos)
├── processing/
│ └── data_processing.ipynb    # Notebook con el procesado del dataset origen
├── python/                    # Scripts varios de carga a Supabase, cálculo de embeddings, chunking, etc.
├── schema/
│ ├── DDL.sql                  # Creación de la estructura de la base de datos
│ ├── schema_metadata.json     # Descripciones, columnas, enums, ejemplos por tabla/vista
│ ├── embeddings_cache.pkl     # Embeddings del schema, precalculados
│ ├── local_model/             # Modelo E5 local, compartido entre schema pruning y RAG (gitignored)
│ ├── download_model.py
│ └── views/                   # Consultas SQL usadas para crear las vistas en la base de datos
├── src/
│ ├── config.py                # Flags y constantes
│ ├── prompts.py               # Prompts y reglas de dominio (Text-to-SQL)
│ ├── rag_prompts.py           # Prompts y reglas de dominio (RAG)
│ ├── schema_format.py         # Formateo de metadata de schema para el LLM
│ ├── schema_pruning.py        # Selección de tablas relevantes por embeddings (inactivo)
│ ├── retrieval.py             # Embedding de query + similarity search en Supabase (RAG)
│ ├── text_to_sql.py           # Generación de SQL vía Gemini
│ ├── db.py                    # Validación + ejecución contra Postgres (rol solo lectura)
│ ├── pipeline.py              # Orquestación Text-to-SQL: prompt → SQL → ejecución → retry
│ ├── rag_pipeline.py          # Orquestación RAG: prompt → retrieval → respuesta con citas
│ └── chart_detector.py        # Heurística de selección de gráfico
├── wikipedia/                 # Funciones para extraer artículos de Wikipedia
└── wikipedia_links/           # Listas curadas de URLs de Wikipedia por categoría (input del corpus)
```
---

## Arquitectura del pipeline Text-to-SQL

```
Prompt del usuario
      │
      ▼
Schema injection (metadata de tablas/vistas + reglas de dominio)
      │
      ▼
Gemini genera SQL ──► Validación de solo-lectura (regex) ──► Ejecución (rol agent_readonly)
      │                                                              │
      │                                                    ¿Error de Postgres?
      │                                                              │
      │                                              Sí ── reintento con el error ──┐
      │                                                                              │
      ▼                                                                              ▼
   Resultado exitoso                                                          (hasta 2 intentos extra)
      │
      ▼
Detección de tipo de gráfico (keywords del usuario + heurística por forma de la tabla resultante)
      │
      ▼
Tabla + gráfico + SQL
```

## Arquitectura del pipeline RAG

```
Prompt del usuario
      │
      ▼
Embedding de la query (prefijo "query: ", modelo E5)
      │
      ▼
Similarity search en Supabase (función RPC match_chunks)
      │
      ▼
Top-k chunks recuperados
      │
      ▼
Gemini genera respuesta citando fuentes ([Fuente N]) ──► ¿answerable=false?
      │                                                           │
      │                                              Sí ── "no tengo info suficiente"
      ▼
Respuesta + mapeo de citas a URLs reales de Wikipedia
```

## Cómo correrlo localmente

```bash
git clone https://github.com/nazarenomm/World-Cups-Analytics-Agent
cd World-Cups-Analytics-Agent
pip install -r requirements_local.txt

# Descargar el modelo de embeddings localmente (una sola vez, usado tanto por schema pruning como por RAG)
python schema/download_model.py

# Generar los embeddings del schema (una sola vez, o tras editar schema_metadata.json)
python schema/compute_schema_embeddings.py

# Generar el corpus RAG desde las listas curadas de Wikipedia (una sola vez, o tras editar wikipedia_links/)
python python/build_corpus.py

# Calcular embeddings del corpus y cargarlos a Supabase (una sola vez, o tras regenerar el corpus)
python python/compute_chunks_embeddings.py
python python/load_embeddings_to_supabase.py
```

Configurá un `.env` en la raíz con:
```bash
AGENT_DB_CONNECTION_STRING=postgresql://agent_readonly.xxx:password@host:6543/postgres
GOOGLE_KEY=tu_api_key_de_gemini
HF_TOKEN=tu_token_de_hugging_face # solo necesario para download_model.py
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_service_role_key_de_supabase
```

Correr la app:

```bash
streamlit run app.py
```

---

## Licencia

CC-BY-SA 4.0 — ver sección de fuentes de datos arriba para atribución completa al dataset original.
