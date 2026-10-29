# Prueba técnica full stack: backoffice + API cliente

Starter repo para evaluar criterio full stack con foco principal en Django.

## Stack

- Django 5.2
- Django templates para backoffice
- Django Ninja para API cliente
- Pydantic v2 para contratos y errores del API
- pytest + factory_boy

## Dominio

El dominio es ficticio y está basado en reservas:

- `Customer`
- `Room`
- `Reservation`

## Flujo de la prueba

El assessment tiene tres partes:

1. Extender el backoffice Django con una transición nueva de reservas.
2. Construir una mini app cliente en `client-app/` para consumir el API.
3. Dockerizar la solución completa.

La consigna completa está en [ASSESSMENT.md](./ASSESSMENT.md).
El contrato base del API está en [API_CONTRACT.md](./API_CONTRACT.md).

Las decisiones técnicas y el uso de IA están en [DECISIONS.md](./DECISIONS.md).

## Correr con Docker

Requisito: Docker con Compose v2. Desde la raíz del repo:

```bash
docker compose up --build
```

Al terminar de arrancar:

| Servicio | URL | Usuario |
|---|---|---|
| App cliente | [http://localhost:8080](http://localhost:8080) | `alice@example.com` / `demo1234` |
| Backoffice | [http://localhost:8000/accounts/login/](http://localhost:8000/accounts/login/) | `manager` / `demo1234` |

No hace falta ningún paso manual: el backend espera a que Postgres esté listo,
corre las migraciones y carga los datos de demo al arrancar, y el cliente espera
a que el backend esté healthy.

### Qué se levanta

- **`db`**: PostgreSQL 17. No expone puertos al host; solo lo ve el backend.
- **`backend`** (`Dockerfile` en la raíz): Django servido por gunicorn, como
  usuario sin privilegios. Las dependencias se instalan con `uv sync --frozen`
  desde `uv.lock`. Los estáticos (incluido el admin) se generan en el build y
  los sirve WhiteNoise.
- **`client`** (`client-app/Dockerfile`): build de Vite servido por nginx sin
  root. nginx también reenvía `/api/` al backend, así que la app y el API
  comparten origen y no hace falta CORS.

### Base de datos

En Docker se usa **PostgreSQL**, con los datos en el volumen nombrado
`db-data`, así que sobreviven a `docker compose down`. El porqué está en
[DECISIONS.md](./DECISIONS.md). Fuera de Docker (sin `POSTGRES_HOST`), Django
sigue usando SQLite como en el starter.

El seed solo corre si la base no tiene reservas
(`seed_demo_data_if_empty`), porque volver a correr `seed_assessment_data`
duplica reservas.

Para empezar de cero:

```bash
docker compose down -v
docker compose up --build
```

### Variables de entorno

Compose lee un archivo `.env` en la raíz si existe. Sin él, usa valores de demo,
**que no sirven para producción**. Para cambiarlos:

```bash
cp .env.example .env
```

| Variable | Default | Uso |
|---|---|---|
| `DJANGO_SECRET_KEY` | valor de demo | Secret de Django. Cambiarlo fuera de la demo. |
| `API_JWT_SECRET` | valor de demo | Firma de los JWT del API cliente. |
| `POSTGRES_DB` | `reservations` | Nombre de la base. |
| `POSTGRES_USER` | `reservations` | Usuario de la base. |
| `POSTGRES_PASSWORD` | valor de demo | Contraseña de la base. Cambiarla fuera de la demo. |
| `DJANGO_DEBUG` | `false` | Modo debug de Django. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts que acepta el backend. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | Orígenes aceptados para los POST del backoffice. |
| `DJANGO_SEED_DEMO_DATA` | `true` | Cargar los datos de demo si la base no tiene reservas. |
| `GUNICORN_WORKERS` | `2` | Cantidad de workers de gunicorn. |
| `BACKEND_PORT` | `8000` | Puerto del host para el backoffice. |
| `CLIENT_PORT` | `8080` | Puerto del host para la app cliente. |

Si cambiás `BACKEND_PORT`, actualizá también `DJANGO_CSRF_TRUSTED_ORIGINS`, o el
login del backoffice va a fallar por CSRF.

## Setup local (sin Docker)

Backend:

```bash
uv sync
uv run python src/manage.py migrate
uv run python src/manage.py seed_assessment_data
uv run python src/manage.py runserver
```

App cliente, en otra terminal (requiere Node 20.19+ o 22+; Vite reenvía `/api` al backend
en `:8000`):

```bash
cd client-app
npm install
npm run dev
```

Queda en [http://localhost:5173](http://localhost:5173). Más detalles en
[client-app/README.md](./client-app/README.md).

## URLs útiles

- Backoffice login: [http://127.0.0.1:8000/accounts/login/](http://127.0.0.1:8000/accounts/login/)
- Backoffice reservas: [http://127.0.0.1:8000/backoffice/reservations/](http://127.0.0.1:8000/backoffice/reservations/)
- API base: [http://127.0.0.1:8000/api/v1/](http://127.0.0.1:8000/api/v1/)

## Checks mínimos

```bash
PYTHONPATH=src uv run pytest
uv run ruff check .
```

Así los tests corren en SQLite, y el test de concurrencia de cancelación se
salta porque necesita bloqueo de filas. Para correr toda la suite contra
Postgres:

```bash
docker run -d --rm --name pg-test -p 55432:5432 \
  -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test \
  postgres:17-alpine

POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55432 POSTGRES_DB=test \
  POSTGRES_USER=test POSTGRES_PASSWORD=test uv run pytest

docker stop pg-test
```

## Credenciales semilla

Se crean con `seed_assessment_data`:

- Staff manager
  - username: `manager`
  - password: `demo1234`
- Staff operator
  - username: `operator`
  - password: `demo1234`
- Cliente Alice
  - email: `alice@example.com`
  - password: `demo1234`
- Cliente Bob
  - email: `bob@example.com`
  - password: `demo1234`
