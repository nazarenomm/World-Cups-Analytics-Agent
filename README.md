# World Cups Analytics Agent

Un agente conversacional que responde preguntas en lenguaje natural (español) sobre la historia completa de los Mundiales de fútbol (1930–2022), combinando dos pipelines complementarios:

- **Text-to-SQL** para preguntas estadísticas/estructuradas (rankings, totales, comparaciones)
- **RAG** para preguntas históricas/contextuales (por qué, cómo, repercusiones)

Este proyecto es un ejercicio de portfolio enfocado en decisiones de ingeniería production-minded — no solo "que funcione", sino documentar por qué se tomó cada decisión, qué alternativas se descartaron, y qué limitaciones son conscientes vs. accidentales.

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
> **Modificaciones realizadas sobre el dataset original:** los datos fueron reprocesados y cargados bajo un **schema relacional propio** (claves primarias sustitutas de tipo TEXT, normalización y organización de tablas distinta a la original), diseñado específicamente para este proyecto. La estructura de tablas, las vistas agregadas, y todo el código de este repositorio son trabajo propio derivado del dataset original, y se publican bajo la misma licencia CC-BY-SA 4.0, según lo requerido.

Este proyecto, en tanto obra derivada, se distribuye también bajo licencia **CC-BY-SA 4.0**.

### Datos adicionales

- Pelotas oficiales de cada Mundial (`match_balls`): scrapeadas de Wikipedia.
- **Corpus RAG**: artículos seleccionados manualmente de Wikipedia en español (confederaciones, ediciones de Mundiales, partidos históricos, estadios, selecciones nacionales, e historia general del torneo).

---

## Estructura del repo

```
world-cups-analytics-agent/
├── app.py                     # Entrypoint de Streamlit
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

---

## Decisiones de diseño y por qué

Esta sección documenta las decisiones de arquitectura más relevantes, incluyendo alternativas evaluadas y descartadas — el objetivo es que las limitaciones actuales se entiendan como elecciones conscientes, no como cosas "que faltó hacer".

### Seguridad: rol de Postgres de solo lectura, no solo validación de texto

El agente se conecta con un rol dedicado (`agent_readonly`) que **solo tiene permiso de `SELECT`** sobre el schema — sin `INSERT`/`UPDATE`/`DELETE`/`DROP`/etc. Esta es la barrera dura: aunque el LLM generara una consulta destructiva, la base la rechaza a nivel de permisos.

Sobre esto se agrega una segunda capa liviana, una validación por regex que exige que la consulta empiece con `SELECT`/`WITH`, bloquea keywords de escritura, y bloquea múltiples statements encadenados. Esta capa no es la defensa principal — es una mejora de UX (mensajes de error más claros).

**RLS (Row Level Security) fue deshabilitado deliberadamente.** Supabase lo activa por default en varias tablas, pero está pensado para control de acceso multi-usuario vía la API REST pública. Como el agente se conecta directo por Postgres con un rol propio de permisos acotados, RLS no aporta nada adicional en este escenario. Además, sin una policy explícita, RLS bloquea silenciosamente todas las consultas (devuelve 0 filas sin error explícito), este fue justamente el bug que motivó a desactivar esta capa conscientemente.

### Pruning de schema por embeddings: implementado, pero inactivo

El plan original incluía podar el schema antes de mandarlo al LLM (usando similitud de embeddings entre el prompt del usuario y las descripciones de cada tabla/vista), para evitar mandar las ~30 tablas completas en cada consulta.

Al testear con `gemini-3.1-flash-lite`, el modelo manejó correctamente el schema completo (33 tablas/vistas) sin necesidad de podarlo, con precisión validada en pruebas manuales sobre una decena de prompts variados.

**Se decidió no activar el pruning para este volumen de datos.** El módulo queda implementado y funcional detrás de un flag de configuración (`USE_SCHEMA_PRUNING`), documentado como una solución de escalabilidad lista para reactivarse si el schema crece considerablemente, o si se migra a un modelo con ventana de contexto o costo por token más restrictivo.

### Modelo de embeddings: unificado a uno solo, elegido empíricamente

El proyecto pasó por dos iteraciones de modelo de embeddings antes de asentarse en la elección actual:

1. **Primera etapa**: `hiiamsid/sentence_similarity_spanish_es`, un modelo español-only entrenado para similitud semántica simétrica (STS — comparar oraciones parecidas en forma y longitud entre sí).
2. **Al construir el corpus RAG**, un test empírico con 6 preguntas de control mostró que este modelo fallaba sistemáticamente en preguntas formuladas de forma indirecta (sin compartir vocabulario explícito con el texto fuente), llegando a 0/5 chunks relevantes en varios casos, mientras que reformulaciones de la misma pregunta con una entidad nombrada explícitamente sí funcionaban bien. Este patrón es la firma característica de un modelo STS aplicado a un caso de uso de **retrieval asimétrico** (pregunta corta → pasaje largo que la responde), tarea para la que no fue entrenado.
3. **Se migró a `intfloat/multilingual-e5-base`**, un modelo multilingüe diseñado específicamente para retrieval asimétrico, con el mismo test de 6 preguntas mostrando mejoras sustanciales (0/5 → 5/5 en los casos más problemáticos). Este modelo requiere prefijar los textos con `"query: "` (búsquedas) o `"passage: "` (corpus) al momento de embeddear — convención de entrenamiento del modelo, no arbitraria, y crítica: omitirla degrada el retrieval sin arrojar ningún error.
4. **El modelo local se comparte entre schema pruning y RAG.** Al reemplazar los pesos locales para el paso 3, se detectó que `schema_pruning.py` cargaba el modelo desde la misma carpeta (`schema/local_model`) que ya tenía embeddeadas las descripciones de tabla con el modelo *anterior* — generando una discrepancia silenciosa de espacio vectorial (mismas 768 dimensiones en ambos modelos, así que no había error explícito de forma, solo resultados de similitud incorrectos). Se resolvió regenerando `schema/schema_embeddings_cache.pkl` con E5 + el prefijo `passage:` correspondiente, unificando todo el proyecto a un único modelo de embeddings.

### Se descartó un umbral de similarity absoluto para filtrar chunks irrelevantes

La primera intuición para RAG fue: si el mejor chunk recuperado tiene una similarity por debajo de cierto umbral, asumir que no hay información relevante y no llamar al LLM. Al testear con preguntas deliberadamente fuera de dominio (capital de Francia, reglas del ajedrez, autor de una novela), se encontró que **todas** devolvían similarities por encima de 0.7 contra el corpus de fútbol — un efecto de anisotropía conocido en modelos tipo BERT/E5, donde el espacio de embeddings queda comprimido y el coseno absoluto deja de ser interpretable como score de relevancia. El *orden relativo* del ranking sí es confiable (por eso el retrieval funciona bien en la práctica); el *valor* absoluto no.

**Se descartó el umbral** y se delegó el juicio de relevancia al LLM, vía un campo `answerable` (booleano) en el schema de respuesta estructurada — el mismo patrón ya usado en el pipeline SQL para preguntas sin dato disponible en el schema. Esto no agrega una llamada extra al modelo: ocurre en el mismo call que genera la respuesta final.

### Chunking del corpus RAG: por sección de Wikipedia, con split/merge y overlap

Cada artículo se trocea inicialmente respetando la jerarquía de headers de Wikipedia (una sección = un chunk candidato, con su `header_path` completo guardado como metadata), en vez de un chunking por tamaño fijo ciego al contenido — esto le da contexto temático explícito al LLM en el momento de responder.

Sobre esa base:
- **Secciones muy largas** (algunas superaban las 4000 palabras, ej. secciones de historia de selecciones con muchos títulos) se sub-dividen por oración (no por párrafo, ya que varias secciones vienen como bloques de texto corrido) respetando un máximo de ~350 palabras, con un overlap de 50 palabras entre sub-chunks consecutivos para no perder contexto en el corte.
- **Secciones muy cortas** (menos de 15 palabras — comunes en tablas de clasificación con subtítulos tipo "Grupo 4" sin texto propio) se fusionan con la sección siguiente.

### Citación de fuentes en RAG

Cada chunk recuperado se numera (`[Fuente N]`) y se le pide al LLM que cite explícitamente cuál usó para cada afirmación de su respuesta. La app mapea esos índices de vuelta a la URL real del artículo de Wikipedia y el título de la sección, mostrándolos como links verificables en la interfaz — priorizando trazabilidad por sobre una respuesta "más fluida" sin atribución.

### Corpus curado manualmente, no por búsqueda automática

Los artículos de Wikipedia que componen el corpus fueron seleccionados a mano (listas de URLs por categoría: confederaciones, ediciones, partidos famosos, estadios, selecciones, historia general), en vez de generarse por búsqueda automática de términos relacionados. Esto evita el ruido de títulos ambiguos y da control total sobre qué entra al corpus, a costo de no escalar automáticamente — trade-off aceptado para el volumen actual del proyecto.

### Modo de consulta: selección manual, no ruteo automático (por ahora)

La interfaz expone un selector explícito entre modo SQL y modo RAG, en vez de que el sistema infiera automáticamente cuál usar según la pregunta. Se eligió así para poder validar y depurar ambos pipelines de forma completamente independiente antes de invertir en la lógica de ruteo — que necesariamente requeriría una clasificación adicional (por LLM o heurística) y se construirá con mejor criterio una vez que se tenga evidencia real de qué tipo de preguntas fallan en cada modo por separado.

### Modelo de embeddings local, sin dependencia de tokens en runtime

El modelo de embeddings se descarga una única vez y se guarda localmente en el proyecto, en vez de cargarse desde Hugging Face Hub en cada arranque. Esto elimina una dependencia de red y de autenticación (token de HF) del camino crítico de la aplicación — un token expirado no debería poder tirar la app en producción.

### Manejo de NULL vs. 0 según cobertura real de los datos

Varias tablas fuente (`player_appearances`, `bookings`, `substitutions`) solo tienen cobertura completa desde 1970 en adelante. Las vistas agregadas (`v_player_stats_career`, etc.) distinguen explícitamente entre "el jugador no tiene datos disponibles" (`NULL`) y "el jugador tiene datos y el valor es cero" (`0`), en vez de colapsar ambos casos a `0`, lo cual falsearía comparaciones históricas.

### Entidades históricas divididas (Alemania, URSS, Yugoslavia, Checoslovaquia)

Varios países que sufrieron cambios políticos están representados como múltiples entidades distintas en la tabla `teams`, cada una con su propio `team_id`. Esto es correcto desde el punto de vista histórico/FIFA, pero genera un problema real al calcular estadísticas de carrera para jugadores que representaron a más de una de estas entidades. Este comportamiento se documenta explícitamente en las reglas de generación de SQL inyectadas en cada prompt, indicando al modelo cómo resolverlo en lugar de normalizar artificialmente los datos originales.

### Gráficos: heurística de reglas, no una decisión del LLM

En vez de pedirle al LLM que además de generar SQL elija un tipo de gráfico, la decisión se resuelve con lógica determinística: si el usuario pide explícitamente un tipo de gráfico se respeta ese pedido; si no, se infiere según la forma del resultado. Este enfoque evita agregar otro campo a parsear en la respuesta del LLM y es determinístico y testeable de forma aislada.

---

## Limitaciones conocidas (RAG)

- **Confusión temática entre eventos históricos similares con `top_k` bajo.** Ej.: la pregunta "¿por qué Uruguay se negó a jugar el mundial de 1934?" puede recuperar en su lugar contenido sobre la ausencia de Uruguay en 1938 (motivo distinto, mismo patrón temático), si el `top_k` es muy chico. Se mitiga subiendo `top_k`; una solución más robusta a futuro sería enriquecer cada chunk con el año explícito en el contenido, no solo en el `header_path`, o agregar un paso de re-ranking.
- **Cobertura del corpus es manual y finita.** Preguntas sobre eventos, jugadores o ediciones no cubiertos por los artículos curados no van a tener fuente — el sistema debería responder `answerable=false` en ese caso en vez de alucinar, pero esto depende de que el LLM siga bien la instrucción.
- **El corpus está en español; no se probó retrieval cross-lingual.** Preguntas en otros idiomas no fueron validadas end-to-end (aunque el modelo E5 es multilingüe y en teoría debería sostenerlo razonablemente).

---

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