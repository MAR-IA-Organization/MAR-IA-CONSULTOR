# app_connector.py - VERSIÓN CORREGIDA Y OPTIMIZADA
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os, re, yaml, requests, difflib
import psycopg2, psycopg2.extras
from typing import Optional, Set, List, Dict, Tuple
from contextlib import contextmanager
import logging
from fastapi.middleware.cors import CORSMiddleware

# ====== CONFIGURACIÓN DE LOGGING ======
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== CONFIG CON VALIDACIÓN ======
SQLCODER_URL = os.getenv("SQLCODER_URL", "http://127.0.0.1:8011/generate_sql")
NLG_URL      = os.getenv("NLG_URL", "http://127.0.0.1:8002/refine")
SCHEMA_PATH  = os.getenv("SCHEMA_PATH", "/workspace/api/conector/schema_catalog.yaml")

# Variables críticas de PostgreSQL
PG_HOST = os.getenv("PG_HOST")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB")
PG_USER = os.getenv("PG_USER")
PG_PASS = os.getenv("PG_PASS")
PG_SSL  = os.getenv("PG_SSLMODE", "prefer")

MAX_RETRIES = 3
SQLCODER_TIMEOUT = int(os.getenv("SQLCODER_TIMEOUT", "180"))  # Timeout configurable
MAX_ROWS_LIMIT = 1000  # Límite de seguridad

# Validación de configuración al inicio
def validate_config():
    """Valida que todas las variables críticas estén configuradas"""
    missing = []
    if not PG_HOST: missing.append("PG_HOST")
    if not PG_DB: missing.append("PG_DB")
    if not PG_USER: missing.append("PG_USER")
    if not PG_PASS: missing.append("PG_PASS")
    
    if missing:
        raise RuntimeError(f"❌ Variables de entorno faltantes: {', '.join(missing)}")
    
    if not os.path.exists(SCHEMA_PATH):
        raise RuntimeError(f"❌ Archivo de esquema no encontrado: {SCHEMA_PATH}")
    
    logger.info("✅ Configuración validada correctamente")

app = FastAPI(title="Conector SQLCoder+NLG v2.2", version="2.2")

# ====== CONFIGURAR CORS ======

# ====== CONFIGURAR CORS ======
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://agro.dagi.digital",
        "http://localhost:5173",  # Para desarrollo local
        "http://localhost:3000"
    ],
    allow_credentials=False,  # Cambiado a False (conflicto con allow_origins=["*"])
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["*"],
    max_age=3600
)

# ====== CONTEXT MANAGER PARA CONEXIONES DB ======
@contextmanager
def get_db_connection():
    """Context manager para manejar conexiones de forma segura"""
    conn = None
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASS,
            sslmode=PG_SSL,
            connect_timeout=10
        )
        yield conn
    except psycopg2.OperationalError as e:
        logger.error(f"❌ Error de conexión a PostgreSQL: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"No se puede conectar a la base de datos: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

# ====== UTILIDADES DE ESQUEMA / SQL ======
def load_schema_text(path: str) -> str:
    """Carga el esquema desde YAML con manejo de errores"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"❌ Error cargando esquema: {e}")
        raise HTTPException(status_code=500, detail=f"Error cargando esquema: {e}")
    
    lines: List[str] = []
    for db in data.get("databases", []):
        for sch in db.get("schemas", []):
            sname = sch.get("name", "public")
            for t in sch.get("tables", []):
                tname = f'{sname}.{t.get("name","")}'
                tdesc = t.get("description","") or ""
                lines.append(f"TABLE {tname} -- {tdesc}".strip())
                for c in t.get("columns", []):
                    cname = c.get('name', '')
                    ctype = c.get('type', '')
                    if cname and ctype:
                        lines.append(f"  - {cname} ({ctype})")
    
    schema_text = "\n".join(lines)[:20000]
    logger.info(f"📚 Esquema cargado: {len(lines)} líneas")
    return schema_text

def allowed_tables_from_yaml(path: str) -> Set[str]:
    """Extrae todas las tablas permitidas del YAML"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"❌ Error leyendo tablas permitidas: {e}")
        return set()
    
    tabs: Set[str] = set()
    for db in data.get("databases", []):
        for sch in db.get("schemas", []):
            sname = (sch.get("name") or "public").lower()
            for t in sch.get("tables", []):
                tname = (t.get("name") or "").lower()
                if tname:
                    tabs.add(f"{sname}.{tname}")
    
    logger.info(f"📋 Tablas permitidas: {len(tabs)}")
    return tabs

def normalize_schema_dots(sql: str) -> str:
    """Normaliza espacios alrededor de puntos en nombres de tablas"""
    if not sql:
        return ""
    
    # Eliminar espacios alrededor de puntos
    sql = re.sub(r'([a-zA-Z0-9_]+)\s*\.\s*([a-zA-Z0-9_]+)', r'\1.\2', sql)
    
    # Normalizar referencias FROM/JOIN
    def norm(m):
        kw = m.group(1)
        schema = m.group(2).lower()
        table = m.group(3).lower()
        rest = m.group(4) or ""
        return f"{kw} {schema}.{table}{rest}"
    
    sql = re.sub(
        r'(?i)\b(FROM|JOIN)\s+([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)(\s+(?:AS\s+)?[a-zA-Z0-9_]+)?',
        norm,
        sql
    )
    
    return sql.strip()

def tables_in_sql(sql: str) -> Set[str]:
    """Extrae todas las tablas referenciadas en el SQL"""
    if not sql:
        return set()
    
    tables = set()
    
    # Patrón mejorado que captura más casos
    patterns = [
        r'(?i)\b(?:FROM|JOIN)\s+([a-z0-9_]+)\.([a-z0-9_]+)\b',
        r'(?i)\bINTO\s+([a-z0-9_]+)\.([a-z0-9_]+)\b',
        r'(?i)\bUPDATE\s+([a-z0-9_]+)\.([a-z0-9_]+)\b',
    ]
    
    for pattern in patterns:
        for m in re.finditer(pattern, sql):
            schema = m.group(1).lower()
            table = m.group(2).lower()
            tables.add(f"{schema}.{table}")
    
    return tables

def verify_tables_exist(conn, tables: Set[str]) -> List[str]:
    """Verifica que las tablas existan en la base de datos"""
    missing: List[str] = []
    
    with conn.cursor() as cur:
        for t in tables:
            if '.' not in t:
                logger.warning(f"⚠️ Tabla sin esquema: {t}")
                continue
            
            schema, table = t.split(".", 1)
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema=%s AND table_name=%s
                )
            """, (schema, table))
            
            if not cur.fetchone()[0]:
                missing.append(t)
    
    if missing:
        logger.warning(f"⚠️ Tablas no encontradas en BD: {missing}")
    
    return missing

# ====== ALIASES Y CORRECCIONES ======
ALIASES: Dict[str, str] = {
    "public.commerce_buyers": "public.commerce_buyer",
    "public.customer": "public.commerce_buyer",
    "public.customers": "public.commerce_buyer",
    "public.user": "public.users_user",
    "public.company": "public.commerce_buyer",
    "public.invoice": "public.commerce_invoice",
    "public.invoices": "public.commerce_invoice",
    "public.factura": "public.commerce_invoice",
    "public.facturas": "public.commerce_invoice",
    "public.comprador": "public.commerce_buyer",
    "public.compradores": "public.commerce_buyer",
    "public.listings": "public.commerce_listing",
    "public.trabajadores": "public.commerce_worker",
    "public.deudas": "public.commerce_workerdebt",
    "public.pagos": "public.commerce_workerpayment",
    "public.cultivos": "public.farm_crop",
    "public.produccion": "public.farm_production",
    "public.producciones": "public.farm_production",
    "public.fincas": "public.farm_farm",
    "public.herramientas": "public.farm_tool",
    "public.ingresos": "public.farm_income",
    "public.costos": "public.farm_cost",
}

def singularize(name: str) -> str:
    """Convierte plural a singular de forma simple"""
    if len(name) <= 1:
        return name
    
    if name.endswith("ies") and len(name) > 3:
        return name[:-3] + "y"
    if name.endswith("ses") and len(name) > 3:
        return name[:-2]
    if name.endswith("es") and len(name) > 2:
        return name[:-2]
    if name.endswith("s"):
        return name[:-1]
    
    return name

def suggest_replacements(used: Set[str], allowed: Set[str]) -> Dict[str, str]:
    """Sugiere reemplazos para tablas incorrectas"""
    repl: Dict[str, str] = {}
    allowed_by_schema: Dict[str, Dict[str, str]] = {}
    
    # Organizar tablas permitidas por esquema
    for a in allowed:
        if '.' not in a:
            continue
        sch, tbl = a.split(".", 1)
        allowed_by_schema.setdefault(sch, {})[tbl] = a

    for u in used:
        if u in allowed:
            continue
        
        # Verificar alias directo
        if u in ALIASES:
            repl[u] = ALIASES[u]
            continue
        
        if '.' not in u:
            continue
        
        us, ut = u.split(".", 1)
        
        # Intentar singularizar
        cand_tbl = singularize(ut)
        if us in allowed_by_schema and cand_tbl in allowed_by_schema[us]:
            repl[u] = allowed_by_schema[us][cand_tbl]
            continue
        
        # Buscar coincidencias aproximadas en el mismo esquema
        if us in allowed_by_schema:
            allowed_tables = list(allowed_by_schema[us].keys())
            match = difflib.get_close_matches(ut, allowed_tables, n=1, cutoff=0.6)
            if match:
                repl[u] = allowed_by_schema[us][match[0]]
                continue
        
        # Buscar en todos los esquemas
        all_allowed_tables = [a.split(".", 1)[1] for a in allowed if '.' in a]
        match = difflib.get_close_matches(ut, all_allowed_tables, n=1, cutoff=0.6)
        if match:
            for a in allowed:
                if '.' in a:
                    sch, tbl = a.split(".", 1)
                    if tbl == match[0]:
                        repl[u] = a
                        break
    
    return repl

def apply_table_replacements(sql: str, replacements: Dict[str, str]) -> str:
    """Aplica reemplazos de tablas en el SQL"""
    if not sql or not replacements:
        return sql
    
    for wrong, right in replacements.items():
        if '.' not in wrong or '.' not in right:
            continue
        
        ws, wt = wrong.split(".", 1)
        rs, rt = right.split(".", 1)
        
        # Patrón case-insensitive
        pattern = rf'(?i)\b{re.escape(ws)}\s*\.\s*{re.escape(wt)}\b'
        sql = re.sub(pattern, f'{rs}.{rt}', sql)
    
    return sql

def apply_hard_aliases_first(sql: str, allowed: Set[str]) -> str:
    """Aplica aliases conocidos antes de validar"""
    if not sql:
        return sql
    
    used0 = tables_in_sql(sql)
    repl: Dict[str, str] = {}
    
    for u in used0:
        if u not in allowed and u in ALIASES:
            repl[u] = ALIASES[u]
    
    if repl:
        logger.info(f"🔄 Aplicando aliases: {repl}")
        sql = apply_table_replacements(sql, repl)
        sql = normalize_schema_dots(sql)
    
    return sql

def force_count_star_for_how_many(sql: str, question: str, used_tables: Set[str]) -> str:
    """Fuerza COUNT(*) para preguntas de cantidad"""
    if not question or not used_tables:
        return sql
    
    q = question.lower()
    count_keywords = ["cuántos", "cuantos", "cantidad", "número", "numero", "total de"]
    
    if any(k in q for k in count_keywords):
        if len(used_tables) == 1 and "count(" not in (sql or "").lower():
            t = list(used_tables)[0]
            logger.info(f"🔢 Forzando COUNT(*) para tabla {t}")
            return f"SELECT COUNT(*) AS total FROM {t}"
    
    return sql

# ====== ATAJOS "listar/mostrar" ======
def detect_list_intent(question: str) -> bool:
    """Detecta intención de listar datos"""
    if not question:
        return False
    
    q = question.lower()
    keywords = [
        "muestra", "lista", "enséñame", "ensename", "primeros", "top",
        "ver los primeros", "muéstrame", "muestrame", "dame", "ver",
        "últimos", "ultimos"
    ]
    
    return any(w in q for w in keywords)

KEYWORD_TABLE: Dict[str, str] = {
    "compr": "public.commerce_buyer",
    "buyer": "public.commerce_buyer",
    "factur": "public.commerce_invoice",
    "list": "public.commerce_listing",
    "bid": "public.commerce_bid",
    "ofert": "public.commerce_bid",
    "trabaj": "public.commerce_worker",
    "deuda": "public.commerce_workerdebt",
    "pago": "public.commerce_workerpayment",
    "cultiv": "public.farm_crop",
    "producc": "public.farm_production",
    "finca": "public.farm_farm",
    "herram": "public.farm_tool",
    "ingreso": "public.farm_income",
    "costo": "public.farm_cost",
    "usuario": "public.users_user",
    "precio": "public.commerce_marketprice",
}

def pick_table_by_question(question: str, allowed: Set[str]) -> Optional[str]:
    """Selecciona tabla basándose en palabras clave"""
    if not question:
        return None
    
    q = question.lower()
    
    # Buscar coincidencia exacta en keywords
    for key, table in KEYWORD_TABLE.items():
        if key in q and table in allowed:
            logger.info(f"🎯 Tabla detectada por keyword '{key}': {table}")
            return table
    
    # Fallback a tablas principales
    priority_tables = [
        "public.commerce_invoice",
        "public.commerce_buyer",
        "public.farm_production",
        "public.farm_crop",
        "public.users_user"
    ]
    
    for table in priority_tables:
        if table in allowed:
            logger.info(f"📌 Usando tabla prioritaria: {table}")
            return table
    
    return None

def yaml_columns_for_table(path: str, full_table: str) -> List[str]:
    """Obtiene columnas de una tabla desde el YAML"""
    if '.' not in full_table:
        return []
    
    sch, tbl = full_table.split(".", 1)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"❌ Error leyendo columnas: {e}")
        return []
    
    for db in data.get("databases", []):
        for s in db.get("schemas", []):
            if (s.get("name") or "").lower() == sch.lower():
                for t in s.get("tables", []):
                    if (t.get("name") or "").lower() == tbl.lower():
                        cols = [(c.get("name") or "").strip() for c in t.get("columns", [])]
                        return [c for c in cols if c]
    
    return []

def default_list_sql(full_table: str, cols: List[str], limit: int = 10) -> str:
    """Genera SQL por defecto para listar registros"""
    # Validar límite
    limit = min(limit, MAX_ROWS_LIMIT)
    
    # Columnas preferenciales para mostrar
    preferred_order = ["id", "name", "nombre", "created_at", "fecha", "email", "full_name", "date"]
    
    # Ordenar columnas por preferencia
    ordered = []
    for p in preferred_order:
        ordered.extend([c for c in cols if c.lower() == p.lower()])
    
    # Agregar columnas restantes
    ordered.extend([c for c in cols if c.lower() not in [p.lower() for p in preferred_order]])
    
    # Seleccionar primeras 5 columnas o todas si son menos
    if ordered:
        sel_cols = ", ".join(ordered[:5])
    else:
        sel_cols = "*"
    
    # Determinar columna de ordenamiento
    order_col = None
    for cand in ["created_at", "fecha", "date", "id"]:
        if any(c.lower() == cand.lower() for c in cols):
            order_col = cand
            break
    
    order_clause = f" ORDER BY {order_col} DESC" if order_col else ""
    
    sql = f"SELECT {sel_cols} FROM {full_table}{order_clause} LIMIT {limit}"
    logger.info(f"📝 SQL generado (atajo): {sql}")
    
    return sql

# ====== GENERACIÓN SQL CON REINTENTOS ======
def generate_sql_with_retries(
    question: str,
    schema_text: str,
    allowed: Set[str],
    lang: str = "es",
    max_retries: int = MAX_RETRIES
) -> Tuple[str, Set[str], str]:
    """Genera SQL con reintentos automáticos y correcciones"""
    
    feedback: Optional[str] = None
    last_sql: str = ""
    last_used: Set[str] = set()

    for attempt in range(max_retries):
        logger.info(f"🔄 Intento {attempt + 1}/{max_retries} para generar SQL")
        
        try:
            payload = {
                "question": question,
                "schema_text": schema_text,
                "lang": lang,
                "max_new_tokens": 256
            }
            
            if feedback:
                payload["feedback"] = feedback
                logger.info(f"📝 Feedback enviado: {feedback[:100]}...")
            
            # Hacer petición con timeout configurable
            r = requests.post(
                SQLCODER_URL,
                json=payload,
                timeout=SQLCODER_TIMEOUT
            )
            r.raise_for_status()
            
            result = r.json()
            sql = result.get("sql", "")
            
            if not sql:
                raise RuntimeError("Respuesta de SQLCoder sin campo 'sql'")
            
            logger.info(f"✅ SQL recibido: {sql[:100]}...")
            
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout en intento {attempt + 1} (>{SQLCODER_TIMEOUT}s)")
            if attempt == max_retries - 1:
                return "", set(), (
                    f"SQLCoder tardó más de {SQLCODER_TIMEOUT}s en responder. "
                    "Aumenta SQLCODER_TIMEOUT o usa GPU."
                )
            continue
        
        except Exception as e:
            logger.error(f"❌ Error en intento {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return "", set(), f"Error llamando a SQLCoder: {str(e)}"
            continue

        # Normalizar y corregir SQL
        sql = normalize_schema_dots(sql)
        sql = apply_hard_aliases_first(sql, allowed)
        used = tables_in_sql(sql)
        sql = force_count_star_for_how_many(sql, question, used)
        used = tables_in_sql(sql)  # Re-extraer después de correcciones

        last_sql, last_used = sql, used

        # Validar tablas
        if not allowed or used.issubset(allowed):
            logger.info(f"✅ SQL válido generado en intento {attempt + 1}")
            logger.info(f"📊 Tablas usadas: {sorted(used)}")
            return sql, used, ""

        # Tablas incorrectas detectadas
        missing = used - allowed
        logger.warning(f"⚠️ Tablas incorrectas: {missing}")
        
        repl = suggest_replacements(used, allowed)

        if repl:
            logger.info(f"🔄 Correcciones sugeridas: {repl}")
            sql2 = apply_table_replacements(sql, repl)
            sql2 = normalize_schema_dots(sql2)
            used2 = tables_in_sql(sql2)
            
            if used2.issubset(allowed):
                logger.info(f"✅ SQL corregido automáticamente en intento {attempt + 1}")
                return sql2, used2, ""
            
            # Feedback detallado
            mapping_txt = "; ".join([f"'{k}' → '{v}'" for k, v in repl.items()])
            feedback = (
                f"ERROR: Las tablas {', '.join(sorted(missing))} NO EXISTEN. "
                f"Debes usar EXACTAMENTE: {mapping_txt}. "
                f"Genera de nuevo el SQL usando SOLO estas tablas válidas."
            )
        else:
            feedback = (
                f"ERROR CRÍTICO: Las tablas {', '.join(sorted(missing))} NO EXISTEN. "
                f"Tablas ÚNICAS disponibles: {', '.join(sorted(list(allowed)[:10]))}... "
                f"NO inventes nombres. Usa SOLO las tablas listadas."
            )

    # Agotados todos los intentos
    error_msg = (
        f"Después de {max_retries} intentos, no se pudo generar SQL válido. "
        f"Tablas usadas: {sorted(last_used)}. Tablas permitidas: {sorted(list(allowed)[:5])}..."
    )
    logger.error(f"❌ {error_msg}")
    
    return last_sql, last_used, error_msg

# ====== FEEDBACK AL MODELO ======
def send_feedback_to_sqlcoder(
    question: str,
    sql: str,
    success: bool,
    tables_used: Optional[Set[str]] = None
):
    """Envía feedback al modelo SQLCoder"""
    try:
        feedback_url = SQLCODER_URL.replace("/generate_sql", "/feedback")
        
        requests.post(
            feedback_url,
            json={
                "question": question,
                "sql": sql,
                "success": success,
                "tables_used": sorted(list(tables_used)) if tables_used else []
            },
            timeout=10
        )
        
        logger.info(f"✅ Feedback enviado: success={success}")
    
    except Exception as e:
        logger.warning(f"⚠️ No se pudo enviar feedback: {e}")

# ====== VALIDACIÓN DE CONEXIÓN ======
def test_db_connection() -> Tuple[bool, str]:
    """Prueba la conexión a PostgreSQL"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
        
        logger.info("✅ Conexión a PostgreSQL exitosa")
        return True, version
    
    except Exception as e:
        logger.error(f"❌ Error de conexión a PostgreSQL: {e}")
        return False, str(e)

# ====== SCHEMAS PYDANTIC ======
class AskIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    lang: str = Field(default="es", pattern="^(es|en)$")

class RefineIn(BaseModel):
    question: str
    sql: str = ""
    columns: List[str] = []
    rows: List[Dict] = []
    lang: str = "es"
    tone: str = "amigable"
    suggest_followups: bool = True
    max_new_tokens: int = Field(default=192, ge=50, le=512)

# ====== STARTUP EVENT ======
@app.on_event("startup")
async def startup_event():
    """Validación al iniciar la aplicación"""
    try:
        validate_config()
        logger.info("🚀 Aplicación iniciada correctamente")
    except Exception as e:
        logger.error(f"❌ Error en startup: {e}")
        raise

# ====== ENDPOINTS ======
@app.get("/health")
def health():
    """Health check con validación de conexiones"""
    db_ok, db_info = test_db_connection()
    
    return {
        "status": "ok" if db_ok else "degraded",
        "version": "2.2",
        "sqlcoder_url": SQLCODER_URL,
        "sqlcoder_timeout": SQLCODER_TIMEOUT,
        "nlg_url": NLG_URL,
        "schema_path": SCHEMA_PATH,
        "pg_host": PG_HOST,
        "pg_connection": "ok" if db_ok else "error",
        "pg_info": db_info if db_ok else f"Error: {db_info}",
        "max_retries": MAX_RETRIES,
        "max_rows_limit": MAX_ROWS_LIMIT,
    }

@app.post("/refine")
def refine_via_nlg(data: RefineIn):
    """Proxy directo a NLG - úsalo solo si ya tienes el SQL ejecutado"""
    try:
        r = requests.post(NLG_URL, json=data.model_dump(), timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout al contactar NLG")
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error al llamar NLG: {str(e)}"
        )

@app.get("/nlg/health")
def nlg_health():
    """Health check del servicio NLG"""
    try:
        base = NLG_URL.rsplit("/", 1)[0]
        r = requests.get(f"{base}/health", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"NLG no disponible: {str(e)}"
        )

@app.get("/nlg/identity")
def nlg_identity():
    """Identidad del servicio NLG"""
    try:
        base = NLG_URL.rsplit("/", 1)[0]
        r = requests.get(f"{base}/identity", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo consultar identity del NLG: {str(e)}"
        )

@app.post("/ask")
def ask(data: AskIn):
    """
    Endpoint principal - convierte preguntas en SQL y las ejecuta
    
    Flujo:
    1. Detecta atajos (listar tablas comunes)
    2. Genera SQL con SQLCoder (con reintentos)
    3. Valida y ejecuta en PostgreSQL
    4. Genera respuesta en lenguaje natural con NLG
    """
    
    # 0) Verificar conexión a BD
    db_ok, db_error = test_db_connection()
    if not db_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "error": f"Base de datos no disponible: {db_error}",
                "suggestion": "Verifica las variables de entorno: PG_HOST, PG_DB, PG_USER, PG_PASS"
            }
        )
    
    # 1) Cargar esquema y tablas permitidas
    try:
        schema_text = load_schema_text(SCHEMA_PATH)
        allowed = allowed_tables_from_yaml(SCHEMA_PATH)
        logger.info(f"📚 Esquema cargado: {len(allowed)} tablas disponibles")
    except Exception as e:
        logger.error(f"❌ Error cargando esquema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cargando esquema: {str(e)}"
        )

    # ===== ATAJO: intención de listar =====
    if detect_list_intent(data.question):
        table = pick_table_by_question(data.question, allowed)
        
        if table:
            logger.info(f"🎯 Atajo detectado para tabla: {table}")
            cols = yaml_columns_for_table(SCHEMA_PATH, table)
            
            # Extraer límite si está en la pregunta
            limit = 10
            limit_match = re.search(r'\b(\d+)\b', data.question)
            if limit_match:
                limit = min(int(limit_match.group(1)), MAX_ROWS_LIMIT)
            
            sql = default_list_sql(table, cols, limit=limit)
            
            # Ejecutar query
            try:
                with get_db_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(sql)
                        rows = cur.fetchall() if cur.description else []
                        cols_out = [c.name for c in cur.description] if cur.description else []
                
                logger.info(f"✅ Query ejecutado (atajo): {len(rows)} filas")
            
            except Exception as e:
                logger.error(f"❌ Error ejecutando SQL (atajo): {e}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": f"Error ejecutando SQL: {str(e)}",
                        "sql": sql
                    }
                )
            
            # Enviar feedback positivo
            send_feedback_to_sqlcoder(data.question, sql, True, {table})
            
            # Generar respuesta NLG
            try:
                r2 = requests.post(NLG_URL, json={
                    "question": data.question,
                    "sql": sql,
                    "columns": cols_out,
                    "rows": rows,
                    "lang": data.lang,
                    "tone": "amigable",
                    "suggest_followups": True,
                    "max_new_tokens": 192
                }, timeout=120)
                r2.raise_for_status()
                answer = r2.json().get("answer", f"Encontré {len(rows)} registros en {table}")
            
            except Exception as ex:
                logger.warning(f"⚠️ NLG falló (atajo): {ex}")
                answer = f"Encontré {len(rows)} registros en {table}"

            return {
                "sql": sql,
                "rows": rows,
                "answer": answer,
                "shortcut": "list_intent",
                "tables_used": [table],
                "execution_success": True
            }

    # ===== GENERACIÓN SQL NORMAL =====
    logger.info(f"🤖 Generando SQL para: {data.question}")
    
    sql, used, error = generate_sql_with_retries(
        question=data.question,
        schema_text=schema_text,
        allowed=allowed,
        lang=data.lang,
        max_retries=MAX_RETRIES
    )
    
    # Si hubo error en generación
    if error:
        logger.error(f"❌ Error generando SQL: {error}")
        return {
            "error": error,
            "sql": sql,
            "used_tables": sorted(list(used)),
            "allowed_tables": sorted(list(allowed))[:20],  # Solo primeras 20
            "suggestion": "Intenta reformular la pregunta o especifica mejor qué información necesitas",
            "execution_success": False
        }

    logger.info(f"📝 SQL generado: {sql}")
    logger.info(f"🔍 Tablas usadas: {sorted(used)}")

    # ===== EJECUTAR SQL =====
    try:
        with get_db_connection() as conn:
            # Verificar que las tablas existan
            missing = verify_tables_exist(conn, used)
            
            if missing:
                logger.error(f"❌ Tablas no encontradas en BD: {missing}")
                send_feedback_to_sqlcoder(data.question, sql, False, used)
                
                return {
                    "error": f"Las siguientes tablas no existen en la base de datos: {', '.join(missing)}",
                    "sql": sql,
                    "used_tables": sorted(list(used)),
                    "missing_tables": missing,
                    "suggestion": "El catálogo YAML puede estar desactualizado o las tablas fueron eliminadas",
                    "execution_success": False
                }

            # Ejecutar query
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall() if cur.description else []
                cols = [c.name for c in cur.description] if cur.description else []

        logger.info(f"✅ Ejecución exitosa: {len(rows)} filas retornadas")
        send_feedback_to_sqlcoder(data.question, sql, True, used)

    except psycopg2.errors.SyntaxError as e:
        logger.error(f"❌ Error de sintaxis SQL: {e}")
        send_feedback_to_sqlcoder(data.question, sql, False, used)
        
        return {
            "error": f"Error de sintaxis en el SQL generado: {str(e)}",
            "sql": sql,
            "suggestion": "El SQL generado tiene errores de sintaxis. Intenta reformular la pregunta.",
            "execution_success": False
        }
    
    except psycopg2.errors.UndefinedColumn as e:
        logger.error(f"❌ Columna no definida: {e}")
        send_feedback_to_sqlcoder(data.question, sql, False, used)
        
        return {
            "error": f"Una o más columnas no existen en la tabla: {str(e)}",
            "sql": sql,
            "suggestion": "El esquema YAML puede estar desactualizado. Verifica las columnas disponibles.",
            "execution_success": False
        }
    
    except Exception as e:
        logger.error(f"❌ Error ejecutando SQL: {e}")
        send_feedback_to_sqlcoder(data.question, sql, False, used)
        
        return {
            "error": f"Error ejecutando SQL en PostgreSQL: {str(e)}",
            "sql": sql,
            "suggestion": "Verifica que el SQL sea válido y las tablas/columnas existan",
            "execution_success": False
        }

    # ===== GENERAR RESPUESTA NLG =====
    try:
        logger.info("💬 Generando respuesta en lenguaje natural...")
        
        r2 = requests.post(NLG_URL, json={
            "question": data.question,
            "sql": sql,
            "columns": cols,
            "rows": rows,
            "lang": data.lang,
            "tone": "amigable",
            "suggest_followups": True,
            "max_new_tokens": 192
        }, timeout=120)
        
        r2.raise_for_status()
        answer = r2.json().get("answer")
        logger.info("✅ Respuesta generada por NLG")
    
    except requests.exceptions.Timeout:
        logger.warning("⚠️ Timeout en NLG, usando respuesta por defecto")
        if rows:
            answer = f"Encontré {len(rows)} resultado(s). Columnas disponibles: {', '.join(cols)}"
        else:
            answer = "No encontré resultados para tu consulta."
    
    except Exception as ex:
        logger.warning(f"⚠️ NLG falló: {ex}, usando respuesta por defecto")
        if rows:
            answer = f"Encontré {len(rows)} resultado(s). Columnas: {', '.join(cols)}"
        else:
            answer = "No encontré resultados para tu consulta."

    # ===== RESPUESTA EXITOSA =====
    return {
        "sql": sql,
        "rows": rows,
        "answer": answer,
        "tables_used": sorted(list(used)),
        "row_count": len(rows),
        "columns": cols,
        "execution_success": True
    }


# ====== ENDPOINT DE DEBUG ======
@app.get("/debug/tables")
def debug_tables():
    """Lista todas las tablas disponibles en el esquema"""
    try:
        allowed = allowed_tables_from_yaml(SCHEMA_PATH)
        return {
            "total_tables": len(allowed),
            "tables": sorted(list(allowed))
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error leyendo tablas: {str(e)}"
        )


@app.get("/debug/aliases")
def debug_aliases():
    """Muestra todos los aliases configurados"""
    return {
        "total_aliases": len(ALIASES),
        "aliases": ALIASES
    }


@app.post("/debug/validate_sql")
def debug_validate_sql(sql: str, question: str = ""):
    """Valida SQL sin ejecutarlo"""
    try:
        allowed = allowed_tables_from_yaml(SCHEMA_PATH)
        
        # Normalizar
        sql_normalized = normalize_schema_dots(sql)
        sql_with_aliases = apply_hard_aliases_first(sql_normalized, allowed)
        
        # Extraer tablas
        used = tables_in_sql(sql_with_aliases)
        
        # Validar
        missing = used - allowed
        suggestions = suggest_replacements(used, allowed) if missing else {}
        
        # Verificar en BD
        with get_db_connection() as conn:
            db_missing = verify_tables_exist(conn, used)
        
        return {
            "original_sql": sql,
            "normalized_sql": sql_normalized,
            "sql_with_aliases": sql_with_aliases,
            "tables_used": sorted(list(used)),
            "tables_valid": len(missing) == 0,
            "missing_in_schema": sorted(list(missing)),
            "missing_in_db": db_missing,
            "suggestions": suggestions,
            "is_valid": len(missing) == 0 and len(db_missing) == 0
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validando SQL: {str(e)}"
        )


@app.get("/debug/config")
def debug_config():
    """Muestra la configuración actual (sin credenciales)"""
    return {
        "sqlcoder_url": SQLCODER_URL,
        "sqlcoder_timeout": SQLCODER_TIMEOUT,
        "nlg_url": NLG_URL,
        "schema_path": SCHEMA_PATH,
        "schema_exists": os.path.exists(SCHEMA_PATH),
        "pg_host": PG_HOST,
        "pg_port": PG_PORT,
        "pg_db": PG_DB,
        "pg_user": PG_USER,
        "pg_ssl": PG_SSL,
        "max_retries": MAX_RETRIES,
        "max_rows_limit": MAX_ROWS_LIMIT,
    }


# ====== MAIN ======
if __name__ == "__main__":
    import uvicorn
    
    try:
        validate_config()
        logger.info("🚀 Iniciando servidor FastAPI...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"❌ Error al iniciar: {e}")
        exit(1)
