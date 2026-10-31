/* oxlint-disable react/only-export-components -- the provider and its hook belong together */
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // True while a saved token is being checked with GET /auth/me on app load.
  const [checking, setChecking] = useState(() => Boolean(localStorage.getItem("token")));
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!checking) return;
    let stale = false;
    api
      .me()
      .then((me) => {
        if (stale) return;
        setUser(me);
        setChecking(false);
      })
      .catch((err) => {
        // On a 401 the API client is already redirecting to /login.
        if (stale || err.status === 401) return;
        setLoadError(err.message);
        setChecking(false);
      });
    return () => {
      stale = true;
    };
  }, [checking]);

  function retry() {
    setLoadError("");
    setChecking(true);
  }

  function acceptToken({ access_token, user: me }) {
    localStorage.setItem("token", access_token);
    setUser(me);
  }

  const value = {
    user,
    isOwner: user?.role === "owner",
    checking,
    loadError,
    retry,
    login: (data) => api.login(data).then(acceptToken),
    register: (data) => api.register(data).then(acceptToken),
    logout() {
      localStorage.removeItem("token");
      setUser(null);
    },
    updateUser: (changes) => setUser((old) => ({ ...old, ...changes })),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
