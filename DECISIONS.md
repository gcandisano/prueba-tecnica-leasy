# Decisiones técnicas

## 1. Las transiciones viven en el servicio y se protegen con un bloqueo de fila (por eso PostgreSQL)

`hold_reservation` y `cancel_customer_reservation` siguen el mismo patrón que
`confirm_reservation` del starter, dentro de `ReservationLifecycleService`:

1. Validan el motivo (`strip()` + no vacío) antes de tocar la base.
2. Leen la reserva con `select_for_update()` dentro de `transaction.atomic`.
3. Recién con la fila bloqueada chequean si la transición es válida.
4. Guardan con `save(update_fields=...)`.

Los estados de origen permitidos están en `constants.py`
(`RESERVATION_HOLDABLE_STATUSES` y `RESERVATION_CANCELLABLE_STATUSES`). La vista del backoffice usa la misma
constante para decidir si muestra el botón "Poner en espera", así que la UI y
la regla no pueden divergir.

- **Reglas elegidas:** solo `requested` y `confirmed` pueden pasar a
`on_hold`. El cliente puede cancelar `requested`, `confirmed` y `on_hold`: si
ya podía cancelar una reserva confirmada, no tiene sentido que una en espera
quede bloqueada para él.



### El admin de Django tampoco puede saltarse el servicio

El starter monta `/admin/`, y `ReservationAdmin` dejaba editar todos los
campos. Un usuario staff con `change_reservation` pero **sin**
`hold_reservation` (como `operator`) podía entrar al admin y poner una reserva
en `on_hold` sin motivo, reactivar una cancelada o reescribir `hold_reason` y
`cancel_reason`. Eso salteaba las tres reglas de la feature: el permiso, el
motivo obligatorio y las transiciones válidas.

Marqué `status`, `hold_reason` y `cancel_reason` como `readonly_fields`. El
admin los sigue mostrando, pero la única forma de cambiar un estado es el
servicio, que es donde están las validaciones.

### Por qué pasamos de SQLite a PostgreSQL

El escenario que me preocupaba: dos requests (un doble click, o el backoffice poniendo en espera mientras el cliente cancela) leen la reserva como `confirmed` al mismo tiempo y las dos intentan cambiarla.

- **Con SQLite**, `select_for_update()` no hace nada. El dato no se corrompe
(SQLite deja escribir a una transacción por vez y rechaza a la que leyó un
estado viejo), pero en una simulación con dos conexiones la segunda falla con
`database is locked`. Ese error no es de dominio, así que el cliente recibe un
**500** en vez de un 409.
- **Con PostgreSQL**, `select_for_update()` bloquea solo esa fila: la segunda
request espera, cuando la primera commitea vuelve a leer, ve `cancelled` y
responde **409** `reservation_invalid_transition`, que es lo que el cliente
sabe mostrar.

Lo verifiqué de dos formas:

- `test_cancel_customer_reservation_waits_for_concurrent_cancellation` comprueba
que la segunda cancelación queda esperando y termina en
`ReservationStatusTransitionError`.
- Sacando temporalmente `select_for_update()`, ese test falla: en Postgres la  
segunda request **sí** cancela y pisa el motivo de la primera. O sea, en  
Postgres el lock no es decorativo, es lo que evita la doble cancelación.

Además, PostgreSQL es lo que usaría en producción: permite varias réplicas del backend contra la misma base y no depende de un archivo dentro de un volumen.

- **Trade-off:** un contenedor más en compose y una dependencia nueva
(`psycopg[binary]`). Uso la variante `binary` porque trae su propia `libpq` y
no obliga a instalar paquetes de sistema ni un compilador en la imagen; para
producción estricta, psycopg recomienda compilarlo contra la `libpq` del
sistema. Fuera de Docker, Django sigue usando SQLite si no hay
`POSTGRES_HOST`, así que el setup local y `pytest` siguen como en el starter.
El test de concurrencia se salta en SQLite, y el README explica cómo correr
la suite contra Postgres.



## 2. Errores del API estables: Problem Details con `code`, y el HTTP status se decide en la capa API

Los servicios lanzan errores de dominio (`ReservationNotFoundError`,
`ReservationStatusTransitionError`, ...) que no saben nada de HTTP. En
`client_portal/api.py`, la tabla `ERROR_HTTP` los traduce a status:


| Error                                     | Status | `code`                                 |
| ----------------------------------------- | ------ | -------------------------------------- |
| Reserva inexistente **o de otro cliente** | 404    | `reservation_not_found`                |
| Transición inválida                       | 409    | `reservation_invalid_transition`       |
| Body inválido o motivo vacío              | 422    | `validation_error`                     |
| Sin token / token inválido                | 401    | `auth_required` / `auth_invalid_token` |


- **Por qué:** el dominio queda reutilizable desde el backoffice (que muestra
el mismo error como mensaje) y el contrato HTTP está en un solo lugar.
- **404 en vez de 403 para reservas ajenas:** un 403 confirmaría que el ID
existe. El servicio filtra por `customer_id`, así que para el cliente una
reserva ajena simplemente no existe.
- **El cliente decide por** `code`**, no por el texto:** `errorMessages.ts` mapea
cada `code` a un mensaje en español. Los textos del backend pueden cambiar sin
romper la app.
- **Trade-off:** agregué handlers globales para `AuthenticationError` y
`ValidationError` de Ninja. Eso también cambia el formato de los 422 de
`/auth/login`, que antes devolvía el formato por defecto de Ninja. Es más
consistente con `API_CONTRACT.md`, pero es un cambio de comportamiento sobre
un endpoint existente.



## 3. El cliente y el API se sirven desde el mismo origen (proxy), sin CORS

La app llama a `/api/v1` con una URL relativa. En desarrollo, el proxy de Vite
reenvía `/api` al backend en `:8000`. En Docker, nginx sirve el build estático y
reenvía `/api/` al servicio `backend`.

- **Por qué:** el navegador ve un solo origen, así que no hace falta configurar
CORS en Django ni agregar dependencias. Además, la misma imagen del cliente
sirve para cualquier entorno: la URL del backend (`BACKEND_URL`) se inyecta al
arrancar nginx, no al compilar.
- **Trade-off:** el cliente depende de que haya un reverse proxy delante. Si en
el futuro el API vive en otro dominio, hay que agregar CORS o un proxy en ese
entorno.



## Alternativa descartada: quedarse en SQLite con `transaction_mode = "IMMEDIATE"`

Desde Django 5.1, `"OPTIONS": {"transaction_mode": "IMMEDIATE"}` hace que cada
transacción de SQLite tome el lock de escritura desde el `BEGIN`. La segunda
request esperaría (hasta el timeout de 5 segundos) en vez de fallar, y después
leería `cancelled` y respondería 409. Era el cambio más chico: una línea en
`settings.py` y ningún contenedor nuevo.

La descartamos porque:

- **Lo resuelve bloqueando toda la base, no la fila.** Todas las escrituras
quedan en fila, aunque sean sobre reservas distintas.
- **Deja** `select_for_update()` **del código sin efecto.** Ese código se escribió  
para una base con locks de fila, y en Postgres podemos testear que hace  
lo que dice.



## Otros trade-offs conocidos

- **Migraciones y seed en el entrypoint, no en un servicio aparte:**
`docker/backend-entrypoint.sh` corre `migrate` (que es idempotente) y
`seed_demo_data_if_empty` antes de hacer `exec` de gunicorn. Con una sola
réplica alcanza. Con varias réplicas, todas correrían `migrate` a la vez, y
`seed_demo_data_if_empty` (que chequea si hay datos y después siembra) podría
sembrar dos veces. Ahí pasaría a un servicio `migrate` de una sola ejecución
(`depends_on: condition: service_completed_successfully`).
- **El seed no es idempotente:** `seed_assessment_data` crea reservas con fechas  
relativas a "ahora" y las duplica si se corre de nuevo. En vez de tocar el  
comando del starter, agregué `seed_demo_data_if_empty`, que solo lo llama si  
no hay reservas.
- **Actualización pesimista en el cliente:** la fila cambia a `cancelled`
recién cuando responde el backend, usando la respuesta del servidor. Si el
backend responde 404 o 409, la lista se vuelve a pedir, porque significa que
el estado local quedó desactualizado.
- **Dependencias nuevas:** `gunicorn` (la consigna pide no usar `runserver`),
`whitenoise` (con `DEBUG=False`, Django no sirve los estáticos, y el
backoffice quedaría sin CSS sin agregar otro contenedor) y `psycopg[binary]`
(el driver de PostgreSQL).



## Cosas que identifiqué pero no implementé

Mientras trabajaba en la prueba identifiqué varias reglas de negocio, que un sistema real de reservas necesitaría. No las implementé porque no iban directamente de la mano de la consigna, y agregarlas habría ampliado el alcance sobre código del starter que no se pedía cambiar. Dejo documentadas algunas junto con cómo las encararía.

- **No se puede sacar una reserva de** `on_hold`**:** `confirm_reservation` solo
acepta `requested`, así que una reserva en espera solo puede terminar
cancelada por el cliente. Agregaría una transición `release_hold` en
`ReservationLifecycleService`, con su propio permiso. Habría que decidir si
vuelve a `requested` o al estado anterior; lo segundo requiere guardar el
estado previo al poner en espera.
- **El staff no puede cancelar ni rechazar:** desde el backoffice solo se puede
confirmar o poner en espera; cancelar es exclusivo del cliente. Agregaría
`cancel_reservation` para el staff, con permiso y motivo obligatorio,
reutilizando `RESERVATION_CANCELLABLE_STATUSES`.
- **La edición no mira el estado:** `ReservationUpdateView` permite cambiar  
sala y fechas de una reserva cancelada. Movería la regla de qué estados son  
editables a una constante y la validaría en `ReservationUpdateService`, igual  
que las transiciones.



## Uso de IA

Usé Claude Code como asistente durante toda la prueba: para leer y analizar el starter, discutir alternativas, escribir código, tests y documentación. Revisé cada parte antes de hacer el commit y las decisiones de este documento las tomé yo.