const API_BASE_URL = "/api/v1";

export type ReservationStatus = "requested" | "confirmed" | "on_hold" | "cancelled";

export type Reservation = {
  id: string;
  room_name: string;
  status: ReservationStatus | string;
  starts_at: string;
  ends_at: string;
  cancel_reason: string | null;
};

export type ClientProfile = {
  id: string;
  email: string;
  display_name: string;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
};

// Error body defined in API_CONTRACT.md (Problem Details).
export type Problem = {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  instance: string;
  errors: Array<{ loc: Array<string | number>; msg: string; type: string }> | null;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly problem: Problem | null;

  constructor(status: number, code: string, message: string, problem: Problem | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.problem = problem;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }
}

type RequestOptions = {
  method?: "GET" | "POST";
  token?: string;
  body?: unknown;
};

async function request<T>(path: string, { method = "GET", token, body }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "network_error", "No se pudo conectar con el servidor.");
  }

  if (!response.ok) {
    throw await toApiError(response);
  }
  return (await response.json()) as T;
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const problem = (await response.json()) as Problem;
    if (typeof problem.code === "string") {
      return new ApiError(response.status, problem.code, problem.detail, problem);
    }
  } catch {
    // Body is not JSON (e.g. a proxy error page): fall through to a generic error.
  }
  return new ApiError(response.status, "unexpected_error", `Error inesperado (${response.status}).`);
}

export async function login(email: string, password: string): Promise<string> {
  const data = await request<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
  return data.access_token;
}

export function getMe(token: string): Promise<ClientProfile> {
  return request<ClientProfile>("/auth/me", { token });
}

export function listReservations(token: string): Promise<Reservation[]> {
  return request<Reservation[]>("/reservations/", { token });
}

export function cancelReservation(token: string, reservationId: string, reason: string): Promise<Reservation> {
  return request<Reservation>(`/reservations/${reservationId}/cancel`, {
    method: "POST",
    token,
    body: { reason },
  });
}
