import torch
from transformers import pipeline

device = 0 if torch.cuda.is_available() else -1
# Si tienes VRAM, sube a flan-t5-large para mejor calidad en español.
model_name = "google/flan-t5-large"  # usa "google/flan-t5-base" si vas justo de VRAM

print(f"Device: {'CUDA' if device==0 else 'CPU'} | Model: {model_name}")
gen = pipeline("text2text-generation", model=model_name, device=device)

FEWSHOT = (
    "Responde en español de forma directa y sin repetir la pregunta.\n\n"
    "Pregunta: ¿Qué es el sobreajuste (overfitting)?\n"
    "Respuesta: Es cuando un modelo aprende demasiado los detalles y el ruido del entrenamiento y rinde mal en datos nuevos. Se mitiga con más datos, regularización, early stopping o validación cruzada.\n\n"
    "Pregunta: ¿Para qué sirve el aprendizaje por refuerzo?\n"
    "Respuesta: Sirve para aprender decisiones secuenciales mediante prueba y error usando recompensas; se aplica en robótica, juegos y optimización de procesos.\n\n"
)

def ask(question: str):
    prompt = FEWSHOT + f"Pregunta: {question}\nRespuesta:"
    out = gen(
        prompt,
        max_new_tokens=96,
        num_beams=4,                # beam search (determinista)
        early_stopping=True,
        no_repeat_ngram_size=3,
        encoder_no_repeat_ngram_size=5,  # evita copiar n-gramas del input
        repetition_penalty=1.15,
    )
    return out[0]["generated_text"].strip()

print("\n== PRUEBA 1 ==")
print(ask("¿Qué es un LLM y un ejemplo de uso real?"))
