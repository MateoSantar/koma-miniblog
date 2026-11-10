import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv

load_dotenv()

from app.core.db import Base, engine
from app.services.noticias import importar

Base.metadata.create_all(bind=engine)
resultado = importar(int(os.getenv("MAX_NOTICIAS", "20")))
sys.exit(1 if resultado["fallidas"] else 0)
