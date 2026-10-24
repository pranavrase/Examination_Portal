import axiosInstance from './axiosInstance';

/**
 * Fetch questions with filter parameters
 * @param {Object} params - { category, topic, difficulty, question_type, search, page, limit }
 */
export const getQuestions = async (params = {}) => {
  const response = await axiosInstance.get('/questions', { params });
  return response.data;
};

/**
 * Get single question details by ID
 * @param {string|number} id
 */
export const getQuestionById = async (id) => {
  const response = await axiosInstance.get(`/questions/${id}`);
  return response.data;
};

/**
 * Create a new question (MCQ or Coding)
 * @param {Object} questionData
 */
export const createQuestion = async (questionData) => {
  const response = await axiosInstance.post('/questions', questionData);
  return response.data;
};

/**
 * Update an existing question
 * @param {string|number} id
 * @param {Object} questionData
 */
export const updateQuestion = async (id, questionData) => {
  const response = await axiosInstance.put(`/questions/${id}`, questionData);
  return response.data;
};

/**
 * Delete a question by ID
 * @param {string|number} id
 */
export const deleteQuestion = async (id) => {
  const response = await axiosInstance.delete(`/questions/${id}`);
  return response.data;
};

/**
 * Save test cases for a coding question
 * @param {string|number} id
 * @param {Array} testCases
 */
export const saveTestCases = async (id, testCases) => {
  const response = await axiosInstance.post(`/questions/coding/${id}/test-cases`, { test_cases: testCases });
  return response.data;
};

/**
 * Bulk import questions via CSV/JSON payload
 * @param {FormData|Object} importData
 */
export const importQuestions = async (importData) => {
  const isFormData = importData instanceof FormData;
  const response = await axiosInstance.post('/questions/import', importData, {
    headers: isFormData ? { 'Content-Type': 'multipart/form-data' } : { 'Content-Type': 'application/json' }
  });
  return response.data;
};
