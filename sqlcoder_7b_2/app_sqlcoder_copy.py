# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from threading import Lock
import os, re, torch, json, time

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)

# ---------- Config ----------
MODEL_NAME = os.getenv("SQLCODER_MODEL", "defog/sqlcoder-7b-2")
TITLE = "SQLCoder 7B-2 (PostgreSQL) - Enhanced"
PORT = int(os.getenv("PORT", "8001"))
MEMORY_FILE = os.getenv("MEMORY_FILE", "/workspace/sqlcoder_7b_2/memory.json")

# Sugerencias para reducir RAM/CPU (ajústalas según tu máquina)
os.environ.setdefault("HF_HOME", "/workspace/.cache/hf")
os.environ.setdefault("TRANSFORMERS_CACHE", "/workspace/.cache/hf/transformers")
os.makedirs(os.environ["TRANSFORMERS_CACHE"], exist_ok=True)

# Limitar hilos BLAS para no saturar CPU (ajústalo si tienes muchos núcleos)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
try:
    torch.set_num_threads(int(os.getenv("TORCH_NUM_THREADS", "1")))
except Exception:
    pass

# ---------- FastAPI ----------
app = FastAPI(title=TITLE, version="2.0")

class SQLIn(BaseModel):
    question: str
    schema_text: str
    lang: str = "es"
    max_new_tokens: int = 256
    feedback: Optional[str] = None

# ---------- Sistema de Memoria ----------
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
            if len(self.memory["successful_queries"]) > 50:
                self.memory["successful_queries"] = self.memory["successful_queries"][-50:]
            self._save()

    def add_failure(self, pattern: str):
        if pattern not in self.memory["failed_patterns"]:
            self.memory["failed_patterns"].append(pattern)
            if len(self.memory["failed_patterns"]) > 20:
                self.memory["failed_patterns"] = self.memory["failed_patterns"][-20:]
            self._save()

    def get_similar_examples(self, question: str, limit: int = 3) -> List[dict]:
        q_lower = question.lower()
        q_words = set(re.findall(r'\w+', q_lower))
        scored = []
        for entry in self.memory["successful_queries"]:
            entry_words = set(re.findall(r'\w+', entry["question"]))
            overlap = len(q_words & entry_words)
            if overlap > 0:
                scored.append((overlap, entry))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [entry for _, entry in scored[:limit]]

memory = SQLMemory(MEMORY_FILE)

# ---------- Utilidades ----------
def list_tables(schema_text: str):
    tabs = []
    for line in schema_text.splitlines():
        m = re.match(r"\s*TABLE\s+([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)", line)
        if m:
            tabs.append(f"{m.group(1)}.{m.group(2)}")
    return tabs

def extract_table_details(schema_text: str) -> Dict[str, dict]:
    tables: Dict[str, dict] = {}
    current_table = None
    for line in schema_text.splitlines():
        table_match = re.match(r"\s*TABLE\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s*(?:--\s*(.+))?", line)
        if table_match:
            current_table = table_match.group(1)
            description = table_match.group(2) or ""
            tables[current_table] = {"description": description.strip(), "columns": []}
        elif current_table and line.strip().startswith("- "):
            col_match = re.match(r"\s*-\s*(\w+)\s*\(([^)]+)\)", line)
            if col_match:
                tables[current_table]["columns"].append({
                    "name": col_match.group(1),
                    "type": col_match.group(2)
                })
    return tables

def build_prompt(q: str, schema: str, lang: str, feedback: str = None):
    allowed = list_tables(schema)
    allowed_str = ", ".join(allowed) if allowed else "(sin tablas detectadas)"

    examples = memory.get_similar_examples(q, limit=3)
    examples_text = ""
    if examples:
        examples_text = "\n### EJEMPLOS DE CONSULTAS EXITOSAS\n"
        for ex in examples:
            examples_text += f"Pregunta: {ex['question']}\nSQL: {ex['sql']}\n\n"

    sys = f"""Eres un generador EXPERTO de SQL para PostgreSQL.

REGLAS CRÍTICAS:
1. Genera EXACTAMENTE UNA sentencia SELECT válida
2. USA SOLO estas tablas: {allowed_str}
3. NO inventes tablas, columnas ni funciones que no existan en el esquema
4. Para conteos usa COUNT(*) o COUNT(columna)
5. Usa JOIN cuando necesites relacionar tablas
6. Para fechas usa formato ISO: YYYY-MM-DD
7. NO uses DDL (CREATE, DROP) ni DML (INSERT, UPDATE, DELETE)
8. Si la pregunta es ambigua, genera la consulta MÁS SIMPLE que responda
"""
    if feedback:
        sys += f"\nCORRECCIÓN NECESARIA: {feedback}\n"

    q_lower = q.lower()
    hints = []
    if any(k in q_lower for k in ["cuántos", "cuantos", "cantidad"]):
        hints.append("Usa COUNT(*) para contar registros")
    if any(k in q_lower for k in ["último", "ultimos", "reciente"]):
        hints.append("Usa ORDER BY fecha_columna DESC LIMIT N")
    if any(k in q_lower for k in ["promedio", "media"]):
        hints.append("Usa AVG(columna)")
    if any(k in q_lower for k in ["total", "suma"]):
        hints.append("Usa SUM(columna)")
    if hints:
        sys += "\nHINTS para esta pregunta:\n" + "\n".join(f"- {h}" for h in hints) + "\n"

    prompt = f"""{sys}
{examples_text}
### ESQUEMA COMPLETO
{schema}

### PREGUNTA ({lang})
{q}

### SQL (responde SOLO con el código SQL, sin explicaciones):
SELECT"""
    return prompt

def postprocess_sql(text: str) -> str:
    text = text.strip()
    m = re.search(r"```sql\s*(.+?)```", text, flags=re.S|re.I) or re.search(r"```\s*(.+?)```", text, flags=re.S)
    if m:
        text = m.group(1).strip()
    if not text.upper().startswith("SELECT"):
        text = "SELECT " + text
    candidates = re.split(r";\s*", text)
    for c in candidates:
        c = c.strip()
        if c.upper().startswith("SELECT"):
            c = re.sub(r'--[^\n]*', '', c)
            return c.strip()
    return candidates[0].strip() if candidates else text

def device_name():
    return "cuda" if torch.cuda.is_available() else "cpu"

# ---------- Carga perezosa ----------
_tokenizer = None
_model = None
_loading = False
_lock = Lock()
_last_error: Optional[str] = None
_loaded_at: Optional[float] = None

def _load_model_sync():
    global _tokenizer, _model, _last_error, _loaded_at
    _last_error = None
    start = time.time()
    print(f"🔧 Cargando {MODEL_NAME} en {device_name()}...")

    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)

    if torch.cuda.is_available():
        try:
            bnb_cfg = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            _model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                device_map="auto",
                quantization_config=bnb_cfg,
                torch_dtype=torch.bfloat16,
            )
            print("✅ Modelo cargado en 4-bit")
        except Exception as e:
            _last_error = str(e)
            print(f"⚠️ 4-bit falló: {e} → intentando 8-bit…")
            _model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                device_map="auto",
                load_in_8bit=True,
            )
            print("✅ Modelo cargado en 8-bit")
    else:
        # CPU
        # Nota: mantener float32 en CPU evita problemas de fp16/bf16
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
            device_map="cpu",
        )
        print("✅ Modelo cargado en CPU")

    _loaded_at = time.time()
    print(f"⏱️  Carga completa en {(_loaded_at - start):.1f}s")

def ensure_model():
    global _loading
    if _model is not None:
        return
    if _loading:
        return
    with _lock:
        if _model is None and not _loading:
            _loading = True
            try:
                _load_model_sync()
            finally:
                _loading = False

# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "device": device_name(),
        "model_loaded": _model is not None,
        "loading": _loading,
        "loaded_at": _loaded_at,
        "memory_examples": len(memory.memory["successful_queries"]),
        "load_warning": _last_error,
    }

@app.post("/warmup")
def warmup():
    """Dispara la carga del modelo sin bloquear el arranque inicial."""
    ensure_model()
    if _loading:
        raise HTTPException(status_code=202, detail="Cargando modelo…")
    return {"status": "ready", "model_loaded": _model is not None}

@app.post("/generate_sql")
def generate_sql(data: SQLIn):
    ensure_model()
    if _model is None or _loading:
        raise HTTPException(status_code=503, detail="Modelo cargando, intenta en unos segundos")

    prompt = build_prompt(data.question, data.schema_text, data.lang, data.feedback)
    enc = _tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096)

    # mover a GPU si existe
    if next(_model.parameters()).is_cuda:
        enc = {k: v.to(_model.device) for k, v in enc.items()}

    with torch.inference_mode():
        out = _model.generate(
            **enc,
            max_new_tokens=data.max_new_tokens,
            do_sample=False,
            temperature=1e-5,
            top_p=1.0,
            num_beams=1,
            no_repeat_ngram_size=3,
            repetition_penalty=1.05,
            eos_token_id=_tokenizer.eos_token_id,
            pad_token_id=_tokenizer.eos_token_id,
        )

    txt = _tokenizer.decode(out[0], skip_special_tokens=True)
    if prompt in txt:
        txt = txt[len(prompt):]
    else:
        tail = prompt.split("SELECT")[-1]
        if txt.startswith(tail):
            txt = txt[len(tail):]

    sql = postprocess_sql(txt)
    return {"sql": sql, "debug_info": {"prompt_length": len(prompt), "raw_output_length": len(txt)}}

@app.post("/feedback")
def record_feedback(question: str, sql: str, success: bool, tables_used: List[str] = None):
    if success and tables_used:
        memory.add_success(question, sql, tables_used)
        return {"status": "success_recorded"}
    elif not success:
        memory.add_failure(sql)
        return {"status": "failure_recorded"}
    return {"status": "no_action"}
