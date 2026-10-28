import { useCallback, useState } from "react";

import LoginForm from "./components/LoginForm";
import ReservationsPage from "./components/ReservationsPage";
import { clearToken, loadToken, saveToken } from "./session";

export default function App() {
  const [token, setToken] = useState<string | null>(() => loadToken());
  const [notice, setNotice] = useState<string | null>(null);

  const handleLogin = useCallback((newToken: string) => {
    saveToken(newToken);
    setNotice(null);
    setToken(newToken);
  }, []);

  const handleLogout = useCallback(() => {
    clearToken();
    setToken(null);
  }, []);

  const handleSessionExpired = useCallback(() => {
    clearToken();
    setToken(null);
    setNotice("Tu sesión expiró. Inicia sesión nuevamente.");
  }, []);

  if (!token) {
    return <LoginForm notice={notice} onLogin={handleLogin} />;
  }

  return (
    <ReservationsPage
      token={token}
      onLogout={handleLogout}
      onSessionExpired={handleSessionExpired}
    />
  );
}
