const STATUS_LABELS: Record<string, string> = {
  requested: "Solicitada",
  confirmed: "Confirmada",
  on_hold: "En espera",
  cancelled: "Cancelada",
};

// Mirrors RESERVATION_CANCELLABLE_STATUSES in the backend. It only decides
// whether to show the button; the API remains the source of truth.
const CANCELLABLE_STATUSES = new Set(["requested", "confirmed", "on_hold"]);

const dateTimeFormat = new Intl.DateTimeFormat("es", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function isCancellable(status: string): boolean {
  return CANCELLABLE_STATUSES.has(status);
}

export function formatDateTime(value: string): string {
  return dateTimeFormat.format(new Date(value));
}
