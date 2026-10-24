import axiosInstance from './axiosInstance';

/**
 * Fetch topic-wise performance report.
 * @param {Object} params - { exam_id, topic, from_date, to_date }
 */
export const getTopicWiseReport = async (params = {}) => {
  const response = await axiosInstance.get('/reports/topic-wise', { params });
  return response.data;
};

/**
 * Fetch candidate-wise performance report.
 * @param {Object} params - { exam_id, topic, candidate, from_date, to_date, page, limit }
 */
export const getCandidateWiseReport = async (params = {}) => {
  const response = await axiosInstance.get('/reports/candidate-wise', { params });
  return response.data;
};

/**
 * Request a filtered report export (CSV or PDF).
 * Returns a Blob that the browser can download.
 * @param {Object} params - { exam_id, topic, candidate, from_date, to_date, format: 'csv'|'pdf' }
 */
export const exportReport = async (params = {}) => {
  const response = await axiosInstance.get('/reports/export', {
    params,
    responseType: 'blob',
  });
  return response; // Caller extracts blob + headers
};
