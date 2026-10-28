import { useEffect, useRef, useState, type FormEvent } from "react";

import type { Reservation } from "../api";
import { errorMessage } from "../errorMessages";
import { formatDateTime } from "../format";

type Props = {
  reservation: Reservation;
  onConfirm: (reason: string) => Promise<void>;
  onClose: () => void;
};

export default function CancelReservationDialog({ reservation, onConfirm, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Native <dialog> gives us focus trapping, Escape to close and a backdrop.
  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedReason = reason.trim();
    if (!trimmedReason) {
      setError("El motivo es obligatorio.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await onConfirm(trimmedReason);
    } catch (err) {
      setError(errorMessage(err));
      setSubmitting(false);
    }
  }

  function handleClose() {
    if (!submitting) onClose();
  }

  return (
    <dialog
      ref={dialogRef}
      className="dialog"
      aria-labelledby="cancel-dialog-title"
      onCancel={(event) => {
        event.preventDefault();
        handleClose();
      }}
    >
      <form className="stack" onSubmit={handleSubmit}>
        <h2 id="cancel-dialog-title">Cancelar reserva</h2>
        <p className="muted">
          {reservation.room_name} · {formatDateTime(reservation.starts_at)}
        </p>

        <label className="field">
          <span>Motivo</span>
          <textarea
            rows={4}
            maxLength={1000}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            disabled={submitting}
            autoFocus
          />
        </label>

        {error && (
          <p className="alert alert--error" role="alert">
            {error}
          </p>
        )}

        <div className="actions">
          <button className="btn" type="button" onClick={handleClose} disabled={submitting}>
            Volver
          </button>
          <button className="btn btn--danger" type="submit" disabled={submitting}>
            {submitting ? "Cancelando…" : "Confirmar cancelación"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
