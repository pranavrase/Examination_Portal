import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const axiosInstance = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Enables httpOnly refresh cookie sending
});

// Memory token store & subscriber callbacks to avoid storing JWT tokens in localStorage
let memoryAccessToken = null;
let onLogoutCallback = null;

// Track whether an auth initialization is in progress (to prevent double-refresh on boot)
let initializationPromise = null;

export const setMemoryToken = (token) => {
  memoryAccessToken = token;
};

export const getMemoryToken = () => memoryAccessToken;

export const setInitializationPromise = (promise) => {
  initializationPromise = promise;
};

export const getInitializationPromise = () => initializationPromise;

export const registerLogoutCallback = (cb) => {
  onLogoutCallback = cb;
};

// Queue handling for concurrent requests during token refresh
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

// Request Interceptor: Attach Access Token
axiosInstance.interceptors.request.use(
  (config) => {
    if (memoryAccessToken && !config.headers['Authorization']) {
      config.headers['Authorization'] = `Bearer ${memoryAccessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle 401 & Automatic Refresh
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If no response or status is not 401, reject immediately
    if (!error.response || error.response.status !== 401) {
      return Promise.reject(error);
    }

    // Do not attempt refresh for authentication endpoints to prevent infinite loops
    const isAuthEndpoint =
      originalRequest.url.includes('/auth/login') ||
      originalRequest.url.includes('/auth/refresh') ||
      originalRequest.url.includes('/auth/register');

    if (isAuthEndpoint || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Fail fast: if there's no refresh token stored, skip the refresh attempt entirely
    // This prevents an unnecessary /auth/refresh call that will also 401
    const storedRefreshTokenCheck = localStorage.getItem('exam_portal_refresh_token');
    if (!storedRefreshTokenCheck) {
      if (onLogoutCallback) onLogoutCallback();
      return Promise.reject(error);
    }

    // If there's an initialization promise in flight (app boot), wait for it first
    // before attempting our own refresh — prevents double-refresh race condition
    if (initializationPromise) {
      try {
        await initializationPromise;
        if (memoryAccessToken) {
          originalRequest.headers['Authorization'] = `Bearer ${memoryAccessToken}`;
          return axiosInstance(originalRequest);
        }
      } catch {
        // initializationPromise failed — fall through to normal refresh attempt
      } finally {
        initializationPromise = null;
      }
    }

    originalRequest._retry = true;

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          originalRequest.headers['Authorization'] = `Bearer ${token}`;
          return axiosInstance(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    isRefreshing = true;

    try {
      // Get the stored refresh token from localStorage
      const storedRefreshToken = localStorage.getItem('exam_portal_refresh_token');
      if (!storedRefreshToken) {
        throw new Error('No refresh token available');
      }

      // Call POST /auth/refresh with the refresh token in the body
      const response = await axios.post(
        `${baseURL}/auth/refresh`,
        { refresh_token: storedRefreshToken },
        { withCredentials: true }
      );

      const newAccessToken = response.data?.access_token || response.data?.token;
      // Update stored refresh token if a new one is returned
      if (response.data?.refresh_token) {
        localStorage.setItem('exam_portal_refresh_token', response.data.refresh_token);
      }

      if (newAccessToken) {
        setMemoryToken(newAccessToken);
        axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;

        processQueue(null, newAccessToken);
        return axiosInstance(originalRequest);
      } else {
        throw new Error('No access token returned from refresh');
      }
    } catch (refreshError) {
      processQueue(refreshError, null);
      setMemoryToken(null);
      localStorage.removeItem('exam_portal_refresh_token');
      if (onLogoutCallback) {
        onLogoutCallback();
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default axiosInstance;
