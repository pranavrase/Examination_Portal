import axiosInstance from './axiosInstance';

/**
 * Notifications API Service
 * Connects to FastAPI /notifications endpoints (Module 2.15)
 */

/**
 * Fetch paginated notifications for the authenticated user.
 * @param {Object} params - { page, page_size, is_read, notification_type }
 * @returns {Promise<{ items: Array, total: number, page: number, page_size: number, unread_count: number }>}
 */
export const getNotifications = async (params = {}) => {
  const response = await axiosInstance.get('/notifications', { params });
  return response.data;
};

/**
 * Get total unread notification count for the authenticated user.
 * @returns {Promise<{ unread_count: number }>}
 */
export const getUnreadCount = async () => {
  const response = await axiosInstance.get('/notifications/unread-count');
  return response.data;
};

/**
 * Mark a single notification as read.
 * @param {number} notificationId
 * @returns {Promise<Object>} updated notification
 */
export const markAsRead = async (notificationId) => {
  const response = await axiosInstance.patch(`/notifications/${notificationId}/read`);
  return response.data;
};

/**
 * Mark all unread notifications as read.
 * @returns {Promise<{ updated_count: number, message: string }>}
 */
export const markAllRead = async () => {
  const response = await axiosInstance.patch('/notifications/read-all');
  return response.data;
};
