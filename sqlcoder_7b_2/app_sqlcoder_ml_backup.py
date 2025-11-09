# -*- coding: utf-8 -*-
# OPCIÓN LIGERA: Usa un modelo más pequeño o reglas heurísticas
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os, re, json

# ---------- Config ----------
TITLE = "SQLCoder Ligero (Reglas + Plantillas)"
PORT = int(os.getenv("PORT", "8011"))
MEMORY_FILE = os.getenv("MEMORY_FILE", "/workspace/sqlcoder_7b_2/memory.json")

app = FastAPI(title=TITLE, version="2.2")

class SQLIn(BaseModel):
    question: str
    schema_text: str
    lang: str = "es"
    max_new_tokens: int = 256
    feedback: Optional[str] = None

class SQLMemory:
    def __init__(self, path: str):
        self.path = path
        self.memory = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"successful_queries": [], "failed_patterns": []}
        return {"successful_queries": [], "failed_patterns": []}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)

    def add_success(self, question: str, sql: str, tables_used: List[str]):
        entry = {"question": question.lower(), "sql": sql, "tables": tables_used}
        if not any(e["question"] == entry["question"] for e in self.memory["successful_queries"]):
            self.memory["successful_queries"].append(entry)
            if len(self.memory["successful_queries"]) > 100:
                self.memory["successful_queries"] = self.memory["successful_queries"][-100:]
            self._save()

    def get_exact_match(self, question: str) -> Optional[str]:
        q_lower = question.lower().strip()
        for entry in self.memory["successful_queries"]:
            if entry["question"] == q_lower:
                return entry["sql"]
        return None

memory = SQLMemory(MEMORY_FILE)

# ---------- Extractor de tablas del esquema ----------
def extract_tables_from_schema(schema_text: str):
    """Extrae tabla -> columnas del esquema"""
    tables = {}
    current_table = None
    
    for line in schema_text.splitlines():
        # Detectar tabla
        table_match = re.match(r"\s*TABLE\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)", line)
        if table_match:
            current_table = table_match.group(1)
            tables[current_table] = []
        # Detectar columna
        elif current_table and line.strip().startswith("- "):
            col_match = re.match(r"\s*-\s*(\w+)", line)
            if col_match:
                tables[current_table].append(col_match.group(1))
    
    return tables

# ---------- Mapeo de palabras clave a tablas ----------
KEYWORD_TO_TABLE = {
    # Compradores
    "comprador": "commerce_buyer",
    "compradores": "commerce_buyer",
    "buyer": "commerce_buyer",
    "cliente": "commerce_buyer",
    "clientes": "commerce_buyer",
    
    # Facturas
    "factura": "commerce_invoice",
    "facturas": "commerce_invoice",
    "invoice": "commerce_invoice",
    
    # Listados
    "listado": "commerce_listing",
    "listing": "commerce_listing",
    
    # Ofertas
    "oferta": "commerce_bid",
    "ofertas": "commerce_bid",
    "bid": "commerce_bid",
    
    # Trabajadores
    "trabajador": "commerce_worker",
    "trabajadores": "commerce_worker",
    "worker": "commerce_worker",
    
    # Cultivos
    "cultivo": "farm_crop",
    "cultivos": "farm_crop",
    "crop": "farm_crop",
    
    # Producción
    "produccion": "farm_production",
    "production": "farm_production",
    
    # Fincas
    "finca": "farm_farm",
    "fincas": "farm_farm",
    "farm": "farm_farm",
}

def detect_table_from_question(question: str, available_tables: List[str]) -> Optional[str]:
    """Detecta qué tabla menciona la pregunta"""
    q_lower = question.lower()
    
    # Buscar palabras clave
    for keyword, table_name in KEYWORD_TO_TABLE.items():
        if keyword in q_lower:
            # Buscar tabla completa (con schema)
            for full_table in available_tables:
                if table_name in full_table:
                    return full_table
    
    return None

# ---------- Generador de SQL basado en reglas ----------
def generate_sql_rule_based(question: str, tables_info: dict) -> str:
    """Genera SQL usando reglas simples"""
    q_lower = question.lower()
    available_tables = list(tables_info.keys())
    
    # Detectar tabla objetivo
    target_table = detect_table_from_question(question, available_tables)
    
    if not target_table:
        # Fallback: usar primera tabla disponible
        target_table = available_tables[0] if available_tables else "public.unknown"
    
    columns = tables_info.get(target_table, ["*"])
    
    # Patrón 1: Contar (cuántos, cantidad)
    if any(kw in q_lower for kw in ["cuántos", "cuantos", "cantidad", "número", "numero", "how many"]):
        return f"SELECT COUNT(*) AS total FROM {target_table}"
    
    # Patrón 2: Listar (mostrar, lista, dame)
    if any(kw in q_lower for kw in ["muestra", "lista", "dame", "ver", "show", "list"]):
        # Buscar límite numérico
        limit_match = re.search(r'(\d+)', question)
        limit = int(limit_match.group(1)) if limit_match else 10
        
        # Seleccionar columnas relevantes (máximo 5)
        select_cols = ", ".join(columns[:5]) if columns and columns[0] != "*" else "*"
        
        # Buscar columna de fecha para ordenar
        order_col = None
        for col in columns:
            if any(date_kw in col.lower() for date_kw in ["date", "created", "fecha", "timestamp"]):
                order_col = col
                break
        
        order_clause = f" ORDER BY {order_col} DESC" if order_col else ""
        return f"SELECT {select_cols} FROM {target_table}{order_clause} LIMIT {limit}"
    
    # Patrón 3: Sumar/Total
    if any(kw in q_lower for kw in ["total", "suma", "sum"]):
        # Buscar columna numérica
        numeric_col = None
        for col in columns:
            if any(num_kw in col.lower() for num_kw in ["amount", "price", "precio", "monto", "value", "valor"]):
                numeric_col = col
                break
        
        if numeric_col:
            return f"SELECT SUM({numeric_col}) AS total FROM {target_table}"
        else:
            return f"SELECT COUNT(*) AS total FROM {target_table}"
    
    # Patrón 4: Promedio
    if any(kw in q_lower for kw in ["promedio", "media", "average", "avg"]):
        numeric_col = None
        for col in columns:
            if any(num_kw in col.lower() for num_kw in ["amount", "price", "precio", "monto", "value", "valor"]):
                numeric_col = col
                break
        
        if numeric_col:
            return f"SELECT AVG({numeric_col}) AS promedio FROM {target_table}"
    
    # Fallback: SELECT simple
    select_cols = ", ".join(columns[:5]) if columns and columns[0] != "*" else "*"
    return f"SELECT {select_cols} FROM {target_table} LIMIT 10"

# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "rule_based",
        "description": "SQL generator using pattern matching (no ML model)",
        "memory_examples": len(memory.memory["successful_queries"]),
        "fast": True
    }

@app.post("/warmup")
def warmup():
    return {"status": "ready", "mode": "rule_based"}

@app.post("/generate_sql")
def generate_sql(data: SQLIn):
    try:
        # Buscar match exacto en memoria
        exact_match = memory.get_exact_match(data.question)
        if exact_match:
            print(f"✅ Match exacto encontrado en memoria")
            return {"sql": exact_match, "source": "memory"}
        
        # Extraer info del esquema
        tables_info = extract_tables_from_schema(data.schema_text)
        
        if not tables_info:
            return {
                "sql": "",
                "error": "No se pudo parsear el esquema"
            }
        
        # Generar SQL con reglas
        sql = generate_sql_rule_based(data.question, tables_info)
        
        print(f"🎯 SQL generado: {sql}")
        
        return {
            "sql": sql,
            "source": "rule_based",
            "debug_info": {
                "tables_found": len(tables_info),
                "method": "pattern_matching"
            }
        }
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"sql": "", "error": str(e)}

@app.post("/feedback")
def record_feedback(question: str, sql: str, success: bool, tables_used: List[str] = None):
    try:
        if success and tables_used:
            memory.add_success(question, sql, tables_used)
            return {"status": "success_recorded"}
        return {"status": "no_action"}
    except Exception as e:
        return {"status": "error", "message": str(e)}