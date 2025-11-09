# -*- coding: utf-8 -*-
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re

app = FastAPI(title="MAR-IA - Modelo Agrícola Inteligente", version="3.0")

# ===== IDENTIDAD DE MAR-IA =====
MARIA_IDENTITY = {
    "nombre": "MAR-IA",
    "descripcion": "Modelo de inteligencia artificial GPT diseñado para el agro",
    "especialidad": "agricultura, comercio agrícola y gestión de fincas",
    "personalidad": "amigable, conocedora y orientada a ayudar al sector agrícola"
}

# ===== CONOCIMIENTO AGRÍCOLA BASE =====
AGRO_KNOWLEDGE = {
    "cultivos_comunes": ["café", "maíz", "arroz", "papa", "plátano", "cacao", "caña", "yuca"],
    "temporadas": {
        "siembra": "depende del cultivo y la región, pero generalmente en épocas de lluvias",
        "cosecha": "varía según el ciclo del cultivo (90-180 días para cultivos básicos)"
    },
    "consejos_generales": {
        "riego": "El riego debe ajustarse según la etapa del cultivo y las condiciones climáticas",
        "fertilizacion": "Aplicar fertilizantes según análisis de suelo y requerimientos del cultivo",
        "plagas": "Monitoreo constante y manejo integrado de plagas es fundamental"
    }
}

# ===== DETECCIÓN DE PREGUNTAS SOBRE IDENTIDAD =====
def is_identity_question(question: str) -> Optional[str]:
    q = question.lower()
    patterns = {
        "quien_eres": [r"qui[eé]n eres", r"qui[eé]n es", r"tu nombre", r"c[oó]mo te llamas"],
        "que_haces": [r"qu[eé] haces", r"para qu[eé]", r"cu[aá]l es tu funci[oó]n"],
        "que_eres": [r"qu[eé] eres", r"tipo de (ia|inteligencia)"]
    }
    
    for intent, pats in patterns.items():
        for pat in pats:
            if re.search(pat, q):
                return intent
    return None

def answer_identity(intent: str, tone: str) -> str:
    responses = {
        "quien_eres": f"Soy {MARIA_IDENTITY['nombre']}, un {MARIA_IDENTITY['descripcion']}. 🌱 Estoy aquí para ayudarte con información sobre {MARIA_IDENTITY['especialidad']}.",
        
        "que_haces": f"Mi función es asistirte con información del sector agrícola. Puedo consultar datos de tu base de datos sobre compradores, facturas, cultivos y más, además de brindarte conocimientos generales sobre agricultura.",
        
        "que_eres": f"Soy {MARIA_IDENTITY['nombre']}, un modelo de inteligencia artificial especializado en el agro, basado en tecnología GPT. Mi especialidad es {MARIA_IDENTITY['especialidad']}."
    }
    
    return fmt(responses.get(intent, responses["quien_eres"]), tone)

# ===== DETECCIÓN DE TEMAS AGRÍCOLAS =====
def detect_agro_topic(question: str) -> Optional[str]:
    q = question.lower()
    
    topics = {
        "cultivo": ["cultivar", "siembra", "plantar", "cultivo", "cosecha"],
        "riego": ["riego", "agua", "irrigacion", "hidratar"],
        "fertilizacion": ["fertiliz", "abono", "nutrient", "npk"],
        "plagas": ["plaga", "enfermedad", "insecto", "control", "fungicida", "pesticida"],
        "clima": ["clima", "temperatura", "lluvia", "sequia", "helada"],
        "precio": ["precio", "venta", "mercado", "comercio"]
    }
    
    for topic, keywords in topics.items():
        if any(kw in q for kw in keywords):
            return topic
    return None

def generate_agro_advice(topic: str, question: str, tone: str) -> str:
    advice = {
        "cultivo": "Para un cultivo exitoso, considera: 1) Preparación adecuada del suelo, 2) Selección de semillas de calidad, 3) Época de siembra apropiada según tu región, 4) Manejo integrado durante el ciclo del cultivo.",
        
        "riego": "El riego eficiente requiere: considerar el tipo de suelo, la etapa del cultivo y las condiciones climáticas. El riego por goteo es muy eficiente para cultivos en hileras, mientras que la aspersión funciona bien para cultivos extensivos.",
        
        "fertilizacion": "La fertilización debe basarse en análisis de suelo. En general, los cultivos necesitan Nitrógeno (N) para crecimiento vegetativo, Fósforo (P) para raíces y floración, y Potasio (K) para resistencia y calidad de frutos.",
        
        "plagas": "El Manejo Integrado de Plagas (MIP) es la mejor estrategia: monitoreo regular, control cultural (rotación, limpieza), control biológico cuando sea posible, y uso racional de agroquímicos solo cuando sea necesario.",
        
        "clima": "El clima es crucial para la agricultura. Monitorea las condiciones meteorológicas, planifica según las temporadas de lluvia, y considera prácticas de conservación de agua para épocas secas.",
        
        "precio": "Los precios agrícolas varían según oferta/demanda, temporada y calidad del producto. Te recomiendo consultar los datos de tus registros o contactar con cooperativas agrícolas locales para información actualizada."
    }
    
    response = advice.get(topic, "Puedo ayudarte con información sobre agricultura. ¿Podrías ser más específico sobre lo que necesitas?")
    
    # Agregar nota sobre datos disponibles
    note = "\n\n💡 Si tienes datos específicos en tu sistema, puedo consultarlos para darte información más precisa sobre tu situación particular."
    
    return fmt(response + note, tone)

# ===== UTILIDADES DE ESTILO =====
def fmt(text: str, tone: str) -> str:
    tone = (tone or "amigable").lower()
    if tone == "amigable":
        return text
    if tone == "formal":
        text = re.sub(r" ?[🙂😉😊✨⭐️🎯✅🚀🥇🐣🔥🌱💡]", "", text)
        text = text.replace("¡", "").replace("!", ".").replace("…", ".")
        return text
    if tone == "tecnico":
        text = re.sub(r" ?[🙂😉😊✨⭐️🎯✅🚀🥇🐣🔥🌱💡]", "", text)
        return text
    return text

# Nombres amigables por tabla
NICE_NAMES = {
    "public.commerce_buyer": "compradores agrícolas",
    "public.users_user": "usuarios del sistema",
    "public.commerce_invoice": "facturas de comercio",
    "public.crops": "cultivos registrados",
    "public.harvests": "cosechas",
    "public.sales": "ventas",
}

# ===== DETECCIÓN DE INTENCIÓN =====
def detect_intent(question: str, sql: str, rows: List[Dict[str, Any]]) -> str:
    q = (question or "").lower()
    s = (sql or "").lower()
    if "count(" in s or "count(*)" in s or "cuánt" in q or "cuantos" in q:
        return "count"
    if "limit" in s or (rows and len(rows) <= 10):
        return "list_short"
    return "table"

# ===== HUMANIZACIÓN DE SUJETOS =====
def humanize_subject(question: str, sql: str, fallback: str = "registros") -> str:
    m = re.search(r'(?i)\bfrom\s+([a-z0-9_]+)\.([a-z0-9_]+)', sql or "")
    if m:
        key = f"{m.group(1).lower()}.{m.group(2).lower()}"
        if key in NICE_NAMES:
            return NICE_NAMES[key]
    
    q = (question or "").lower()
    if "compr" in q:
        return "compradores"
    if "usuario" in q:
        return "usuarios"
    if "factur" in q:
        return "facturas"
    if "cultiv" in q:
        return "cultivos"
    if "cosech" in q:
        return "cosechas"
    if "venta" in q or "vendi" in q:
        return "ventas"
    return fallback

def join_cols(cols: List[str]) -> str:
    if not cols: return ""
    if len(cols) == 1: return cols[0]
    return ", ".join(cols[:-1]) + " y " + cols[-1]

# ===== MOTOR HÍBRIDO: BD + CONOCIMIENTO =====
def nlg_answer(
    question: str,
    sql: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    lang: str = "es",
    tone: str = "amigable",
    suggest_followups: bool = True
) -> str:
    # 1. VERIFICAR SI ES PREGUNTA SOBRE IDENTIDAD
    identity_intent = is_identity_question(question)
    if identity_intent:
        return answer_identity(identity_intent, tone)
    
    # 2. SI NO HAY DATOS DE BD, INTENTAR RESPUESTA AGRÍCOLA
    if not rows or len(rows) == 0:
        agro_topic = detect_agro_topic(question)
        if agro_topic:
            return generate_agro_advice(agro_topic, question, tone)
        
        # Respuesta genérica cuando no hay datos ni es tema conocido
        fallback = f"No encontré datos en el sistema para responder tu pregunta. Como {MARIA_IDENTITY['nombre']}, puedo ayudarte con información general sobre agricultura, cultivos, manejo de fincas y comercio agrícola. ¿Podrías reformular tu pregunta o consultar sobre algún tema agrícola específico? 🌱"
        return fmt(fallback, tone)
    
    # 3. SI HAY DATOS, PARAFRASEAR SEGÚN INTENCIÓN
    intent = detect_intent(question, sql, rows)
    
    if lang.startswith("es"):
        subj = humanize_subject(question, sql, "registros")
        
        if intent == "count":
            n = 0
            if rows and len(rows) == 1 and rows[0]:
                first_val = list(rows[0].values())[0]
                try:
                    n = int(first_val)
                except Exception:
                    try:
                        n = float(first_val)
                    except Exception:
                        n = first_val
            
            # Parafraseo natural con contexto
            base = f"Según los datos del sistema, encontré {n} {subj}."
            
            # Agregar contexto agrícola si es relevante
            if "compr" in question.lower():
                base += f" Estos compradores son clave para tu red de comercialización. 🌾"
            elif "cultiv" in question.lower():
                base += f" Es importante monitorear el estado de todos tus cultivos. 🌱"
            
            follow = ""
            if suggest_followups:
                follow = f"\n\n¿Quieres que los liste con más detalle, filtre por alguna condición específica o analice tendencias?"
            return fmt(base + follow, tone)
        
        if intent == "list_short":
            headers = columns or list(rows[0].keys())
            preview = "\n".join(
                ["• " + ", ".join(f"{h}: {str(r.get(h,''))}" for h in headers) for r in rows[:10]]
            )
            base = f"He consultado los datos y aquí tienes {min(len(rows),10)} {subj}:\n\n{preview}"
            
            follow = ""
            if suggest_followups:
                follow = f"\n\n¿Necesitas que exporte estos datos, los agrupe de otra forma o aplique algún filtro adicional?"
            return fmt(base + follow, tone)
        
        # Tabla genérica
        headers = columns or list(rows[0].keys())
        head = join_cols(headers)
        sample = "\n".join(
            ["• " + ", ".join(f"{h}: {str(r.get(h,''))}" for h in headers) for r in rows[:5]]
        )
        base = f"Basándome en tu base de datos, te muestro un resumen de {subj} con las columnas: {head}\n\n{sample}\n\n(Mostrando {min(len(rows), 5)} de {len(rows)} registros totales)"
        
        follow = ""
        if suggest_followups:
            follow = "\n\n¿Te gustaría que ordene los datos de otra forma, calcule totales/promedios o filtre por fechas?"
        return fmt(base + follow, tone)
    
    # Inglés (básico)
    return fmt(f"Found {len(rows)} records in the database.", tone)

# ===== API ENDPOINTS =====
class RefineIn(BaseModel):
    question: str
    sql: str = ""
    columns: List[str] = []
    rows: List[Dict[str, Any]] = []
    lang: str = "es"
    tone: str = "amigable"
    suggest_followups: bool = True
    max_new_tokens: int = 192

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": MARIA_IDENTITY["nombre"],
        "version": "3.0",
        "description": MARIA_IDENTITY["descripcion"]
    }

@app.get("/identity")
def get_identity():
    """Endpoint para conocer información sobre MAR-IA"""
    return MARIA_IDENTITY

@app.post("/refine")
def refine(data: RefineIn):
    """
    Endpoint principal que maneja respuestas híbridas:
    - Parafrasea datos de BD cuando están disponibles
    - Proporciona conocimiento agrícola cuando no hay datos
    - Se identifica como MAR-IA cuando se le pregunta
    """
    answer = nlg_answer(
        question=data.question,
        sql=data.sql,
        columns=data.columns,
        rows=data.rows,
        lang=data.lang,
        tone=data.tone,
        suggest_followups=data.suggest_followups
    )
    return {
        "answer": answer,
        "source": "database" if data.rows else "knowledge_base",
        "assistant": MARIA_IDENTITY["nombre"]
    }

# ===== ENDPOINT DE PRUEBA =====
@app.post("/test-maria")
def test_maria(question: str, tone: str = "amigable"):
    """Endpoint para probar MAR-IA sin necesidad de SQL/datos"""
    answer = nlg_answer(
        question=question,
        sql="",
        columns=[],
        rows=[],
        lang="es",
        tone=tone,
        suggest_followups=True
    )
    return {"question": question, "answer": answer}
