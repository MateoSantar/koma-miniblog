"""Levanta el blog sin consola (pensado para pythonw) y deja la salida en logs/servidor.log."""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ))
(RAIZ / "logs").mkdir(exist_ok=True)
salida = open(RAIZ / "logs" / "servidor.log", "a", buffering=1, encoding="utf-8")
sys.stdout = sys.stderr = salida

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")), log_config=None)
