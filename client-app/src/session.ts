// sessionStorage keeps the user logged in across reloads but not across tabs or
// browser restarts. Trade-off: readable by JS (XSS); an httpOnly cookie would
// avoid that but requires changing the backend auth scheme.
const TOKEN_KEY = "client-app.access-token";

export function loadToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function saveToken(token: string): void {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Storage unavailable (e.g. private mode): the session lives in memory only.
  }
}

export function clearToken(): void {
  try {
    sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Nothing to clear.
  }
}
