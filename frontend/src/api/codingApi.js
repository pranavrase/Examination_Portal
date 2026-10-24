import axiosInstance from './axiosInstance';

/**
 * Fetch coding questions for a specific exam attempt
 * @param {string|number} examId
 */
export const getCodingQuestions = async (examId) => {
  const response = await axiosInstance.get(`/coding/questions/${examId}`);
  return response.data;
};

/**
 * Run student code against sample test cases
 * @param {Object} payload - { question_id, code, language, input? }
 */
export const runCode = async (payload) => {
  const response = await axiosInstance.post('/coding/run', payload);
  return response.data;
};

/**
 * Submit student code for final evaluation against hidden test cases
 * @param {Object} payload - { question_id, code, language }
 */
export const submitCode = async (payload) => {
  const response = await axiosInstance.post('/coding/submit', payload);
  return response.data;
};
