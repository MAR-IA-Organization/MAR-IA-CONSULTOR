# -*- coding: utf-8 -*-
# app_gpt_maria.py - MAR-IA con NLG integrado
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
    },
    "fertilizantes": {
        "yara": {
            "descripcion": "Yara es una marca líder en fertilizantes y nutrición vegetal a nivel mundial",
            "productos_principales": [
                "YaraMila: Fertilizantes compuestos NPK para diversos cultivos",
                "YaraVera: Fertilizantes nitrogenados de alta calidad",
                "YaraLiva: Nitratos de calcio para nutrición balanceada",
                "YaraTera: Fertilizantes solubles para fertirriego",
                "YaraBela: Sulfato de amonio y nitrato de amonio"
            ],
            "ventajas": [
                "Alta solubilidad y disponibilidad de nutrientes",
                "Formulaciones específicas por cultivo",
                "Tecnología de liberación controlada",
                "Reducen pérdidas por lixiviación"
            ],
            "aplicaciones": {
                "cafe": "YaraMila COMPLEX 12-11-18 o YaraBela SULFAN para mantenimiento",
                "papa": "YaraMila HYDRAN para alto rendimiento",
                "maiz": "YaraVera AMIDAS para crecimiento vegetativo",
                "frutas": "YaraLiva CALCINIT para calidad y firmeza"
            }
        },
        "npk": {
            "n": "Nitrógeno - Crecimiento vegetativo, hojas verdes",
            "p": "Fósforo - Desarrollo de raíces y floración",
            "k": "Potasio - Resistencia y calidad de frutos"
        },
        "tipos": {
            "simples": "Un solo nutriente (urea, DAP, KCl)",
            "compuestos": "Varios nutrientes (NPK 10-20-20)",
            "organicos": "Compost, humus, gallinaza, bokashi",
            "foliares": "Aplicación en hojas para corrección rápida",
            "solubles": "Para fertirriego y sistemas hidropónicos"
        },
        "marcas_comunes": ["Yara", "Monómeros", "Abocol", "Agrosavia", "Nutrimon", "Fertilab"]
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
        "fertilizante_marca": ["yara", "yaramilas", "yaraliva", "yaratera", "monomeros", "abocol"],
        "plagas": ["plaga", "enfermedad", "insecto", "control", "fungicida", "pesticida"],
        "clima": ["clima", "temperatura", "lluvia", "sequia", "helada"],
        "precio": ["precio", "venta", "mercado", "comercio"]
    }
    
    for topic, keywords in topics.items():
        if any(kw in q for kw in keywords):
            return topic
    return None

def generate_fertilizer_advice(question: str) -> str:
    """Genera respuestas específicas sobre fertilizantes y marcas"""
    q = question.lower()
    fert_data = AGRO_KNOWLEDGE["fertilizantes"]
    
    # Detectar si pregunta por Yara específicamente
    if "yara" in q:
        yara = fert_data["yara"]
        
        # Pregunta sobre Yara en general
        if any(word in q for word in ["qué es", "que es", "cuéntame", "cuentame", "info"]):
            response = f"{yara['descripcion']}. 🌾\n\n"
            response += "**Líneas principales de Yara:**\n"
            for producto in yara["productos_principales"]:
                response += f"• {producto}\n"
            response += f"\n**Ventajas clave:**\n"
            for ventaja in yara["ventajas"]:
                response += f"✓ {ventaja}\n"
            return response
        
        # Pregunta sobre Yara para cultivo específico
        for cultivo in AGRO_KNOWLEDGE["cultivos_comunes"]:
            if cultivo in q:
                if cultivo in yara["aplicaciones"]:
                    return f"Para {cultivo}, te recomiendo {yara['aplicaciones'][cultivo]}. Estos productos de Yara están formulados específicamente para maximizar el rendimiento y calidad de este cultivo. 🌱"
                else:
                    return f"Para {cultivo}, Yara ofrece varias opciones. Los fertilizantes compuestos YaraMila son muy versátiles. Te recomiendo consultar con un distribuidor local para la fórmula NPK más adecuada según tu análisis de suelo."
        
        # Pregunta sobre producto específico de Yara
        productos_yara = ["yaramila", "yaravera", "yaraliva", "yaratera", "yarabela"]
        for producto in productos_yara:
            if producto in q:
                linea = producto.capitalize()
                for prod_desc in yara["productos_principales"]:
                    if linea in prod_desc:
                        return f"📦 {prod_desc}\n\nEste producto es ideal para asegurar una nutrición balanceada. ¿Para qué cultivo lo necesitas? Puedo darte recomendaciones más específicas."
        
        # Respuesta general sobre Yara
        return f"{yara['descripcion']}. Tienen una amplia gama de productos como YaraMila, YaraVera, YaraLiva y más. ¿Para qué cultivo necesitas el fertilizante?"
    
    # Preguntas sobre NPK
    if "npk" in q:
        npk = fert_data["npk"]
        return f"NPK son los tres macronutrientes esenciales:\n\n• **N (Nitrógeno)**: {npk['n']}\n• **P (Fósforo)**: {npk['p']}\n• **K (Potasio)**: {npk['k']}\n\nPor ejemplo, un fertilizante 10-20-20 contiene 10% de N, 20% de P y 20% de K. La fórmula ideal depende del cultivo y la etapa de desarrollo."
    
    # Preguntas sobre tipos de fertilizantes
    if any(word in q for word in ["tipos", "clases", "cuáles", "cuales"]):
        tipos = fert_data["tipos"]
        response = "Existen varios tipos de fertilizantes:\n\n"
        response += f"🔹 **Simples**: {tipos['simples']}\n"
        response += f"🔹 **Compuestos**: {tipos['compuestos']}\n"
        response += f"🔹 **Orgánicos**: {tipos['organicos']}\n"
        response += f"🔹 **Foliares**: {tipos['foliares']}\n"
        response += f"🔹 **Solubles**: {tipos['solubles']}\n"
        return response
    
    # Marcas comunes
    if "marca" in q or "cuál comprar" in q or "cual comprar" in q:
        marcas = ", ".join(fert_data["marcas_comunes"][:-1]) + f" y {fert_data['marcas_comunes'][-1]}"
        return f"Las marcas más reconocidas en Colombia incluyen: {marcas}. Yara es líder mundial, mientras que Monómeros y Abocol son muy usadas localmente. La elección depende de tu presupuesto, cultivo y disponibilidad en tu región."
    
    # Respuesta genérica sobre fertilizantes
    return "Los fertilizantes son esenciales para la nutrición de los cultivos. Puedo ayudarte con información sobre marcas como Yara, tipos de fertilizantes (NPK, orgánicos, foliares), o recomendaciones específicas por cultivo. ¿Qué necesitas saber?"

def generate_agro_advice(topic: str, question: str, tone: str) -> str:
    q = question.lower()
    
    # Detectar cultivo específico mencionado
    cultivo_mencionado = None
    for cultivo in AGRO_KNOWLEDGE["cultivos_comunes"]:
        if cultivo in q:
            cultivo_mencionado = cultivo
            break
    
    advice = {
        "cultivo": "Para un cultivo exitoso, considera: 1) Preparación adecuada del suelo, 2) Selección de semillas de calidad, 3) Época de siembra apropiada según tu región, 4) Manejo integrado durante el ciclo del cultivo.",
        
        "riego": "El riego eficiente requiere: considerar el tipo de suelo, la etapa del cultivo y las condiciones climáticas. El riego por goteo es muy eficiente para cultivos en hileras, mientras que la aspersión funciona bien para cultivos extensivos.",
        
        "fertilizacion": "La fertilización debe basarse en análisis de suelo. En general, los cultivos necesitan Nitrógeno (N) para crecimiento vegetativo, Fósforo (P) para raíces y floración, y Potasio (K) para resistencia y calidad de frutos.",
        
        "fertilizante_marca": generate_fertilizer_advice(question),
        
        "plagas": "El Manejo Integrado de Plagas (MIP) es la mejor estrategia: monitoreo regular, control cultural (rotación, limpieza), control biológico cuando sea posible, y uso racional de agroquímicos solo cuando sea necesario.",
        
        "clima": "El clima es crucial para la agricultura. Monitorea las condiciones meteorológicas, planifica según las temporadas de lluvia, y considera prácticas de conservación de agua para épocas secas.",
        
        "precio": "Los precios agrícolas varían según oferta/demanda, temporada y calidad del producto. Te recomiendo consultar los datos de tus registros o contactar con cooperativas agrícolas locales para información actualizada."
    }
    
    response = advice.get(topic, "Puedo ayudarte con información sobre agricultura. ¿Podrías ser más específico sobre lo que necesitas?")
    
    # Agregar nota sobre datos disponibles
    note = "\n\n💡 Si tienes datos específicos en tu sistema sobre productos o inventarios, puedo consultarlos para darte información más precisa."
    
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

# ===== VALIDACIÓN DE RESPUESTAS DE BD =====
def is_valid_db_response(rows: List[Dict[str, Any]], sql: str, question: str) -> bool:
    """
    Determina si la respuesta de BD es válida/útil o si debemos usar conocimiento de GPT
    """
    # 1. Sin filas = respuesta vacía
    if not rows or len(rows) == 0:
        return False
    
    # 2. SQL sospechoso (SELECT literal hardcodeado)
    sql_lower = (sql or "").lower()
    if "select '" in sql_lower or 'select "' in sql_lower:
        # Detectar si es un valor hardcodeado como "SELECT 'iphone' AS answer"
        return False
    
    # 3. Una sola fila con valor genérico/no útil
    if len(rows) == 1:
        first_row = rows[0]
        
        # Obtener el primer valor
        if first_row:
            first_value = list(first_row.values())[0] if first_row.values() else None
            
            # Valores que indican "no hay datos reales"
            non_useful_values = [
                None, "", "null", "none", "n/a", "no data",
                "iphone", "test", "example", "placeholder"
            ]
            
            if first_value:
                value_str = str(first_value).lower().strip()
                
                # Si el valor es genérico/placeholder
                if value_str in non_useful_values:
                    return False
                
                # Si el valor parece ser la pregunta repetida
                q_words = set(question.lower().split())
                v_words = set(value_str.split())
                if len(q_words & v_words) > 2:  # Muchas palabras en común
                    return False
    
    # 4. Verificar si las columnas tienen nombres genéricos
    if rows:
        first_row = rows[0]
        generic_cols = ["answer", "result", "output", "response", "value"]
        
        if len(first_row) == 1:
            col_name = list(first_row.keys())[0].lower()
            if col_name in generic_cols:
                # Columna genérica = probablemente placeholder
                return False
    
    # Si pasó todas las validaciones, es respuesta válida
    return True

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
    
    # 2. VALIDAR SI LA RESPUESTA DE BD ES ÚTIL
    has_valid_data = is_valid_db_response(rows, sql, question)
    
    # 3. SI NO HAY DATOS VÁLIDOS, USAR CONOCIMIENTO GPT
    if not has_valid_data:
        agro_topic = detect_agro_topic(question)
        if agro_topic:
            return generate_agro_advice(agro_topic, question, tone)
        
        # Respuesta genérica cuando no hay datos ni es tema conocido
        fallback = f"No encontré información específica en el sistema sobre '{question}'. "
        fallback += f"Como {MARIA_IDENTITY['nombre']}, puedo ayudarte con:\n\n"
        fallback += "🌱 Cultivos y técnicas agrícolas\n"
        fallback += "💧 Riego y fertilización (incluye Yara y otras marcas)\n"
        fallback += "🐛 Control de plagas\n"
        fallback += "📊 Análisis de datos agrícolas\n\n"
        fallback += "¿Sobre qué tema agrícola te gustaría saber más?"
        return fmt(fallback, tone)
    
    # 4. SI HAY DATOS VÁLIDOS, PARAFRASEAR SEGÚN INTENCIÓN
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
    - Valida si los datos de BD son útiles o placeholders
    - Parafrasea datos reales de BD cuando están disponibles
    - Proporciona conocimiento agrícola cuando no hay datos válidos
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
    
    # Determinar fuente de la respuesta
    has_valid_data = is_valid_db_response(data.rows, data.sql, data.question)
    source = "database" if has_valid_data else "knowledge_base"
    
    return {
        "answer": answer,
        "source": source,
        "assistant": MARIA_IDENTITY["nombre"],
        "data_validated": has_valid_data
    }

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
