# ⚽ World Cup Analytics Agent

Un agente conversacional que responde preguntas en lenguaje natural (español) sobre la historia completa de los Mundiales de fútbol (1930–2022), usando un pipeline **Text-to-SQL** sobre una base de datos relacional.

Este proyecto es un ejercicio de portfolio enfocado en decisiones de ingeniería production-minded — no solo "que funcione", sino documentar por qué se tomó cada decisión, qué alternativas se descartaron, y qué limitaciones son conscientes vs. accidentales.

> 🚧 **Estado: MVP funcional.** El flujo Text-to-SQL está completo end-to-end (prompt → SQL → ejecución → tabla/gráfico + sql query). La capa de RAG para preguntas contextuales/históricas y el ruteo híbrido SQL+RAG están en desarrollo.

---

## Demo

- Preguntás en lenguaje natural sobre estadísticas de jugadores, DTs, selecciones, partidos, árbitros, pelotas oficiales, etc.
- El agente genera la consulta SQL correspondiente, la ejecuta contra una base **de solo lectura**, y devuelve:
  - Una tabla con los resultados.
  - Un gráfico automático cuando aplica (barras, línea temporal, scatter, o métrica destacada).
  - La consulta SQL generada, visible para debug/transparencia. (el dataset que da origen a la base de datos es público, por lo que no hay un problema de seguridad al mostrar esto al usuario)
- Mantiene contexto conversacional: podés hacer preguntas de seguimiento ("mejor dame el top 20 en lugar del top 10") sin repetir todo el contexto.

*(Deploy público pendiente — se hará una vez completada la capa de RAG. Por ahora, instrucciones de corrida local más abajo.)*

---

## Stack

- **UI**: Streamlit
- **Base de datos**: Supabase (PostgreSQL), con un rol dedicado de solo lectura para el agente
- **LLM**: Google Gemini (`gemini-3.1-flash-lite`, free tier vía AI Studio)
- **Embeddings** (para pruning de schema, actualmente inactivo): `paraphrase-multilingual-MiniLM-L12-v2`, corriendo localmente
- **Gráficos**: Plotly

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

---

## Decisiones de diseño y por qué

Esta sección documenta las decisiones de arquitectura más relevantes, incluyendo alternativas evaluadas y descartadas — el objetivo es que las limitaciones actuales se entiendan como elecciones conscientes, no como cosas "que faltó hacer".

### Seguridad: rol de Postgres de solo lectura, no solo validación de texto

El agente se conecta con un rol dedicado (`agent_readonly`) que **solo tiene permiso de `SELECT`** sobre el schema — sin `INSERT`/`UPDATE`/`DELETE`/`DROP`/etc. Esta es la barrera dura: aunque el LLM generara una consulta destructiva, la base la rechaza a nivel de permisos.

Sobre esto se agrega una segunda capa liviana, una validación por regex que exige que la consulta empiece con `SELECT`/`WITH`, bloquea keywords de escritura, y bloquea múltiples statements encadenados. Esta capa no es la defensa principal — es una mejora de UX (mensajes de error más claros).

**RLS (Row Level Security) fue deshabilitado deliberadamente.** Supabase lo activa por default en varias tablas, pero está pensado para control de acceso multi-usuario vía la API REST pública. Como el agente se conecta directo por Postgres con un rol propio de permisos acotados, RLS no aporta nada adicional en este escenario. Además, sin una policy explícita, RLS bloquea silenciosamente todas las consultas (devuelve 0 filas sin error explícito), este fue justamente el bug que motivó a desactivar esta capa conscientemente.

### Pruning de schema por embeddings: implementado, pero inactivo

El plan original incluía podar el schema antes de mandarlo al LLM (usando similitud de embeddings entre el prompt del usuario y las descripciones de cada tabla/vista), para evitar mandar las ~30 tablas completas en cada consulta.

Al testear con `gemini-3.1-flash-lite`, el modelo manejó correctamente el schema completo (33 tablas/vistas) sin necesidad de podarlo, con precisión validada en pruebas manuales sobre una decena de prompts variados. Orignalmente pensaba usar `gemini-2.5-flash-lite` ya que no sabía que Google había liberado el uso gratuito de la versión 3.1, esa versión anterior seguramente hubiera necesitado el pruning.

**Se decidió no activar el pruning para este volumen de datos.** El módulo queda implementado y funcional (embeddings locales precalculados, sin dependencia de tokens externos en runtime) detrás de un flag de configuración (`USE_SCHEMA_PRUNING`), documentado como una solución de escalabilidad lista para reactivarse si el schema crece considerablemente, o si se migra a un modelo con ventana de contexto o costo por token más restrictivo.

### Modelo de embeddings local, sin dependencia de tokens en runtime

El modelo de embeddings (`paraphrase-multilingual-MiniLM-L12-v2`) se descarga una única vez y se guarda localmente en el proyecto, en vez de cargarse desde Hugging Face Hub en cada arranque. Esto elimina una dependencia de red y de autenticación (token de HF) del camino crítico de la aplicación. Esto es relevante porque un token expirado no debería poder tirar la app en producción.

### Manejo de NULL vs. 0 según cobertura real de los datos

Varias tablas fuente (`player_appearances`, `bookings`, `substitutions`) solo tienen cobertura completa desde 1970 en adelante. Las vistas agregadas (`v_player_stats_career`, etc.) distinguen explícitamente entre "el jugador no tiene datos disponibles" (`NULL`) y "el jugador tiene datos y el valor es cero" (`0`), en vez de colapsar ambos casos a `0`, lo cual falsearía comparaciones históricas (ej. un jugador de 1950 no "tiene 0 tarjetas amarillas", simplemente no hay registro).

### Entidades históricas divididas (Alemania, URSS, Yugoslavia, Checoslovaquia)

Varios países que sufrieron cambios políticos (reunificación de Alemania, disolución de la URSS y Yugoslavia, separación de Checoslovaquia) están representados como múltiples entidades distintas en la tabla `teams`, cada una con su propio `team_id`. Esto es correcto desde el punto de vista histórico/FIFA, pero genera un problema real al calcular estadísticas de carrera para jugadores que representaron a más de una de estas entidades (ej. Lothar Matthäus, convocado tanto por Alemania Occidental como por la Alemania reunificada): agrupar por equipo puede dividir su total entre ambas entidades (haciéndolo desaparecer de un ranking top-N), y unir sin agregar correctamente puede duplicar sus filas.

Este comportamiento se documenta, junto a otros, explícitamente en las reglas de generación de SQL que se inyectan en cada prompt, indicando al modelo cómo resolverlo (tomar una entidad representativa por jugador en vez de agrupar/unir ingenuamente) en lugar de normalizar artificialmente los datos originales.

### Gráficos: heurística de reglas, no una decisión del LLM

En vez de pedirle al LLM que además de generar SQL elija un tipo de gráfico de una lista, la decisión se resuelve con lógica determinística:

1. Si el usuario pide explícitamente un tipo de gráfico (por keywords: "gráfico de barras", "evolución", "scatter", etc.), se respeta ese pedido.
2. Si no, se infiere automáticamente según la forma del resultado (una categórica + una numérica → barras; una columna de año + una numérica → línea; dos numéricas → scatter; una sola fila con un valor → métrica destacada; en cualquier otro caso, solo tabla).

Este enfoque evita agregar otro campo a parsear en la respuesta del LLM (menos superficie de fallo, menos tokens) y es determinístico y testeable de forma aislada, sin depender de que el modelo "elija bien".

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

---

## Estructura del repo

```
world-cups-analytics-agent/
├── app.py                     # Entrypoint de Streamlit
├── requirements.txt
├── data/
│   └── processed/             # Archivos .csv cargados a Supabase (base de datos)
├── processing/
│   └── data_processing.ipynb  # Notebook con el procesado del dataset origen
├── src/
│   ├── config.py              # Flags y constantes
│   ├── prompts.py             # Prompts y reglas de dominio para el LLM
│   ├── schema_format.py       # Formateo de metadata de schema para el LLM
│   ├── schema_pruning.py      # Selección de tablas relevantes por embeddings (inactivo)
│   ├── text_to_sql.py         # Generación de SQL vía Gemini
│   ├── db.py                  # Validación + ejecución contra Postgres (rol solo lectura)
│   ├── pipeline.py            # Orquestación: prompt → SQL → ejecución → retry
│   └── chart_detector.py      # Heurística de selección de gráfico
├── schema/
│   ├── schema_metadata.json   # Descripciones, columnas, enums, ejemplos por tabla/vista
│   ├── embeddings_cache.pkl   # Embeddings precalculados (gitignored, regenerable)
│   ├── local_model/           # Modelo de embeddings local (gitignored, se descarga una vez)
│   ├── download_model.py
│   └── views/                 # Consultas SQL usadas para crear las vistas en la base de datos
├── python/                    # scripts de carga a supabase, calculo de embedding y testeo del rol agent_readonly
├── wikipedia/                 # scripts para scrapear wikipedia en busca de tablas adicionales y ampliar el corpus
└── corpus/                    # (en construcción) corpus para la capa de RAG
```

---

## Cómo correrlo localmente

```bash
git clone https://github.com/nazarenomm/World-Cups-Analytics-Agent
cd World-Cups-Analytics-Agent
pip install -r requirements.txt

# Descargar el modelo de embeddings localmente (una sola vez)
python schema/download_model.py

# Generar los embeddings del schema (una sola vez, o tras editar schema_metadata.json)
python schema/build_embeddings.py
```

Configurá un `.env` en la raíz con:

```
AGENT_DB_CONNECTION_STRING=postgresql://agent_readonly.xxx:password@host:6543/postgres
GOOGLE_KEY=tu_api_key_de_gemini
HF_TOKEN=tu_token_de_hugging_face   # solo necesario para download_model.py
```

Correr la app:

```bash
streamlit run app.py
```

---

## Roadmap

- [ ] Corpus RAG (Wikipedia + otras fuentes) para preguntas contextuales/históricas
- [ ] Ruteo híbrido entre Text-to-SQL y RAG
- [ ] Deploy público (Streamlit Community Cloud u otra alternativa)

---

## Licencia

CC-BY-SA 4.0 — ver sección de fuentes de datos arriba para atribución completa al dataset original.