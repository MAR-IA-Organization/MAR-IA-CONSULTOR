import runpy, sys
from fastapi import FastAPI

# Ejecuta el archivo real y captura su namespace
ns = runpy.run_path("app_connector.py")

# Intenta encontrar una instancia FastAPI en el namespace
app = None
for k, v in ns.items():
    if isinstance(v, FastAPI):
        app = v
        print(f"[bootstrap] FastAPI encontrado en atributo: {k}", file=sys.stderr)
        break

# Si no se encontró, crea una app mínima para ver el /health
if app is None:
    print("[bootstrap] No se encontró FastAPI en app_connector.py", file=sys.stderr)
    app = FastAPI(title="conector (bootstrap)")

    @app.get("/health")
    def health():
        return {"status": "ok", "note": "No se encontró FastAPI en app_connector.py"}
