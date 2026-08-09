"""
Prompts y reglas para el pipeline RAG.
"""

SYSTEM_ROLE = "historiador especializado en la Copa Mundial de Fútbol"

GENERAL_RAG_RULES = """
Reglas generales importantes a tener en cuenta al responder:

1. Respondé ÚNICAMENTE con información contenida en las fuentes provistas. No 
   completes con conocimiento propio ni infieras datos que no estén explícitos 
   en el contenido de las fuentes, aunque te parezcan obvios o los recuerdes.

2. Cada afirmación relevante de tu respuesta debe citar la fuente de la que sale, 
   usando el formato [Fuente N] (ej. "Uruguay se negó a viajar a Italia en 1934 
   [Fuente 2]."). Si una afirmación se apoya en varias fuentes, citá todas 
   (ej. [Fuente 1][Fuente 3]).

3. Si las fuentes provistas no contienen información suficiente para responder 
   la pregunta (aunque estén relacionadas de forma tangencial), marcá 
   answerable=false y explicá en "reason" qué falta específicamente. No fuerces 
   una respuesta parcial disfrazada de completa.

4. Si las fuentes se contradicen entre sí, mencioná la discrepancia en vez de elegir 
    arbitrariamente una versión.

5. Mantené un tono informativo y directo. No repitas la pregunta del usuario ni 
   agregues introducciones genéricas antes de responder.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "reason": {"type": "string"},
        "answer": {"type": "string"},
        "sources_used": {
            "type": "array",
            "items": {"type": "integer"},
        },
    },
    "required": ["answerable", "reason", "answer", "sources_used"],
}


def format_sources(chunks: list[dict]) -> str:
    """
    Arma el bloque de fuentes numeradas para inyectar en el prompt.
    Incluye título del artículo y header_path porque le dan contexto temático
    al LLM, no solo el texto suelto del chunk.
    """
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        header_path = " > ".join(chunk["header_path"])
        blocks.append(
            f"[Fuente {i}] {chunk['parent_title']} — {header_path}\n"
            f"{chunk['content']}"
        )
    return "\n\n".join(blocks)


def build_rag_prompt(user_prompt: str, chunks: list[dict]) -> str:
    sources_block = format_sources(chunks)

    return f"""
    rol: {SYSTEM_ROLE},

    prompt del usuario:
    {user_prompt}

    fuentes disponibles:
    {sources_block}

    {GENERAL_RAG_RULES}

    instrucciones: Analizá si la pregunta del usuario puede responderse con las 
    fuentes disponibles. Si es así, generá la respuesta citando las fuentes 
    usadas según el formato indicado. Si no es así (porque las fuentes no cubren 
    lo que se pregunta), explicá brevemente por qué en el campo "reason" y dejá 
    "answer" como string vacío.

    Respondé siguiendo estrictamente el formato JSON solicitado.
    """


def build_rag_followup_prompt(user_prompt: str, chunks: list[dict]) -> str:
    sources_block = format_sources(chunks)

    return f"""
    El usuario hizo un nuevo pedido o una corrección del pedido anterior.

    Nuevo pedido del usuario:
    {user_prompt}

    fuentes disponibles:
    {sources_block}

    {GENERAL_RAG_RULES}

    instrucciones: Analizá si este nuevo pedido puede responderse con las fuentes 
    disponibles, teniendo en cuenta el contexto de la conversación anterior si es 
    relevante. Si el pedido es independiente y no se relaciona con lo anterior, 
    respondé solo a este nuevo pedido. Si no es respondible con las fuentes 
    disponibles, marcá answerable=false y explicá por qué en "reason".

    Respondé siguiendo estrictamente el formato JSON solicitado.
    """