"""Analiza la distribución de tamaños de sección en el corpus generado."""
import json
from pathlib import Path

CORPUS_DIR = Path("corpus")

lengths = []
long_ones = []
short_ones = []

for json_file in CORPUS_DIR.rglob("*.json"):
    doc = json.loads(json_file.read_text(encoding="utf-8"))
    for section in doc["sections"]:
        n_words = len(section["content"].split())
        lengths.append(n_words)
        header = " > ".join(section["header_path"])
        if n_words > 400:
            long_ones.append((n_words, doc["title"], header))
        elif n_words < 15:
            short_ones.append((n_words, doc["title"], header))

if lengths:
    lengths.sort()
    n = len(lengths)
    print(f"Total secciones: {n}")
    print(f"Min: {lengths[0]}, Max: {lengths[-1]}")
    print(f"Mediana: {lengths[n//2]}, Promedio: {sum(lengths)/n:.0f}")
    print(f"\nSecciones largas (>400 palabras, candidatas a sub-dividir): {len(long_ones)}")
    for n_w, title, header in sorted(long_ones, reverse=True)[:5]:
        print(f"  {n_w}w - {title} > {header}")
    print(f"\nSecciones cortas (<15 palabras, candidatas a fusionar): {len(short_ones)}")
    for n_w, title, header in short_ones[:5]:
        print(f"  {n_w}w - {title} > {header}")
else:
    print("No se encontraron JSONs en corpus/")