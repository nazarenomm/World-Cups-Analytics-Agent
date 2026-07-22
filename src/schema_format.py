"""
Formateo de metadata de schema para inyección en prompts de LLM.
Usado tanto con pruning activo (top_k chico) como con schema completo
(top_k = total de tablas, cuando USE_SCHEMA_PRUNING=False).
"""


def format_schema_for_prompt(relevant_tables: list[dict]) -> str:
    blocks = []
    for entry in relevant_tables:
        meta = entry["metadata"]
        lines = [f"### Table/view: {meta['name']}", f"Description: {meta['description']}"]

        table_note = meta.get("note")
        if table_note:
            lines.append(f"Note: {table_note}")

        lines.append("Columns:")

        for col_name, col_info in meta["columns"].items():
            if isinstance(col_info, dict):
                desc = col_info.get("description", "")
                line = f"  - {col_name}: {desc}"
                if "enum_values" in col_info:
                    values = ", ".join(str(v) for v in col_info["enum_values"])
                    line += f" [possible values: {values}]"
                if "note" in col_info:
                    line += f" (Note: {col_info['note']})"
            else:
                line = f"  - {col_name}: {col_info}"
            lines.append(line)

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)