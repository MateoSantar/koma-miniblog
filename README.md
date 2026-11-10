# FastAPI Mini Blog

API REST para gestionar publicaciones de un blog. Es un proyecto de aprendizaje y portfolio que evoluciona junto con los módulos de desarrollo backend.

## Funcionalidades implementadas actualmente

- Crear, listar, consultar, actualizar y eliminar publicaciones.
- Buscar publicaciones por título.
- Paginar resultados y ordenar por identificador o título.
- Filtrar publicaciones por una o más etiquetas.
- Asociar opcionalmente un autor y etiquetas a una publicación.
- Validar datos de entrada mediante Pydantic.
- Manejar respuestas HTTP para recursos no encontrados y errores de persistencia.
- Documentación interactiva generada por FastAPI.

## Tecnologías

- Python
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- SQLite para desarrollo local
- python-dotenv para configuración mediante variables de entorno

## Estructura principal

```text
app/
├── main.py
├── core/
│   └── db.py
├── models/
│   ├── author.py
│   ├── post.py
│   └── tag.py
└── api/
    └── v1/
        └── posts/
            ├── router.py
            ├── repository.py
            └── schemas.py
```

## Requisitos

Python 3.10 o superior. Las dependencias están declaradas en `requirements.txt`.

## Instalación en Windows (PowerShell)

Desde la raíz del repositorio:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si necesitás usar variables de entorno, copiá `.env.example` como `.env` y ajustá los valores para tu entorno. No subas el archivo `.env` a GitHub.

## Ejecutar la API

```powershell
fastapi dev app/main.py
```

Abrí la documentación interactiva en `http://127.0.0.1:8000/docs`.

## Endpoints actuales

| Método | Ruta | Propósito |
|---|---|---|
| `GET` | `/posts` | Listar publicaciones, con búsqueda, paginación y orden |
| `GET` | `/posts/by-tags` | Filtrar publicaciones por etiquetas |
| `GET` | `/posts/{post_id}` | Consultar una publicación; permite omitir el contenido |
| `POST` | `/posts` | Crear una publicación |
| `PUT` | `/posts/{post_id}` | Actualizar una publicación |
| `DELETE` | `/posts/{post_id}` | Eliminar una publicación |

## Estado del proyecto

Esta es la versión inicial publicada del proyecto. La autenticación JWT, la gestión independiente de usuarios/categorías/etiquetas, los slugs, las migraciones con Alembic, PostgreSQL y el despliegue son trabajo futuro y no se presentan aquí como funcionalidades ya implementadas.

Actualmente, la aplicación crea las tablas al iniciar, una solución de desarrollo que se revisará al incorporar migraciones.

## Objetivo educativo

El repositorio acompaña el aprendizaje de desarrollo de APIs REST y se ampliará con commits pequeños y coherentes a medida que se implementen nuevas funcionalidades. Cada commit documentará un cambio real en el código.

## Autor

César Gimenez Lascano — [@cgldev](https://github.com/cgldev)

## Interfaz web: Koma

La API sirve en `/` una interfaz de blog de anime y manga (`app/static/index.html`): lista con búsqueda, orden, paginación y filtro por etiqueta, lector de posts, login y alta, edición y baja de posts.

Mientras el servidor está prendido, `app/services/noticias.py` trae las últimas noticias del [RSS de MyAnimeList](https://myanimelist.net/rss/news.xml) al arrancar y cada 30 minutos, y las publica firmadas por MyAnimeList, con su imagen y el link a la nota original. Una noticia que ya está no se vuelve a cargar.

Para traerlas a mano: `python scripts/importar_noticias.py`.

### Variables de entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./blog.db` | Base de datos |
| `MEDIA_DIR` | `app/media` | Carpeta de las imágenes subidas |
| `SECRET_KEY` | `change-me-in-prod` | Firma de los JWT. En producción tiene que ser otra |
| `ALUMNO_PASSWORD` | `123456` | Clave de `alumno@example.com` |
| `CESAR_PASSWORD` | `secret123` | Clave de `cesar@example.com` |
| `NOTICIAS_AUTO` | `1` | `0` apaga la importación automática |
| `NOTICIAS_INTERVALO_MIN` | `30` | Minutos entre importaciones |

## Despliegue en Render

El repositorio trae un `render.yaml` para el plan gratis.

1. Subí el repositorio a tu cuenta de GitHub.
2. En Render: **New > Blueprint**, elegí el repositorio y confirmá. Render pide la clave para `ALUMNO_PASSWORD`; `SECRET_KEY` y `CESAR_PASSWORD` las genera solo.
3. Cuando termina el deploy, el blog queda en `https://koma-miniblog.onrender.com` (o el nombre que Render asigne).

Lo que hay que saber del plan gratis:

- El disco no se conserva. Cada deploy, reinicio o apagado borra la base SQLite y las imágenes. Las noticias vuelven solas al arrancar; los posts escritos a mano se pierden.
- El servicio se apaga después de 15 minutos sin visitas y tarda cerca de un minuto en volver.
- Para conservar los posts hace falta un plan pago con disco persistente (montado, por ejemplo, en `/var/data`, con `DATABASE_URL=sqlite:////var/data/blog.db` y `MEDIA_DIR=/var/data/media`) o una base Postgres (`psycopg2-binary` ya está en las dependencias).
