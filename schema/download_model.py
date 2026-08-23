"""
Correr UNA SOLA VEZ para descargar el modelo localmente al proyecto.
Después de esto, nunca más hace falta token ni internet para cargarlo.
"""
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "intfloat/multilingual-e5-base"
LOCAL_PATH = Path(__file__).parent / "local_model"
HF_TOKEN = os.environ.get("HF_TOKEN")

def main():
    print(f"Descargando {MODEL_NAME} desde Hugging Face Hub...")
    model = SentenceTransformer(MODEL_NAME, token=HF_TOKEN)
    model.save(str(LOCAL_PATH))
    print(f"Modelo guardado en {LOCAL_PATH}")

if __name__ == "__main__":
    main()