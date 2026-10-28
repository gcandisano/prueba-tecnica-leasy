import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  cancelReservation,
  getMe,
  listReservations,
  type ClientProfile,
  type Reservation,
} from "../api";
import { errorMessage } from "../errorMessages";
import { formatDateTime, isCancellable, statusLabel } from "../format";
import CancelReservationDialog from "./CancelReservationDialog";

type Props = {
  token: string;
  onLogout: () => void;
  onSessionExpired: () => void;
};

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready" };

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.isUnauthorized;
}

export default function ReservationsPage({ token, onLogout, onSessionExpired }: Props) {
  const [profile, setProfile] = useState<ClientProfile | null>(null);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loadState, setLoadState] = useState<LoadState>({ kind: "loading" });
  const [cancelTarget, setCancelTarget] = useState<Reservation | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadState({ kind: "loading" });
    try {
      const [me, items] = await Promise.all([getMe(token), listReservations(token)]);
      setProfile(me);
      setReservations(items);
      setLoadState({ kind: "ready" });
    } catch (error) {
      if (isUnauthorized(error)) {
        onSessionExpired();
        return;
      }
      setLoadState({ kind: "error", message: errorMessage(error) });
    }
  }, [token, onSessionExpired]);

  useEffect(() => {
    void load();
  }, [load]);

  // Throws on failure so the dialog can show the error next to the form.
  async function confirmCancel(reservation: Reservation, reason: string) {
    try {
      const updated = await cancelReservation(token, reservation.id, reason);
      setReservations((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setCancelTarget(null);
      setSuccessMessage(`La reserva de ${updated.room_name} fue cancelada.`);
    } catch (error) {
      if (isUnauthorized(error)) {
        onSessionExpired();
        return;
      }
      if (error instanceof ApiError && (error.status === 404 || error.status === 409)) {
        // Our copy of the list is stale (e.g. cancelled from another tab): resync it.
        listReservations(token).then(setReservations, () => {});
      }
      throw error;
    }
  }

  function openCancelDialog(reservation: Reservation) {
    setSuccessMessage(null);
    setCancelTarget(reservation);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>Mis reservas</h1>
          {profile && <p className="muted">{profile.display_name}</p>}
        </div>
        <button className="btn" type="button" onClick={onLogout}>
          Cerrar sesión
        </button>
      </header>

      {successMessage && (
        <p className="alert alert--success" role="status">
          {successMessage}
        </p>
      )}

      <section className="card">
        {loadState.kind === "loading" && <p className="muted">Cargando reservas…</p>}

        {loadState.kind === "error" && (
          <div className="stack">
            <p className="alert alert--error" role="alert">
              {loadState.message}
            </p>
            <button className="btn" type="button" onClick={() => void load()}>
              Reintentar
            </button>
          </div>
        )}

        {loadState.kind === "ready" && reservations.length === 0 && (
          <p className="muted">No tienes reservas.</p>
        )}

        {loadState.kind === "ready" && reservations.length > 0 && (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Sala</th>
                  <th>Inicio</th>
                  <th>Fin</th>
                  <th>Estado</th>
                  <th>Motivo de cancelación</th>
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {reservations.map((reservation) => (
                  <tr key={reservation.id}>
                    <td>{reservation.room_name}</td>
                    <td>{formatDateTime(reservation.starts_at)}</td>
                    <td>{formatDateTime(reservation.ends_at)}</td>
                    <td>
                      <span className={`badge badge--${reservation.status}`}>
                        {statusLabel(reservation.status)}
                      </span>
                    </td>
                    <td>{reservation.cancel_reason ?? "-"}</td>
                    <td>
                      {isCancellable(reservation.status) && (
                        <button
                          className="btn btn--danger"
                          type="button"
                          onClick={() => openCancelDialog(reservation)}
                        >
                          Cancelar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {cancelTarget && (
        <CancelReservationDialog
          reservation={cancelTarget}
          onConfirm={(reason) => confirmCancel(cancelTarget, reason)}
          onClose={() => setCancelTarget(null)}
        />
      )}
    </main>
  );
}
