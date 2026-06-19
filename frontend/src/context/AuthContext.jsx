import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, getToken, setToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const me = await api('/auth/me');
      setUser(me);
      return me;
    } catch {
      setToken('');
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email, password) => {
    const data = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    return refresh();
  }, [refresh]);

  const register = useCallback(async (payload) => {
    const data = await api('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (data.access_token) {
      setToken(data.access_token);
      await refresh();
    }
    return data;
  }, [refresh]);

  const verifyEmail = useCallback(async (email, code) => {
    const data = await api('/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    });
    if (data.access_token) {
      setToken(data.access_token);
      await refresh();
    }
    return data;
  }, [refresh]);

  const resendVerification = useCallback(async (email) => {
    return api('/auth/resend-verification-email', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  }, []);

  const logout = useCallback(async () => {
    try {
      await api('/auth/logout', { method: 'POST' });
    } catch {
      /* ignore */
    }
    setToken('');
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, verifyEmail, resendVerification, logout, refresh }),
    [user, loading, login, register, verifyEmail, resendVerification, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
