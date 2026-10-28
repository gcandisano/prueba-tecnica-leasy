import { ApiError } from "./api";

// The UI depends on the stable `code`, never on the English `detail` text.
const MESSAGES_BY_CODE: Record<string, string> = {
  auth_invalid_credentials: "Email o contraseña incorrectos.",
  auth_invalid_token: "Tu sesión expiró. Inicia sesión nuevamente.",
  auth_required: "Tu sesión expiró. Inicia sesión nuevamente.",
  reservation_not_found: "La reserva no existe o no te pertenece.",
  reservation_invalid_transition: "Esta reserva ya no se puede cancelar en su estado actual.",
  reservation_cancel_reason_required: "El motivo es obligatorio.",
  validation_error: "Revisa los datos ingresados.",
  network_error: "No se pudo conectar con el servidor. Intenta nuevamente.",
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return MESSAGES_BY_CODE[error.code] ?? error.message;
  }
  return "Ocurrió un error inesperado.";
}
