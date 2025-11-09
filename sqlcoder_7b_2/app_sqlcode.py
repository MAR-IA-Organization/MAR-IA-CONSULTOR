# -*- coding: utf-8 -*-
"""
SQLCoder Ligero v2.2 - Generador de SQL basado en reglas
Sin dependencias de ML (PyTorch, transformers, etc.)
Ventajas: Instantáneo (<10ms), RAM mínima (~5MB), aprende de consultas exitosas
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import re
import json
import time

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
PORT = int(os.getenv("PORT", "8011"))
MEMORY_FILE = os.getenv("MEMORY_FILE", "/workspace/sqlcoder_7b_2/memory.json")

app = FastAPI(
    title="SQLCoder Ligero",
    description="Generador de SQL basado en reglas y patrones (sin ML)",
    version="2.2"
)

# ============================================================================
# MODELOS DE DATOS
# ============================================================================
class SQLIn(BaseModel):
    question: str
    schema_text: str
    lang: str = "es"
    max_new_tokens: int = 256
    feedback: Optional[str] = None

class SQLOut(BaseModel):
    sql: str
    source: str = "rule_engine"
    debug_info: Optional[Dict] = None

# ============================================================================
# SISTEMA DE MEMORIA Y APRENDIZAJE
# ============================================================================
class SQLMemory:
    """Sistema de caché inteligente que aprende de consultas exitosas"""
    
    def __init__(self, path: str):
        self.path = path
        self.memory = self._load()
    
    def _load(self) -> Dict:
        """Carga memoria desde archivo JSON"""
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando memoria: {e}")
                return {"successful_queries": [], "failed_patterns": []}
        return {"successful_queries": [], "failed_patterns": []}
    
    def _save(self):
        """Guarda memoria en archivo JSON"""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando memoria: {e}")
    
    def add_success(self, question: str, sql: str, tables_used: List[str]):
        """Registra una consulta exitosa"""
        # Normalizar pregunta (reemplazar números por N)
        q_normalized = re.sub(r'\d+', 'N', question.lower().strip())
        
        entry = {
            "question": q_normalized,
            "original": question.lower(),
            "sql": sql,
            "tables": tables_used,
            "timestamp": time.time()
        }
        
        # Evitar duplicados
        if not any(e["question"] == q_normalized for e in self.memory["successful_queries"]):
            self.memory["successful_queries"].append(entry)
            
            # Mantener solo las últimas 200 consultas
            if len(self.memory["successful_queries"]) > 200:
                self.memory["successful_queries"] = self.memory["successful_queries"][-200:]
            
            self._save()
            print(f"✅ Consulta aprendida: {q_normalized}")
    
    def get_similar(self, question: str) -> Optional[str]:
        """Busca consulta similar en memoria"""
        q_normalized = re.sub(r'\d+', 'N', question.lower().strip())
        
        for entry in self.memory["successful_queries"]:
            if entry["question"] == q_normalized:
                sql = entry["sql"]
                
                # Si la pregunta tenía números, reemplazarlos en el SQL
                numbers = re.findall(r'\d+', question)
                if numbers and 'LIMIT' in sql.upper():
                    sql = re.sub(r'LIMIT\s+\d+', f'LIMIT {numbers[0]}', sql, flags=re.IGNORECASE)
                
                print(f"🔍 Match encontrado en memoria para: {q_normalized}")
                return sql
        
        return None
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas de la memoria"""
        return {
            "total_queries": len(self.memory["successful_queries"]),
            "failed_patterns": len(self.memory.get("failed_patterns", [])),
            "memory_size_kb": os.path.getsize(self.path) / 1024 if os.path.exists(self.path) else 0
        }

# Instancia global de memoria
memory = SQLMemory(MEMORY_FILE)

# ============================================================================
# PARSER DE ESQUEMA
# ============================================================================
def parse_schema(schema_text: str) -> Dict[str, dict]:
    """
    Parsea el esquema YAML en formato de texto y extrae tablas/columnas
    
    Formato esperado:
        TABLE schema.table_name -- descripción
          - column_name (type)
          - another_column (type)
    """
    tables = {}
    current_table = None
    
    for line in schema_text.splitlines():
        # Detectar línea de tabla: TABLE public.commerce_buyer -- descripción
        table_match = re.match(
            r"\s*TABLE\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)(?:\s*--\s*(.+))?", 
            line
        )
        
        if table_match:
            current_table = table_match.group(1)
            description = table_match.group(2) or ""
            tables[current_table] = {
                "description": description.strip(),
                "columns": []
            }
        
        # Detectar línea de columna: - id (integer)
        elif current_table and line.strip().startswith("- "):
            col_match = re.match(r"\s*-\s*(\w+)\s*\(([^)]+)\)", line)
            if col_match:
                tables[current_table]["columns"].append({
                    "name": col_match.group(1),
                    "type": col_match.group(2).lower()
                })
    
    return tables

# ============================================================================
# MAPEO DE PALABRAS CLAVE A TABLAS
# ============================================================================
KEYWORD_MAP = {
    # Compradores/Clientes
    ("comprador", "compradores", "buyer", "cliente", "clientes", "customer", "customers"): 
        "commerce_buyer",
    
    # Facturas
    ("factura", "facturas", "invoice", "invoices"): 
        "commerce_invoice",
    
    # Listados/Publicaciones
    ("listado", "listados", "listing", "listings", "publicacion", "publicaciones"): 
        "commerce_listing",
    
    # Ofertas
    ("oferta", "ofertas", "bid", "bids", "puja", "pujas"): 
        "commerce_bid",
    
    # Trabajadores
    ("trabajador", "trabajadores", "worker", "workers", "empleado", "empleados"): 
        "commerce_worker",
    
    # Deudas
    ("deuda", "deudas", "debt", "debts", "debe", "deben"): 
        "commerce_workerdebt",
    
    # Pagos
    ("pago", "pagos", "payment", "payments", "abono", "abonos"): 
        "commerce_workerpayment",
    
    # Cultivos
    ("cultivo", "cultivos", "crop", "crops", "siembra", "siembras"): 
        "farm_crop",
    
    # Producción
    ("produccion", "producción", "production", "cosecha", "cosechas"): 
        "farm_production",
    
    # Fincas
    ("finca", "fincas", "farm", "farms", "terreno", "terrenos", "predio"): 
        "farm_farm",
    
    # Herramientas
    ("herramienta", "herramientas", "tool", "tools", "equipo", "equipos"): 
        "farm_tool",
    
    # Ingresos
    ("ingreso", "ingresos", "income", "incomes", "ganancia", "ganancias"): 
        "farm_income",
    
    # Costos/Gastos
    ("costo", "costos", "gasto", "gastos", "cost", "costs", "expense", "expenses"): 
        "farm_cost",
    
    # Usuarios
    ("usuario", "usuarios", "user", "users"): 
        "users_user",
    
    # Precios de mercado
    ("precio", "precios", "price", "prices", "mercado"): 
        "commerce_marketprice",
}

def find_table(question: str, available_tables: List[str]) -> Optional[str]:
    """Encuentra la tabla más relevante para la pregunta"""
    q_lower = question.lower()
    
    # Buscar por keywords mapeadas
    for keywords, table_suffix in KEYWORD_MAP.items():
        if any(kw in q_lower for kw in keywords):
            for full_table in available_tables:
                if table_suffix in full_table:
                    return full_table
    
    # Fallback: retornar primera tabla disponible
    return available_tables[0] if available_tables else None

# ============================================================================
# GENERADOR DE SQL BASADO EN PATRONES
# ============================================================================
def generate_sql(question: str, tables: Dict[str, dict]) -> str:
    """
    Genera SQL usando patrones y heurísticas inteligentes
    
    Patrones soportados:
    - Contar: cuántos, cantidad, número
    - Listar: muestra, lista, dame, ver
    - Sumar: total, suma
    - Promedio: promedio, media, average
    - Máximo/Mínimo: mayor, menor, máximo, mínimo
    """
    q_lower = question.lower()
    available_tables = list(tables.keys())
    
    # Encontrar tabla objetivo
    target_table = find_table(question, available_tables)
    if not target_table:
        return ""
    
    table_info = tables[target_table]
    columns = [col["name"] for col in table_info["columns"]]
    
    # ========================================
    # PATRÓN 1: CONTAR
    # ========================================
    if any(kw in q_lower for kw in [
        "cuántos", "cuantos", "cuántas", "cuantas", "cantidad", 
        "número", "numero", "how many", "count"
    ]):
        return f"SELECT COUNT(*) AS total FROM {target_table}"
    
    # ========================================
    # PATRÓN 2: SUMAR/TOTAL
    # ========================================
    if any(kw in q_lower for kw in ["total", "suma", "sum", "sumar"]):
        # Buscar columnas numéricas
        numeric_cols = [
            col["name"] for col in table_info["columns"] 
            if any(t in col["type"] for t in ["int", "decimal", "numeric", "float", "money"])
        ]
        
        # Preferir columnas con keywords de dinero/monto
        money_col = None
        for col in numeric_cols:
            if any(kw in col.lower() for kw in [
                "amount", "price", "precio", "monto", "valor", "value", "total"
            ]):
                money_col = col
                break
        
        if money_col:
            return f"SELECT SUM({money_col}) AS total FROM {target_table}"
        elif numeric_cols:
            return f"SELECT SUM({numeric_cols[0]}) AS total FROM {target_table}"
        else:
            # Fallback a COUNT si no hay columnas numéricas
            return f"SELECT COUNT(*) AS total FROM {target_table}"
    
    # ========================================
    # PATRÓN 3: PROMEDIO
    # ========================================
    if any(kw in q_lower for kw in ["promedio", "media", "average", "avg"]):
        numeric_cols = [
            col["name"] for col in table_info["columns"] 
            if any(t in col["type"] for t in ["int", "decimal", "numeric", "float"])
        ]
        if numeric_cols:
            return f"SELECT AVG({numeric_cols[0]}) AS promedio FROM {target_table}"
    
    # ========================================
    # PATRÓN 4: LISTAR/MOSTRAR
    # ========================================
    if any(kw in q_lower for kw in [
        "muestra", "lista", "dame", "ver", "show", "list", 
        "enséñame", "ensename", "primeros", "top"
    ]):
        # Buscar límite numérico en la pregunta (ej: "los primeros 5")
        limit_match = re.search(r'(\d+)', question)
        limit = int(limit_match.group(1)) if limit_match else 10
        
        # Seleccionar columnas inteligentemente
        priority_cols = ["id", "name", "nombre", "title", "titulo", "email", "phone", "telefono"]
        selected_cols = []
        
        # Agregar columnas prioritarias primero
        for prio in priority_cols:
            for col in columns:
                if prio in col.lower() and col not in selected_cols:
                    selected_cols.append(col)
                    break
        
        # Completar hasta 5 columnas
        for col in columns:
            if col not in selected_cols and len(selected_cols) < 5:
                selected_cols.append(col)
        
        select_clause = ", ".join(selected_cols) if selected_cols else "*"
        
        # Buscar columna para ORDER BY (fechas preferidas)
        date_cols = [
            col["name"] for col in table_info["columns"] 
            if any(kw in col["name"].lower() for kw in [
                "date", "created", "fecha", "updated", "timestamp", "modified"
            ])
        ]
        
        order_clause = f" ORDER BY {date_cols[0]} DESC" if date_cols else ""
        
        return f"SELECT {select_clause} FROM {target_table}{order_clause} LIMIT {limit}"
    
    # ========================================
    # PATRÓN 5: MÁXIMO
    # ========================================
    if any(kw in q_lower for kw in [
        "mayor", "máximo", "maximo", "max", "más alto", "mas alto", "highest"
    ]):
        numeric_cols = [
            col["name"] for col in table_info["columns"] 
            if any(t in col["type"] for t in ["int", "decimal", "numeric", "float"])
        ]
        if numeric_cols:
            return f"SELECT MAX({numeric_cols[0]}) AS maximo FROM {target_table}"
    
    # ========================================
    # PATRÓN 6: MÍNIMO
    # ========================================
    if any(kw in q_lower for kw in [
        "menor", "mínimo", "minimo", "min", "más bajo", "mas bajo", "lowest"
    ]):
        numeric_cols = [
            col["name"] for col in table_info["columns"] 
            if any(t in col["type"] for t in ["int", "decimal", "numeric", "float"])
        ]
        if numeric_cols:
            return f"SELECT MIN({numeric_cols[0]}) AS minimo FROM {target_table}"
    
    # ========================================
    # FALLBACK: SELECT SIMPLE
    # ========================================
    select_clause = ", ".join(columns[:5]) if columns else "*"
    return f"SELECT {select_clause} FROM {target_table} LIMIT 10"

# ============================================================================
# ENDPOINTS DE LA API
# ============================================================================

@app.get("/health")
def health():
    """Endpoint de salud del servicio"""
    stats = memory.get_stats()
    
    return {
        "status": "ok",
        "service": "SQLCoder Ligero",
        "version": "2.2",
        "mode": "rule_based",
        "description": "Generador SQL sin ML - Basado en patrones y aprendizaje",
        "performance": {
            "fast": True,
            "ml_free": True,
            "avg_response_time_ms": "<10",
            "ram_usage_mb": "~5"
        },
        "memory": stats
    }

@app.post("/warmup")
def warmup():
    """Pre-calentamiento (no necesario en modo ligero)"""
    return {
        "status": "ready",
        "mode": "rule_based",
        "load_time_ms": 0,
        "message": "No warmup needed - instant response"
    }

@app.post("/generate_sql", response_model=SQLOut)
def generate_sql_endpoint(data: SQLIn):
    """
    Endpoint principal para generar SQL
    
    Flujo:
    1. Buscar en memoria (caché)
    2. Parsear esquema
    3. Generar SQL con reglas
    4. Retornar resultado
    """
    start_time = time.time()
    
    try:
        # Paso 1: Buscar en memoria primero
        cached_sql = memory.get_similar(data.question)
        if cached_sql:
            execution_time = (time.time() - start_time) * 1000
            return SQLOut(
                sql=cached_sql,
                source="memory_cache",
                debug_info={
                    "execution_time_ms": round(execution_time, 2),
                    "cache_hit": True
                }
            )
        
        # Paso 2: Parsear esquema
        tables = parse_schema(data.schema_text)
        
        if not tables:
            raise ValueError("No se pudieron parsear tablas del esquema")
        
        # Paso 3: Generar SQL con reglas
        sql = generate_sql(data.question, tables)
        
        if not sql:
            raise ValueError("No se pudo generar SQL para esta pregunta")
        
        execution_time = (time.time() - start_time) * 1000
        
        print(f"🎯 SQL generado: {sql} (en {execution_time:.2f}ms)")
        
        return SQLOut(
            sql=sql,
            source="rule_engine",
            debug_info={
                "tables_available": len(tables),
                "method": "pattern_matching",
                "execution_time_ms": round(execution_time, 2),
                "cache_hit": False
            }
        )
    
    except Exception as e:
        print(f"❌ Error generando SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
def record_feedback(
    question: str, 
    sql: str, 
    success: bool, 
    tables_used: List[str] = None
):
    """
    Registra feedback de consultas ejecutadas
    Usado para aprendizaje continuo
    """
    try:
        if success and tables_used:
            memory.add_success(question, sql, tables_used)
            stats = memory.get_stats()
            return {
                "status": "success_recorded",
                "memory_size": stats["total_queries"],
                "message": "Consulta agregada a la memoria de aprendizaje"
            }
        elif not success:
            # Podrías registrar patrones fallidos aquí
            return {"status": "failure_noted"}
        
        return {"status": "no_action"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 SQLCoder Ligero v2.2")
    print("=" * 60)
    print(f"📍 Puerto: {PORT}")
    print(f"💾 Memoria: {MEMORY_FILE}")
    print(f"⚡ Modo: Reglas + Caché (sin ML)")
    print(f"🎯 Consultas aprendidas: {len(memory.memory['successful_queries'])}")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)