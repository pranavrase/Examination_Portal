import axiosInstance from './axiosInstance';

/**
 * Fetch authoritative remaining time for an active exam attempt
 * @param {string|number} attemptId
 */
export const getRemainingTime = async (attemptId) => {
  const response = await axiosInstance.get(`/exam-attempts/${attemptId}/remaining-time`);
  return response.data;
};

/**
 * Submit exam attempt (triggered manually or auto-submitted on timer expiration)
 * @param {string|number} attemptId
 * @param {Object} payload
 */
export const submitExamAttempt = async (attemptId, payload = {}) => {
  const response = await axiosInstance.post(`/exam-attempts/${attemptId}/submit`, payload);
  return response.data;
};

/**
 * Auto-save MCQ answers and coding drafts for an active exam attempt.
 * Called periodically during an active exam without user interaction.
 *
 * @param {string|number} attemptId
 * @param {Object} payload - { mcq_answers: {questionId: selectedOption}, coding_drafts: {questionId: {language, code}} }
 */
export const autoSaveAnswers = async (attemptId, payload = {}) => {
  const response = await axiosInstance.put(
    `/exam-attempts/${attemptId}/answers/autosave`,
    payload
  );
  return response.data;
};
