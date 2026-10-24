import axiosInstance from './axiosInstance';

/**
 * Admin API Service
 * Maps to actual backend endpoints for admin-scoped operations.
 * Note: Admin shares the /examiner/stats endpoint and /users management endpoints.
 */

/**
 * Get aggregated platform statistics (admin uses examiner stats endpoint).
 * @returns {Promise<Object>}
 */
export const getAdminStats = async (signal = undefined) => {
  const response = await axiosInstance.get('/examiner/stats', { signal });
  return response.data;
};

/**
 * List all users with optional pagination and filtering.
 * Restricted to admin role on the backend.
 * @param {Object} params - { page, page_size, email, full_name, role, is_active }
 * @param {AbortSignal} [signal] - Optional abort signal for cancellation
 * @returns {Promise<{ items: Array, total: number }>}
 */
export const getUsers = async (params = {}, signal = undefined) => {
  const response = await axiosInstance.get('/users', { params, signal });
  return response.data;
};

/**
 * Update a user's primary role (admin only).
 * @param {number} userId
 * @param {string} role - new role name
 * @returns {Promise<Object>} updated user
 */
export const updateUserRole = async (userId, role) => {
  const response = await axiosInstance.put(`/users/${userId}/role`, { role });
  return response.data;
};

/**
 * Deactivate a user account (sets is_active = false). Admin only.
 * @param {number} userId
 * @returns {Promise<Object>} updated user record
 */
export const deactivateUser = async (userId) => {
  const response = await axiosInstance.delete(`/users/${userId}`);
  return response.data;
};

/**
 * Fetch paginated activity logs (admin scope).
 * @param {Object} params - { exam_id, attempt_id, student, activity_type, from_date, to_date, page, limit }
 * @param {AbortSignal} [signal] - Optional abort signal for cancellation
 * @returns {Promise<Object>}
 */
export const getActivityLogs = async (params = {}, signal = undefined) => {
  const response = await axiosInstance.get('/activity-logs', { params, signal });
  return response.data;
};

/**
 * Create a new examiner account (Admin only).
 * @param {Object} data - { email, password, full_name }
 * @returns {Promise<Object>} created examiner user record
 */
export const createExaminer = async (data) => {
  const response = await axiosInstance.post('/admin/examiners', data);
  return response.data;
};

/**
 * Delete an existing examiner account (Admin only).
 * @param {number} userId - Examiner user ID
 * @returns {Promise<Object>}
 */
export const deleteExaminer = async (userId) => {
  const response = await axiosInstance.delete(`/admin/examiners/${userId}`);
  return response.data;
};
