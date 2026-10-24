import axiosInstance from './axiosInstance';

/**
 * Fetch paginated activity logs.
 * @param {Object} params - { exam_id, attempt_id, student, activity_type, from_date, to_date, page, limit }
 */
export const getActivityLogs = async (params = {}) => {
  const response = await axiosInstance.get('/activity-logs', { params });
  return response.data;
};

/**
 * Fetch tab-switch events for a specific attempt.
 * @param {string|number} attemptId
 * @param {Object} params - optional extra query params
 */
export const getTabSwitches = async (attemptId, params = {}) => {
  const response = await axiosInstance.get('/activity-logs/tab-switches', {
    params: { attempt_id: attemptId, ...params },
  });
  return response.data;
};

/**
 * Fetch a single activity log entry by ID.
 * @param {string|number} activityId
 */
export const getActivityById = async (activityId) => {
  const response = await axiosInstance.get(`/activity-logs/${activityId}`);
  return response.data;
};
