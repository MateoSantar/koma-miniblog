import asyncio
import html
import os
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.v1.posts.repository import PostRepository
from app.core.db import SessionLocal
from app.models import PostORM
from app.services.file_storage import MAX_MB, CHUNKS, MEDIA_DIR, ensure_media_dir

RSS = "https://myanimelist.net/rss/news.xml"
MEDIA_NS = "{http://search.yahoo.com/mrss/}"
AUTOR = {"username": "MyAnimeList", "email": "noticias@myanimelist.net"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
ETIQUETAS = [
    (r"live[- ]action", "live-action"),
    (r"\bmovies?\b|\bfilm\b", "películas"),
    (r"tv anime|anime adaptation|anime series|season", "anime"),
    (r"\bmanga\b", "manga"),
    (r"\bcast\b|\bstaff\b", "reparto"),
    (r"promo|trailer|teaser|\bpv\b", "trailer"),
    (r"theme|song|opening|ending|music", "música"),
    (r"\bgames?\b", "videojuegos"),
    (r"award|ranking|poll", "rankings"),
]
TIPOS_IMAGEN = {"image/jpeg": ".jpg", "image/png": ".png"}


def log(*partes):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "[noticias]", *partes, flush=True)


def limpiar(texto: str | None) -> str:
    texto = html.unescape(re.sub(r"<[^>]+>", "", texto or ""))
    return re.sub(r"\s+", " ", texto).strip()


def etiquetas_de(titulo: str) -> list[dict]:
    nombres = ["noticias", *[tag for patron, tag in ETIQUETAS if re.search(patron, titulo, re.I)]]
    return [{"name": nombre} for nombre in nombres[:4]]


def fecha_es(pub: str | None) -> str:
    try:
        d = parsedate_to_datetime(pub)
        return f"{d.day} de {MESES[d.month - 1]} de {d.year}"
    except (TypeError, ValueError):
        return "una fecha desconocida"


def titulo_valido(titulo: str) -> str | None:
    if "spam" in titulo.lower() or len(titulo) < 3:
        return None
    return titulo if len(titulo) <= 100 else titulo[:99].rstrip() + "…"


def leer_rss(cliente: httpx.Client, maximo: int) -> list[dict]:
    r = cliente.get(RSS, timeout=30)
    r.raise_for_status()
    noticias = []
    for item in ET.fromstring(r.content).iter("item"):
        miniatura = item.find(f"{MEDIA_NS}thumbnail")
        noticias.append({
            "titulo": limpiar(item.findtext("title")),
            "resumen": limpiar(item.findtext("description")),
            "imagen": miniatura.text.strip() if miniatura is not None and miniatura.text else None,
            "fecha": fecha_es(item.findtext("pubDate")),
            "enlace": (item.findtext("link") or "").split("?")[0],
        })
    return noticias[:maximo]


def guardar_imagen(cliente: httpx.Client, url: str | None) -> str | None:
    if not url:
        return None
    try:
        r = cliente.get(url, timeout=30, follow_redirects=True)
    except httpx.HTTPError:
        return None
    extension = TIPOS_IMAGEN.get(r.headers.get("content-type", "").split(";")[0])
    if r.status_code != 200 or not extension or len(r.content) > MAX_MB * CHUNKS:
        return None
    ensure_media_dir()
    nombre = f"{uuid.uuid4().hex}{extension}"
    with open(os.path.join(MEDIA_DIR, nombre), "wb") as archivo:
        archivo.write(r.content)
    return f"/media/{nombre}"


def importar(maximo: int = 20) -> dict:
    resultado = {"nuevas": 0, "repetidas": 0, "fallidas": 0}
    with httpx.Client(headers={"User-Agent": "koma-miniblog/1.0"}) as cliente, SessionLocal() as db:
        existentes = set(db.scalars(select(PostORM.title)))
        repositorio = PostRepository(db)
        for noticia in reversed(leer_rss(cliente, maximo)):
            titulo = titulo_valido(noticia["titulo"])
            if not titulo:
                continue
            if titulo in existentes:
                resultado["repetidas"] += 1
                continue
            contenido = (
                f"{noticia['resumen']}\n\n"
                f"Publicado en MyAnimeList el {noticia['fecha']}. Nota completa: {noticia['enlace']}"
            )
            try:
                repositorio.create_post(
                    title=titulo,
                    content=contenido,
                    author=AUTOR,
                    tags=etiquetas_de(titulo),
                    image_url=guardar_imagen(cliente, noticia["imagen"]),
                )
                db.commit()
                existentes.add(titulo)
                resultado["nuevas"] += 1
            except IntegrityError:
                db.rollback()
                resultado["fallidas"] += 1
    log(f"{resultado['nuevas']} nuevas, {resultado['repetidas']} ya estaban, {resultado['fallidas']} con error")
    return resultado


async def actualizar_periodicamente() -> None:
    minutos = int(os.getenv("NOTICIAS_INTERVALO_MIN", "30"))
    while True:
        try:
            await asyncio.to_thread(importar)
        except Exception as error:
            log("no se pudieron traer las noticias:", repr(error))
        await asyncio.sleep(minutos * 60)
