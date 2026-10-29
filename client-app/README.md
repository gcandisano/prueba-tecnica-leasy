# Mini app cliente

App en React + TypeScript (Vite) que consume el API cliente para que un
cliente haga login, vea sus reservas y cancele una con motivo.

## Cómo levantarla (desarrollo)

Requiere Node 20.19+ o 22.12+ y el backend corriendo en `127.0.0.1:8000`
(ver el `README.md` de la raíz).

```bash
cd client-app
npm install
npm run dev
```

Abrir [http://localhost:5173](http://localhost:5173) e ingresar con
`alice@example.com` / `demo1234` (o `bob@example.com`).

Vite reenvía `/api` al backend (`vite.config.ts`), así que el navegador ve un
solo origen y no hace falta configurar CORS. En Docker, nginx cumple ese mismo
rol.

## Scripts

- `npm run dev`: servidor de desarrollo con proxy al API.
- `npm run typecheck`: chequeo de tipos.
- `npm run build`: chequeo de tipos + build de producción en `dist/`.

## Estructura

```
src/
  App.tsx              sesión: sin token → login, con token → mis reservas
  session.ts           persistencia del token (sessionStorage)
  api.ts               cliente HTTP: fetch, ApiError tipado desde Problem Details
  errorMessages.ts     code estable del API → mensaje para el usuario
  format.ts            fechas, etiquetas de estado, estados cancelables
  components/
    LoginForm.tsx
    ReservationsPage.tsx
    CancelReservationDialog.tsx
```

## Decisiones

- **Sin librerías extra**: `fetch` + estado local de React alcanza para una
  pantalla de login, una lista y un modal.
- **Errores por `code`**: la UI traduce el `code` del contrato de errores a un
  mensaje; si llega un código desconocido muestra el `detail` del API.
- **Sesión expirada**: cualquier `401` en una llamada autenticada borra el token
  y vuelve al login con un aviso.
- **Actualización con la respuesta del servidor**: al cancelar, la fila se
  reemplaza por la reserva que devuelve el API. Si el API responde `404` o
  `409` (por ejemplo, la reserva ya se canceló en otra pestaña), se muestra el
  error y se vuelve a pedir la lista para resincronizar.
- **Token en `sessionStorage`**: sobrevive a un refresh pero no a cerrar el
  navegador. Es accesible desde JS (riesgo ante XSS); una cookie `httpOnly`
  lo evitaría, pero requiere cambiar el esquema de auth del backend.
