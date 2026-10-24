import axiosInstance from './axiosInstance';

/**
 * Authentication API Service
 * Interacts directly with FastAPI backend endpoints
 */

// LocalStorage key for refresh token persistence
const REFRESH_TOKEN_KEY = 'exam_portal_refresh_token';

export const setStoredRefreshToken = (token) => {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
};

export const getStoredRefreshToken = () => {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

export const registerUser = async (userData) => {
  const response = await axiosInstance.post('/auth/register', userData);
  return response.data;
};

export const loginUser = async (credentials) => {
  const response = await axiosInstance.post('/auth/login', credentials);
  // Store the refresh token on successful login
  if (response.data?.refresh_token) {
    setStoredRefreshToken(response.data.refresh_token);
  }
  return response.data;
};

export const refreshAccessToken = async () => {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }
  const response = await axiosInstance.post('/auth/refresh', { refresh_token: refreshToken });
  // Update stored refresh token if new one is returned
  if (response.data?.refresh_token) {
    setStoredRefreshToken(response.data.refresh_token);
  }
  return response.data;
};

export const logoutUser = async () => {
  const refreshToken = getStoredRefreshToken();
  try {
    if (refreshToken) {
      const response = await axiosInstance.post('/auth/logout', { refresh_token: refreshToken });
      return response.data;
    }
  } finally {
    // Always clear the stored refresh token on logout
    setStoredRefreshToken(null);
  }
  return { message: 'Logged out' };
};

export const forgotPassword = async (emailData) => {
  const response = await axiosInstance.post('/auth/forgot-password', emailData);
  return response.data;
};

export const resetPassword = async (resetData) => {
  const response = await axiosInstance.post('/auth/reset-password', resetData);
  return response.data;
};

export const requestOTP = async (emailData) => {
  const response = await axiosInstance.post('/auth/forgot-password/request-otp', emailData);
  return response.data;
};

export const verifyOTP = async (otpData) => {
  const response = await axiosInstance.post('/auth/forgot-password/verify-otp', otpData);
  return response.data;
};

export const resetPasswordWithOTP = async (resetData) => {
  const response = await axiosInstance.post('/auth/forgot-password/reset-password', resetData);
  return response.data;
};
