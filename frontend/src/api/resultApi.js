import axiosInstance from './axiosInstance';

/**
 * Fetch result scorecard for an exam attempt.
 * @param {string|number} attemptId
 * @returns {Promise<Object>} result data
 */
export const getResult = async (attemptId) => {
  const response = await axiosInstance.get(`/results/${attemptId}`);
  return response.data;
};

/**
 * Fetch ranking leaderboard for a specific exam.
 * @param {string|number} examId
 * @param {Object} [params] - optional { page, limit }
 * @returns {Promise<Object|Array>} rankings data
 */
export const getExamRankings = async (examId, params = {}) => {
  const response = await axiosInstance.get(`/exams/${examId}/rankings`, { params });
  return response.data;
};
