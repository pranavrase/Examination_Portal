import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import {
  loginUser as apiLoginUser,
  registerUser as apiRegisterUser,
  refreshAccessToken as apiRefreshAccessToken,
  logoutUser as apiLogoutUser,
  setStoredRefreshToken,
} from '../api/authApi';
import { setMemoryToken, registerLogoutCallback, setInitializationPromise } from '../api/axiosInstance';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Derived user role (e.g. 'student', 'examiner', 'admin')
  const role = user?.role || user?.user?.role || null;
  const isAuthenticated = Boolean(user && token);

  // Helper to extract user info from response payload
  const handleAuthSuccess = (responseData) => {
    const accessToken = responseData?.access_token || responseData?.token || null;
    const userInfo = responseData?.user || responseData?.data?.user || responseData?.userInfo || responseData;

    setToken(accessToken);
    setMemoryToken(accessToken);

    if (userInfo && typeof userInfo === 'object') {
      setUser(userInfo);
    }
    return { token: accessToken, user: userInfo, role: userInfo?.role };
  };

  const clearAuthState = useCallback(() => {
    setUser(null);
    setToken(null);
    setMemoryToken(null);
    setStoredRefreshToken(null);
  }, []);

  // Silent refresh token on initial application mount
  const initializeAuth = useCallback(async () => {
    setLoading(true);
    try {
      // Expose the refresh promise to the axios interceptor so concurrent requests
      // during app boot will queue behind this single initialization, not race.
      const refreshPromise = apiRefreshAccessToken();
      setInitializationPromise(refreshPromise);
      const data = await refreshPromise;
      handleAuthSuccess(data);
    } catch (err) {
      // Session expired or no active refresh cookie / stored token present
      clearAuthState();
    } finally {
      setInitializationPromise(null);
      setLoading(false);
    }
  }, [clearAuthState]);

  useEffect(() => {
    initializeAuth();
    // Register clear state callback for Axios 401 interceptor
    registerLogoutCallback(clearAuthState);
  }, [initializeAuth, clearAuthState]);

  const login = async (credentials) => {
    const data = await apiLoginUser(credentials);
    return handleAuthSuccess(data);
  };

  const register = async (userData) => {
    const data = await apiRegisterUser(userData);
    return data;
  };

  const logout = async () => {
    try {
      await apiLogoutUser();
    } catch (err) {
      console.warn('Logout request failed or session already expired', err);
    } finally {
      clearAuthState();
    }
  };

  const refreshToken = async () => {
    try {
      const data = await apiRefreshAccessToken();
      return handleAuthSuccess(data);
    } catch (err) {
      clearAuthState();
      throw err;
    }
  };

  const updateUser = (updates) => {
    setUser(prev => ({ ...prev, ...updates }));
  };

  const value = {
    user,
    token,
    role,
    isAuthenticated,
    loading,
    login,
    register,
    logout,
    refreshToken,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
