import html
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx

RSS = "https://myanimelist.net/rss/news.xml"
MEDIA_NS = "{http://search.yahoo.com/mrss/}"
BLOG = os.getenv("BLOG_URL", "http://127.0.0.1:8000")
USUARIO = os.getenv("BLOG_USER", "alumno@example.com")
CLAVE = os.getenv("BLOG_PASSWORD", "123456")
MAXIMO = int(os.getenv("MAX_NOTICIAS", "20"))
LIMITE_IMAGEN = 3 * 1024 * 1024
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


def log(*partes):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *partes, flush=True)


def limpiar(texto: str) -> str:
    texto = html.unescape(re.sub(r"<[^>]+>", "", texto or ""))
    return re.sub(r"\s+", " ", texto).strip()


def etiquetas_de(titulo: str) -> list[str]:
    encontradas = [tag for patron, tag in ETIQUETAS if re.search(patron, titulo, re.I)]
    return ["noticias", *encontradas][:4]


def fecha_es(pub: str) -> str:
    try:
        d = parsedate_to_datetime(pub)
        return f"{d.day} de {MESES[d.month - 1]} de {d.year}"
    except (TypeError, ValueError):
        return "fecha desconocida"


def leer_rss(cliente: httpx.Client) -> list[dict]:
    r = cliente.get(RSS, timeout=30)
    r.raise_for_status()
    noticias = []
    for item in ET.fromstring(r.content).iter("item"):
        miniatura = item.find(f"{MEDIA_NS}thumbnail")
        enlace = (item.findtext("link") or "").split("?")[0]
        noticias.append({
            "titulo": limpiar(item.findtext("title")),
            "resumen": limpiar(item.findtext("description")),
            "imagen": miniatura.text.strip() if miniatura is not None and miniatura.text else None,
            "fecha": fecha_es(item.findtext("pubDate")),
            "enlace": enlace,
        })
    return noticias[:MAXIMO]


def titulos_existentes(cliente: httpx.Client) -> set[str]:
    titulos, pagina = set(), 1
    while True:
        r = cliente.get(f"{BLOG}/posts", params={"page": pagina, "per_page": 50}, timeout=15)
        r.raise_for_status()
        datos = r.json()
        titulos.update(p["title"] for p in datos["items"])
        if not datos["has_next"]:
            return titulos
        pagina += 1


def titulo_valido(titulo: str) -> str | None:
    if "spam" in titulo.lower() or len(titulo) < 3:
        return None
    return titulo if len(titulo) <= 100 else titulo[:99].rstrip() + "…"


def bajar_imagen(cliente: httpx.Client, url: str | None):
    if not url:
        return None
    try:
        r = cliente.get(url, timeout=30, follow_redirects=True)
        tipo = r.headers.get("content-type", "").split(";")[0]
        if r.status_code != 200 or tipo not in ("image/jpeg", "image/png") or len(r.content) > LIMITE_IMAGEN:
            return None
        extension = ".png" if tipo == "image/png" else ".jpg"
        return ("imagen" + extension, r.content, tipo)
    except httpx.HTTPError:
        return None


def main() -> int:
    with httpx.Client(headers={"User-Agent": "koma-miniblog/1.0"}) as cliente:
        login = cliente.post(f"{BLOG}/api/v1/auth/login", data={"username": USUARIO, "password": CLAVE}, timeout=15)
        login.raise_for_status()
        auth = {"Authorization": f"Bearer {login.json()['access_token']}"}

        noticias = leer_rss(cliente)
        existentes = titulos_existentes(cliente)
        nuevas = repetidas = fallidas = 0
        for noticia in reversed(noticias):
            titulo = titulo_valido(noticia["titulo"])
            if not titulo:
                continue
            if titulo in existentes:
                repetidas += 1
                continue
            contenido = (
                f"{noticia['resumen']}\n\n"
                f"Publicado en MyAnimeList el {noticia['fecha']}. Nota completa: {noticia['enlace']}"
            )
            datos = {"title": titulo, "content": contenido, "tags": etiquetas_de(titulo)}
            imagen = bajar_imagen(cliente, noticia["imagen"])
            archivos = {"image": imagen} if imagen else None
            r = cliente.post(f"{BLOG}/posts", data=datos, files=archivos, headers=auth, timeout=60)
            if r.status_code == 201:
                nuevas += 1
                log("publicada:", titulo)
            elif r.status_code == 409:
                repetidas += 1
            else:
                fallidas += 1
                log(f"falló ({r.status_code}):", titulo, r.text[:200])
        log(f"listo: {nuevas} nuevas, {repetidas} ya estaban, {fallidas} con error")
        return 1 if fallidas else 0


if __name__ == "__main__":
    if sys.stdout is None:
        carpeta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(carpeta, exist_ok=True)
        sys.stdout = sys.stderr = open(os.path.join(carpeta, "noticias.log"), "a", buffering=1, encoding="utf-8")
    try:
        sys.exit(main())
    except Exception as error:
        log("error:", repr(error))
        sys.exit(1)
